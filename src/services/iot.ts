import { IoTDevice } from '@/types';
import { mockIotDevice, mockTelemetryHistory } from '@/data/mockIot';
import { supabase, isSupabaseConfigured } from '@/lib/supabase/client';

let currentDevice: IoTDevice = { ...mockIotDevice };

export const iotService = {
  async getIoTDeviceStatus(): Promise<IoTDevice> {
    if (isSupabaseConfigured()) {
      try {
        const { data, error } = await supabase
          .from('iot_devices')
          .select('*')
          .limit(1)
          .maybeSingle();

        if (!error && data) {
          const lastAlert = data.last_alert_time
            ? new Date(data.last_alert_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            : '10:45 AM';

          return {
            id: data.id,
            name: data.device_name,
            status: data.status as 'ONLINE' | 'OFFLINE',
            ip: data.ip_address,
            mac: data.device_uid,
            buzzerStatus: data.buzzer_status as 'READY' | 'TRIGGERED' | 'DISABLED',
            ledStatus: data.led_status as 'READY' | 'WARNING' | 'ALERT' | 'OFF',
            ledColor: data.led_color || '#10b981',
            lastAlertTime: lastAlert,
            firmwareVersion: data.firmware_version,
            rssi: -48,
            uptime: '04h 32m 18s',
          };
        }
      } catch (err) {
        console.warn('Supabase getIoTDeviceStatus failed, using local store:', err);
      }
    }

    await new Promise((r) => setTimeout(r, 100));
    return { ...currentDevice };
  },

  async getTelemetryHistory() {
    await new Promise((r) => setTimeout(r, 100));
    return [...mockTelemetryHistory];
  },

  async sendIoTAlert(payload: {
    buzzerDurationMs?: number;
    ledColor?: string;
    reason?: string;
    studentName?: string;
  }): Promise<{ success: boolean; message: string; timestamp: string }> {
    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    if (isSupabaseConfigured()) {
      try {
        // Record hardware command in iot_events
        await supabase.from('iot_events').insert({
          device_id: '00000000-0000-0000-0000-000000000301',
          event_type: 'BUZZER_TRIGGER',
          command: {
            duration_ms: payload.buzzerDurationMs || 2000,
            led_color: payload.ledColor || '#ef4444',
            reason: payload.reason || 'Cheating Alert Dispatched',
          },
          status: 'SENT',
        });

        // Update hardware status
        await supabase
          .from('iot_devices')
          .update({
            buzzer_status: 'TRIGGERED',
            led_status: 'ALERT',
            led_color: payload.ledColor || '#ef4444',
            last_alert_time: new Date().toISOString(),
          })
          .eq('device_uid', 'ESP32-HALL304-NODE1');

        setTimeout(async () => {
          await supabase
            .from('iot_devices')
            .update({ buzzer_status: 'READY' })
            .eq('device_uid', 'ESP32-HALL304-NODE1');
        }, 4000);
      } catch (err) {
        console.warn('Supabase sendIoTAlert failed:', err);
      }
    }

    currentDevice = {
      ...currentDevice,
      buzzerStatus: 'TRIGGERED',
      ledStatus: 'ALERT',
      ledColor: payload.ledColor || '#ef4444',
      lastAlertTime: now,
    };

    setTimeout(() => {
      currentDevice.buzzerStatus = 'READY';
    }, 4000);

    return {
      success: true,
      message: `ESP32 [${currentDevice.ip}] buzzer triggered & LED set to alert state.`,
      timestamp: now,
    };
  },

  // Real-time subscription hook for ESP32 hardware status
  subscribeToIoT(callback: (device: Partial<IoTDevice>) => void) {
    if (!isSupabaseConfigured()) return () => {};

    const channel = supabase
      .channel('realtime:iot_devices')
      .on(
        'postgres_changes',
        { event: 'UPDATE', schema: 'public', table: 'iot_devices' },
        (payload: any) => {
          const row = payload.new;
          callback({
            status: row.status,
            buzzerStatus: row.buzzer_status,
            ledStatus: row.led_status,
            ledColor: row.led_color,
          });
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  },

  async testBuzzer(): Promise<{ success: boolean; message: string }> {
    return this.sendIoTAlert({ buzzerDurationMs: 1500, reason: 'Manual Test' });
  },

  async setLedState(mode: 'NORMAL' | 'WARNING' | 'ALERT' | 'OFF'): Promise<IoTDevice> {
    const colorMap = {
      NORMAL: '#10b981',
      WARNING: '#f59e0b',
      ALERT: '#ef4444',
      OFF: '#475569',
    };

    const ledStatus = mode === 'OFF' ? 'OFF' : mode === 'NORMAL' ? 'READY' : mode === 'WARNING' ? 'WARNING' : 'ALERT';
    const ledColor = colorMap[mode];

    if (isSupabaseConfigured()) {
      try {
        await supabase
          .from('iot_devices')
          .update({ led_status: ledStatus, led_color: ledColor })
          .eq('device_uid', 'ESP32-HALL304-NODE1');

        await supabase.from('iot_events').insert({
          device_id: '00000000-0000-0000-0000-000000000301',
          event_type: mode === 'ALERT' ? 'LED_ALARM' : mode === 'WARNING' ? 'LED_WARNING' : 'HEARTBEAT',
          command: { mode, hex: ledColor },
        });
      } catch (err) {
        console.warn('Supabase setLedState failed:', err);
      }
    }

    currentDevice = {
      ...currentDevice,
      ledStatus,
      ledColor,
    };
    return { ...currentDevice };
  },

  async toggleDeviceConnection(): Promise<IoTDevice> {
    const newStatus = currentDevice.status === 'ONLINE' ? 'OFFLINE' : 'ONLINE';
    if (isSupabaseConfigured()) {
      try {
        await supabase
          .from('iot_devices')
          .update({ status: newStatus })
          .eq('device_uid', 'ESP32-HALL304-NODE1');
      } catch (err) {
        console.warn('Supabase toggleDeviceConnection failed:', err);
      }
    }
    currentDevice = {
      ...currentDevice,
      status: newStatus,
    };
    return { ...currentDevice };
  },
};
