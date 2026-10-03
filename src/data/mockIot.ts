import { IoTDevice } from '@/types';

export const mockIotDevice: IoTDevice = {
  id: 'esp32-node-01',
  name: 'ESP32 Hall Alert Node [Unit-A]',
  status: 'ONLINE',
  ip: '192.168.1.10',
  mac: '24:6F:28:8C:3A:1B',
  buzzerStatus: 'READY',
  ledStatus: 'READY',
  ledColor: '#10b981', // green = normal
  lastAlertTime: '10:45 AM',
  firmwareVersion: 'v2.4.1-ai-proctor',
  rssi: -48, // dBm (strong)
  uptime: '04h 32m 18s',
};

export const mockTelemetryHistory = [
  { time: '10:00', ping: 12, rssi: -47, packetLoss: 0 },
  { time: '10:10', ping: 14, rssi: -48, packetLoss: 0 },
  { time: '10:20', ping: 13, rssi: -48, packetLoss: 0 },
  { time: '10:30', ping: 19, rssi: -50, packetLoss: 0.1 },
  { time: '10:40', ping: 15, rssi: -49, packetLoss: 0 },
  { time: '10:42', ping: 22, rssi: -48, packetLoss: 0 },
  { time: '10:45', ping: 28, rssi: -49, packetLoss: 0.2 }, // Alert trigger point
  { time: '10:50', ping: 14, rssi: -48, packetLoss: 0 },
  { time: '11:00', ping: 13, rssi: -47, packetLoss: 0 },
];
