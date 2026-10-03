'use client';

import React, { useState } from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { 
  Settings, 
  Cpu, 
  Sliders, 
  Volume2, 
  Radio, 
  ShieldCheck, 
  Save, 
  RotateCcw, 
  Check, 
  Server, 
  Mail, 
  HardDrive 
} from 'lucide-react';

export default function SettingsPage() {
  // Settings requested in prompt:
  // Phone Detection Threshold: 90%
  // Head Movement Threshold: 75%
  // Alert Sound: ON
  // ESP32 Alert: ON
  const [phoneThreshold, setPhoneThreshold] = useState(90);
  const [headMovementThreshold, setHeadMovementThreshold] = useState(75);
  const [gazeThreshold, setGazeThreshold] = useState(60);
  const [audioThreshold, setAudioThreshold] = useState(70);

  const [alertSound, setAlertSound] = useState(true);
  const [esp32Alert, setEsp32Alert] = useState(true);
  const [autoRecordClips, setAutoRecordClips] = useState(true);
  const [emailDigest, setEmailDigest] = useState(false);

  const [fastApiEndpoint, setFastApiEndpoint] = useState('http://localhost:8000/api/v1');
  const [esp32Ip, setEsp32Ip] = useState('192.168.1.10');

  const [savedToast, setSavedToast] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSavedToast(true);
    setTimeout(() => setSavedToast(false), 3000);
  };

  const handleResetDefaults = () => {
    setPhoneThreshold(90);
    setHeadMovementThreshold(75);
    setGazeThreshold(60);
    setAudioThreshold(70);
    setAlertSound(true);
    setEsp32Alert(true);
    setAutoRecordClips(true);
    setEmailDigest(false);
    setFastApiEndpoint('http://localhost:8000/api/v1');
    setEsp32Ip('192.168.1.10');
  };

  return (
    <AppLayout breadcrumbs={[{ label: 'Dashboard', href: '/dashboard' }, { label: 'Settings' }]}>
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-extrabold text-white tracking-tight sm:text-3xl">
              System & AI Vision Settings
            </h1>
            <p className="mt-1 text-xs sm:text-sm text-slate-400">
              Fine-tune YOLO confidence cutoffs, MediaPipe angle limits, audio spike thresholds, and IoT hardware triggers.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={handleResetDefaults}
              className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-slate-900 px-3.5 py-2 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Reset Defaults</span>
            </button>
          </div>
        </div>

        <form onSubmit={handleSave} className="space-y-6">
          {/* 1. AI CONFIGURATION (Threshold Sliders) */}
          <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-6 backdrop-blur-xl shadow-xl space-y-6">
            <div className="flex items-center justify-between pb-3 border-b border-white/5">
              <h2 className="text-sm font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-2">
                <Cpu className="h-4 w-4" />
                <span>AI Vision Inference Thresholds</span>
              </h2>
              <span className="text-[11px] font-mono text-slate-400">YOLOv8 + MediaPipe</span>
            </div>

            <div className="space-y-6">
              {/* Phone Detection Threshold: 90% */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <div>
                    <span className="font-bold text-white">Phone Detection Threshold</span>
                    <p className="text-[11px] text-slate-400">
                      Minimum bounding confidence before triggering high-severity mobile infraction
                    </p>
                  </div>
                  <span className="font-mono text-sm font-extrabold text-rose-400 bg-slate-950 px-2.5 py-0.5 rounded border border-rose-500/30">
                    {phoneThreshold}%
                  </span>
                </div>
                <input
                  type="range"
                  min="50"
                  max="99"
                  value={phoneThreshold}
                  onChange={(e) => setPhoneThreshold(Number(e.target.value))}
                  className="w-full accent-rose-500 cursor-pointer h-2 bg-slate-950 rounded-lg"
                />
              </div>

              {/* Head Movement Threshold: 75% */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <div>
                    <span className="font-bold text-white">Head Movement Sensitivity Threshold</span>
                    <p className="text-[11px] text-slate-400">
                      Tolerance for yaw / pitch deviation exceeding 35 degrees from exam booklet
                    </p>
                  </div>
                  <span className="font-mono text-sm font-extrabold text-amber-400 bg-slate-950 px-2.5 py-0.5 rounded border border-amber-500/30">
                    {headMovementThreshold}%
                  </span>
                </div>
                <input
                  type="range"
                  min="40"
                  max="95"
                  value={headMovementThreshold}
                  onChange={(e) => setHeadMovementThreshold(Number(e.target.value))}
                  className="w-full accent-amber-500 cursor-pointer h-2 bg-slate-950 rounded-lg"
                />
              </div>

              {/* Gaze Deviation Threshold: 60% */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <div>
                    <span className="font-bold text-white">Pupil / Gaze Deviation Threshold</span>
                    <p className="text-[11px] text-slate-400">
                      MediaPipe iris landmark vector offset detection sensitivity
                    </p>
                  </div>
                  <span className="font-mono text-sm font-extrabold text-cyan-400 bg-slate-950 px-2.5 py-0.5 rounded border border-cyan-500/30">
                    {gazeThreshold}%
                  </span>
                </div>
                <input
                  type="range"
                  min="30"
                  max="90"
                  value={gazeThreshold}
                  onChange={(e) => setGazeThreshold(Number(e.target.value))}
                  className="w-full accent-cyan-500 cursor-pointer h-2 bg-slate-950 rounded-lg"
                />
              </div>

              {/* Audio Noise Threshold: 70dB */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <div>
                    <span className="font-bold text-white">Acoustic Whispering Cutoff</span>
                    <p className="text-[11px] text-slate-400">
                      Microphone input sound pressure level spike limit
                    </p>
                  </div>
                  <span className="font-mono text-sm font-extrabold text-indigo-400 bg-slate-950 px-2.5 py-0.5 rounded border border-indigo-500/30">
                    {audioThreshold} dB
                  </span>
                </div>
                <input
                  type="range"
                  min="40"
                  max="100"
                  value={audioThreshold}
                  onChange={(e) => setAudioThreshold(Number(e.target.value))}
                  className="w-full accent-indigo-500 cursor-pointer h-2 bg-slate-950 rounded-lg"
                />
              </div>
            </div>
          </div>

          {/* 2. HARDWARE & NOTIFICATIONS (Toggles) */}
          <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-6 backdrop-blur-xl shadow-xl space-y-6">
            <div className="flex items-center justify-between pb-3 border-b border-white/5">
              <h2 className="text-sm font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-2">
                <Radio className="h-4 w-4" />
                <span>Hardware Dispatch & Auditory Alerts</span>
              </h2>
              <span className="text-[11px] font-mono text-slate-400">Real-time Toggles</span>
            </div>

            <div className="divide-y divide-white/5 space-y-4">
              {/* Alert Sound: ON */}
              <div className="pt-3 flex items-center justify-between">
                <div>
                  <span className="text-xs font-bold text-white flex items-center gap-2">
                    <Volume2 className="h-4 w-4 text-cyan-400" />
                    <span>Dashboard Alert Sound</span>
                  </span>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Play browser audio chime when critical cheating incident is flagged
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setAlertSound(!alertSound)}
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                    alertSound ? 'bg-cyan-500' : 'bg-slate-800'
                  }`}
                >
                  <span
                    className={`inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                      alertSound ? 'translate-x-5' : 'translate-x-0'
                    }`}
                  />
                </button>
              </div>

              {/* ESP32 Alert: ON */}
              <div className="pt-4 flex items-center justify-between">
                <div>
                  <span className="text-xs font-bold text-white flex items-center gap-2">
                    <Radio className="h-4 w-4 text-emerald-400" />
                    <span>ESP32 Hardware Trigger Sync</span>
                  </span>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Automatically beep microcontroller piezo buzzer & strobe RGB LED on high severity alerts
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setEsp32Alert(!esp32Alert)}
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                    esp32Alert ? 'bg-emerald-500' : 'bg-slate-800'
                  }`}
                >
                  <span
                    className={`inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                      esp32Alert ? 'translate-x-5' : 'translate-x-0'
                    }`}
                  />
                </button>
              </div>

              {/* Auto Record Clips: ON */}
              <div className="pt-4 flex items-center justify-between">
                <div>
                  <span className="text-xs font-bold text-white flex items-center gap-2">
                    <HardDrive className="h-4 w-4 text-indigo-400" />
                    <span>Auto-Record Infraction Video Clips</span>
                  </span>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Save 10 seconds of 1080p video buffer around each verified violation for evidence storage
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setAutoRecordClips(!autoRecordClips)}
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                    autoRecordClips ? 'bg-indigo-500' : 'bg-slate-800'
                  }`}
                >
                  <span
                    className={`inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                      autoRecordClips ? 'translate-x-5' : 'translate-x-0'
                    }`}
                  />
                </button>
              </div>
            </div>
          </div>

          {/* 3. BACKEND INTEGRATION ENDPOINTS */}
          <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-6 backdrop-blur-xl shadow-xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-white/5">
              <h2 className="text-sm font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-2">
                <Server className="h-4 w-4" />
                <span>Backend Architecture Endpoints</span>
              </h2>
              <span className="text-[11px] font-mono text-emerald-400">Ready for FastAPI</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  FastAPI Server URL:
                </label>
                <input
                  type="text"
                  value={fastApiEndpoint}
                  onChange={(e) => setFastApiEndpoint(e.target.value)}
                  className="w-full rounded-xl bg-slate-950/80 border border-white/10 px-3.5 py-2 text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-500/80"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  ESP32 Static IP:
                </label>
                <input
                  type="text"
                  value={esp32Ip}
                  onChange={(e) => setEsp32Ip(e.target.value)}
                  className="w-full rounded-xl bg-slate-950/80 border border-white/10 px-3.5 py-2 text-xs font-mono text-emerald-300 focus:outline-none focus:border-cyan-500/80"
                />
              </div>
            </div>
          </div>

          {/* Save Button */}
          <div className="flex items-center justify-end">
            <button
              type="submit"
              className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 px-6 py-2.5 text-xs font-bold text-slate-950 transition-all shadow-lg shadow-cyan-950/60 hover:scale-[1.02]"
            >
              <Save className="h-4 w-4" />
              <span>Save System Settings</span>
            </button>
          </div>
        </form>

        {/* Toast */}
        {savedToast && (
          <div className="fixed bottom-6 right-6 z-50 rounded-2xl border border-emerald-500/40 bg-slate-900/95 p-4 shadow-2xl backdrop-blur-xl flex items-center gap-3 animate-in fade-in slide-in-from-bottom-2">
            <div className="h-8 w-8 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
              <Check className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-bold text-white">Settings Saved Successfully</p>
              <p className="text-[11px] text-slate-400">Thresholds synced with local state.</p>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
