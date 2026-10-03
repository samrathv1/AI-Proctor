'use client';

import React, { useState, useEffect } from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { StatCard } from '@/components/ui/StatCard';
import { ChartCard } from '@/components/ui/ChartCard';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { iotService } from '@/services/iot';
import { mockIotDevice, mockTelemetryHistory } from '@/data/mockIot';
import { IoTDevice } from '@/types';
import { 
  Cpu, 
  Wifi, 
  Volume2, 
  Lightbulb, 
  Radio, 
  Clock, 
  Activity, 
  RotateCcw, 
  Power, 
  Check, 
  Sliders,
  Server,
  Zap,
  ShieldAlert
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip 
} from 'recharts';

export default function Esp32IoTPage() {
  const [device, setDevice] = useState<IoTDevice>(mockIotDevice);
  const [telemetry, setTelemetry] = useState(mockTelemetryHistory);
  const [buzzerTriggered, setBuzzerTriggered] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);

  const showNotification = (msg: string) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 3500);
  };

  useEffect(() => {
    async function loadDevice() {
      const dev = await iotService.getIoTDeviceStatus();
      if (dev) {
        setDevice(dev);
      }
    }
    loadDevice();

    const unsubscribe = iotService.subscribeToIoT((updatedFields) => {
      setDevice((prev) => ({ ...prev, ...updatedFields }));
    });

    return () => {
      unsubscribe();
    };
  }, []);

  const handleTestBuzzer = async () => {
    setBuzzerTriggered(true);
    const res = await iotService.sendIoTAlert({
      buzzerDurationMs: 2000,
      reason: 'Manual Hardware Test from Dashboard',
    });
    setDevice((prev) => ({
      ...prev,
      buzzerStatus: 'TRIGGERED',
      lastAlertTime: res.timestamp,
    }));
    showNotification('Test buzzer dispatched to ESP32 (GPIO 18). Audio alarm triggered!');

    // Web Audio synthesizer beep simulation if audio context is allowed
    try {
      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(880, audioCtx.currentTime); // A5
      gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.4);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.4);
    } catch (e) {
      // Audio autoplay policy fallback
    }

    setTimeout(() => {
      setBuzzerTriggered(false);
      setDevice((prev) => ({ ...prev, buzzerStatus: 'READY' }));
    }, 3000);
  };

  const handleSetLedMode = async (mode: 'NORMAL' | 'WARNING' | 'ALERT' | 'OFF') => {
    const updated = await iotService.setLedState(mode);
    setDevice(updated);
    showNotification(`ESP32 WS2812 RGB LED set to ${mode} mode.`);
  };

  const handleTogglePower = async () => {
    const updated = await iotService.toggleDeviceConnection();
    setDevice(updated);
    showNotification(`ESP32 connection toggled to ${updated.status}.`);
  };

  return (
    <AppLayout breadcrumbs={[{ label: 'Dashboard', href: '/dashboard' }, { label: 'IoT Device' }]}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-extrabold text-white tracking-tight sm:text-3xl">
                ESP32 IoT Alert Hardware
              </h1>
              <StatusBadge status={device.status} label={device.status} size="sm" />
            </div>
            <p className="mt-1 text-xs sm:text-sm text-slate-400">
              Microcontroller physical actuator bridge for audio alarms, RGB beacons, and room invigilator indicators.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={handleTogglePower}
              className={`inline-flex items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-semibold border transition-all ${
                device.status === 'ONLINE'
                  ? 'border-white/10 bg-slate-900 text-slate-300 hover:text-white'
                  : 'bg-emerald-500 text-slate-950 font-bold'
              }`}
            >
              <Power className="h-4 w-4" />
              <span>{device.status === 'ONLINE' ? 'Simulate Disconnect' : 'Reconnect Node'}</span>
            </button>
          </div>
        </div>

        {/* PRIMARY HARDWARE STATUS BANNER (Display: ESP32 STATUS, Connection, IP, Buzzer, LED, Last Alert) */}
        <div className="relative overflow-hidden rounded-2xl border border-cyan-500/30 bg-gradient-to-br from-slate-900/90 via-slate-900/60 to-slate-950/90 p-6 backdrop-blur-xl shadow-2xl">
          <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div className="space-y-2">
              <div className="flex items-center gap-2.5">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  <Cpu className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-white tracking-tight">
                    ESP32 STATUS: <span className="text-emerald-400">{device.status}</span>
                  </h2>
                  <p className="text-xs text-slate-400 font-mono">
                    Node ID: {device.name} • MAC: {device.mac}
                  </p>
                </div>
              </div>
            </div>

            {/* Quick action: Trigger Test Buzzer */}
            <div className="flex items-center gap-3">
              <button
                onClick={handleTestBuzzer}
                disabled={buzzerTriggered || device.status === 'OFFLINE'}
                className={`inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-xs font-bold transition-all shadow-lg ${
                  buzzerTriggered
                    ? 'bg-rose-600 text-white animate-pulse shadow-rose-950/60'
                    : 'bg-rose-500 hover:bg-rose-400 text-white shadow-rose-950/50 hover:scale-[1.02]'
                } disabled:opacity-50`}
              >
                <Volume2 className="h-4 w-4" />
                <span>{buzzerTriggered ? 'BUZZER SOUNDING...' : 'Trigger Test Buzzer'}</span>
              </button>
            </div>
          </div>

          {/* EXACT METRICS FROM USER PROMPT (Connection, IP, Buzzer, LED, Last Alert) */}
          <div className="mt-6 grid grid-cols-2 sm:grid-cols-5 gap-3 pt-5 border-t border-white/5 text-center">
            {/* Connection: ONLINE */}
            <div className="rounded-xl bg-slate-950/60 p-3 border border-white/5">
              <div className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
                Connection
              </div>
              <div className="mt-1 flex items-center justify-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="font-mono text-sm font-bold text-emerald-400">
                  {device.status}
                </span>
              </div>
            </div>

            {/* IP: 192.168.1.10 */}
            <div className="rounded-xl bg-slate-950/60 p-3 border border-white/5">
              <div className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
                Device IP
              </div>
              <div className="mt-1 font-mono text-sm font-bold text-cyan-300">
                {device.ip}
              </div>
            </div>

            {/* Buzzer: READY */}
            <div className="rounded-xl bg-slate-950/60 p-3 border border-white/5">
              <div className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
                Buzzer
              </div>
              <div
                className={`mt-1 font-mono text-sm font-bold ${
                  device.buzzerStatus === 'TRIGGERED' ? 'text-rose-400' : 'text-emerald-400'
                }`}
              >
                {device.buzzerStatus}
              </div>
            </div>

            {/* LED: READY */}
            <div className="rounded-xl bg-slate-950/60 p-3 border border-white/5">
              <div className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
                LED Indicator
              </div>
              <div className="mt-1 flex items-center justify-center gap-1.5">
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: device.ledColor }}
                />
                <span className="font-mono text-sm font-bold text-white">
                  {device.ledStatus}
                </span>
              </div>
            </div>

            {/* Last Alert: 10:45 AM */}
            <div className="rounded-xl bg-slate-950/60 p-3 border border-white/5 col-span-2 sm:col-span-1">
              <div className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
                Last Alert
              </div>
              <div className="mt-1 font-mono text-sm font-bold text-amber-300">
                {device.lastAlertTime}
              </div>
            </div>
          </div>
        </div>

        {/* HARDWARE INTERACTION CARDS */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Card 1: Actuator Controls & LED Modes - 6 Cols */}
          <div className="lg:col-span-6 space-y-5">
            <div className="rounded-2xl border border-white/5 bg-slate-900/70 p-5 backdrop-blur-xl shadow-xl space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-white/5">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <Lightbulb className="h-4 w-4 text-cyan-400" />
                  <span>WS2812 RGB Beacon Control</span>
                </h3>
                <span className="text-[10px] font-mono text-slate-400">GPIO 19</span>
              </div>

              <p className="text-xs text-slate-400">
                Set physical visual beacon in Hall 304 to notify human invigilator without disrupting silent exam room rules.
              </p>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-2">
                <button
                  onClick={() => handleSetLedMode('NORMAL')}
                  className={`rounded-xl p-3 border text-center transition-all ${
                    device.ledColor === '#10b981'
                      ? 'border-emerald-500 bg-emerald-500/20 text-emerald-300 shadow-md'
                      : 'border-white/5 bg-slate-950/60 text-slate-400 hover:text-white'
                  }`}
                >
                  <div className="h-3 w-3 rounded-full bg-emerald-500 mx-auto mb-1.5" />
                  <div className="text-xs font-bold">NORMAL</div>
                  <div className="text-[9px] text-slate-500 mt-0.5">Green Pulse</div>
                </button>

                <button
                  onClick={() => handleSetLedMode('WARNING')}
                  className={`rounded-xl p-3 border text-center transition-all ${
                    device.ledColor === '#f59e0b'
                      ? 'border-amber-500 bg-amber-500/20 text-amber-300 shadow-md'
                      : 'border-white/5 bg-slate-950/60 text-slate-400 hover:text-white'
                  }`}
                >
                  <div className="h-3 w-3 rounded-full bg-amber-500 mx-auto mb-1.5" />
                  <div className="text-xs font-bold">WARNING</div>
                  <div className="text-[9px] text-slate-500 mt-0.5">Amber Glow</div>
                </button>

                <button
                  onClick={() => handleSetLedMode('ALERT')}
                  className={`rounded-xl p-3 border text-center transition-all ${
                    device.ledColor === '#ef4444'
                      ? 'border-rose-500 bg-rose-500/20 text-rose-300 shadow-md'
                      : 'border-white/5 bg-slate-950/60 text-slate-400 hover:text-white'
                  }`}
                >
                  <div className="h-3 w-3 rounded-full bg-rose-500 mx-auto mb-1.5" />
                  <div className="text-xs font-bold">ALARM</div>
                  <div className="text-[9px] text-slate-500 mt-0.5">Red Strobe</div>
                </button>

                <button
                  onClick={() => handleSetLedMode('OFF')}
                  className={`rounded-xl p-3 border text-center transition-all ${
                    device.ledStatus === 'OFF'
                      ? 'border-slate-500 bg-slate-800 text-white shadow-md'
                      : 'border-white/5 bg-slate-950/60 text-slate-400 hover:text-white'
                  }`}
                >
                  <div className="h-3 w-3 rounded-full bg-slate-600 mx-auto mb-1.5" />
                  <div className="text-xs font-bold">DARK</div>
                  <div className="text-[9px] text-slate-500 mt-0.5">Disabled</div>
                </button>
              </div>
            </div>

            {/* Hardware Pin Mapping Visualization */}
            <div className="rounded-2xl border border-white/5 bg-slate-900/70 p-5 backdrop-blur-xl shadow-xl space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-white/5">
                <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                  ESP32 Microcontroller GPIO Mapping
                </h3>
                <span className="text-[10px] font-mono text-emerald-400">Firmware {device.firmwareVersion}</span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="rounded-lg bg-slate-950/60 p-2.5 border border-white/5 flex items-center justify-between">
                  <span className="text-slate-400">GPIO 18:</span>
                  <span className="text-cyan-400 font-bold">Piezo Buzzer (PWM)</span>
                </div>
                <div className="rounded-lg bg-slate-950/60 p-2.5 border border-white/5 flex items-center justify-between">
                  <span className="text-slate-400">GPIO 19:</span>
                  <span className="text-emerald-400 font-bold">WS2812 Data Din</span>
                </div>
                <div className="rounded-lg bg-slate-950/60 p-2.5 border border-white/5 flex items-center justify-between">
                  <span className="text-slate-400">Wi-Fi RSSI:</span>
                  <span className="text-white font-bold">{device.rssi} dBm (Strong)</span>
                </div>
                <div className="rounded-lg bg-slate-950/60 p-2.5 border border-white/5 flex items-center justify-between">
                  <span className="text-slate-400">Uptime:</span>
                  <span className="text-slate-200">{device.uptime}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Card 2: Real-time Ping & Telemetry History - 6 Cols */}
          <div className="lg:col-span-6">
            <ChartCard
              title="ESP32 Ping & Latency Telemetry"
              subtitle="Roundtrip response time between FastAPI server and IoT node"
            >
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={telemetry} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="time" stroke="#64748b" fontSize={11} />
                    <YAxis stroke="#64748b" fontSize={11} domain={[0, 40]} unit="ms" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#090d16',
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderRadius: '0.75rem',
                        color: '#fff',
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="ping"
                      name="Ping (ms)"
                      stroke="#06b6d4"
                      strokeWidth={2.5}
                      dot={{ r: 4, fill: '#06b6d4' }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>
          </div>
        </div>

        {/* Toast */}
        {notification && (
          <div className="fixed bottom-6 right-6 z-50 rounded-2xl border border-cyan-500/40 bg-slate-900/95 p-4 shadow-2xl backdrop-blur-xl flex items-center gap-3 animate-in fade-in slide-in-from-bottom-2">
            <div className="h-8 w-8 rounded-full bg-cyan-500/20 text-cyan-400 flex items-center justify-center">
              <Check className="h-5 w-5" />
            </div>
            <p className="text-xs font-semibold text-white">{notification}</p>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
