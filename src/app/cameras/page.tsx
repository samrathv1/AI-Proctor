'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { AppLayout } from '@/components/layout/AppLayout';
import { CameraCard } from '@/components/ui/CameraCard';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { cameraService } from '@/services/camera';
import { mockCameras } from '@/data/mockCameras';
import { Camera } from '@/types';
import { 
  Laptop, 
  Film, 
  Globe, 
  UploadCloud, 
  Check, 
  Video, 
  RefreshCw, 
  Radio, 
  ShieldCheck, 
  Cpu, 
  Layers 
} from 'lucide-react';

export default function CameraManagementPage() {
  const [cameras, setCameras] = useState<Camera[]>(mockCameras);
  const [selectedCamera, setSelectedCamera] = useState<Camera | null>(mockCameras[0]);

  // Card 1: Laptop webcam state
  const [webcamConnected, setWebcamConnected] = useState(true);

  // Card 2: Recorded video state
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  // Card 3: IP Camera state
  const [rtspUrl, setRtspUrl] = useState('rtsp://192.168.1.120:554/live/ch0');
  const [isConnectingIp, setIsConnectingIp] = useState(false);

  const [notification, setNotification] = useState<string | null>(null);

  const showNotification = (msg: string) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 3000);
  };

  useEffect(() => {
    async function loadCameras() {
      const data = await cameraService.getCameras();
      if (data && data.length > 0) {
        setCameras(data);
      }
    }
    loadCameras();
  }, []);

  // Card 1: Connect / Disconnect Webcam
  const handleToggleWebcam = async () => {
    if (webcamConnected) {
      setWebcamConnected(false);
      showNotification('Webcam disconnected.');
    } else {
      const newCam = await cameraService.connectCamera({
        type: 'WEBCAM',
        name: 'Integrated HD Webcam',
        location: 'Local Invigilator Terminal',
      });
      setCameras((prev) => [newCam, ...prev]);
      setWebcamConnected(true);
      showNotification('Laptop Webcam connected successfully.');
    }
  };

  // Card 2: Upload MP4 & Analyze
  const handleUploadVideo = async () => {
    if (!videoFile) {
      alert('Please select an MP4 video file first.');
      return;
    }
    setIsUploading(true);
    try {
      const newCam = await cameraService.uploadVideoFeed({
        name: videoFile.name,
        size: videoFile.size,
      });
      setCameras((prev) => [newCam, ...prev]);
      setIsUploading(false);
      showNotification(`Video "${videoFile.name}" uploaded and queued for AI analysis.`);
    } catch (e) {
      setIsUploading(false);
    }
  };

  // Card 3: Connect IP Camera
  const handleConnectIp = async () => {
    if (!rtspUrl.trim()) {
      alert('Please enter a valid RTSP stream URL.');
      return;
    }
    setIsConnectingIp(true);
    try {
      const newCam = await cameraService.connectCamera({
        type: 'IP_CAMERA',
        name: `IP Cam - ${rtspUrl.split('//')[1]?.split('/')[0] || 'RTSP Feed'}`,
        url: rtspUrl,
        location: 'Examination Hall Zone',
      });
      setCameras((prev) => [newCam, ...prev]);
      setIsConnectingIp(false);
      showNotification(`RTSP stream connected: ${rtspUrl}`);
    } catch (e) {
      setIsConnectingIp(false);
    }
  };

  const handleDisconnect = async (id: string) => {
    await cameraService.disconnectCamera(id);
    setCameras((prev) =>
      prev.map((c) => (c.id === id ? { ...c, status: 'OFFLINE', fps: 0 } : c))
    );
    showNotification('Camera stream disconnected.');
  };

  return (
    <AppLayout breadcrumbs={[{ label: 'Dashboard', href: '/dashboard' }, { label: 'Cameras' }]}>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-extrabold text-white tracking-tight sm:text-3xl">
              Camera Stream Management
            </h1>
            <p className="mt-1 text-xs sm:text-sm text-slate-400">
              Configure video sources, connect RTSP feeds, upload recorded sessions, and monitor signal fidelity.
            </p>
          </div>

          <Link
            href="/monitoring"
            className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 px-4 py-2.5 text-xs sm:text-sm font-bold text-slate-950 shadow-lg shadow-cyan-950/40 transition-all hover:scale-[1.02]"
          >
            <Video className="h-4 w-4" />
            <span>Open Live Monitoring</span>
          </Link>
        </div>

        {/* 3 CAMERA INPUT METHODS (Cards) */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Layers className="h-4 w-4 text-cyan-400" />
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
              Camera Input Sources (3 Methods Supported)
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {/* CARD 1: Laptop Webcam */}
            <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-slate-900/70 p-6 backdrop-blur-xl shadow-xl flex flex-col justify-between group hover:border-cyan-500/40 transition-all">
              <div>
                <div className="flex items-center justify-between">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 group-hover:scale-105 transition-transform">
                    <Laptop className="h-5 w-5" />
                  </div>
                  <StatusBadge
                    status={webcamConnected ? 'ONLINE' : 'OFFLINE'}
                    label={webcamConnected ? 'Connected' : 'Disconnected'}
                    size="sm"
                  />
                </div>

                <h3 className="mt-4 text-base font-bold text-white tracking-tight">
                  Laptop Webcam
                </h3>
                <p className="mt-1 text-xs text-slate-400">
                  Direct hardware camera on invigilator terminal. Uses HTML5 MediaDevices API with real-time frame capture.
                </p>

                <div className="mt-4 rounded-xl bg-slate-950/60 p-3 border border-white/5 space-y-1 text-xs">
                  <div className="flex items-center justify-between text-slate-400">
                    <span>Status:</span>
                    <span className="font-semibold text-white font-mono">
                      {webcamConnected ? 'Connected' : 'Offline'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-slate-400">
                    <span>Resolution:</span>
                    <span className="font-mono text-cyan-400">1080p (Native)</span>
                  </div>
                </div>
              </div>

              <div className="mt-5 pt-4 border-t border-white/5">
                <button
                  onClick={handleToggleWebcam}
                  className={`w-full rounded-xl py-2.5 text-xs font-bold transition-all shadow-md ${
                    webcamConnected
                      ? 'border border-rose-500/40 bg-rose-500/10 text-rose-300 hover:bg-rose-500/20'
                      : 'bg-cyan-500 hover:bg-cyan-400 text-slate-950 shadow-cyan-950/40'
                  }`}
                >
                  {webcamConnected ? 'Disconnect Camera' : 'Connect Camera'}
                </button>
              </div>
            </div>

            {/* CARD 2: Recorded Video */}
            <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-slate-900/70 p-6 backdrop-blur-xl shadow-xl flex flex-col justify-between group hover:border-cyan-500/40 transition-all">
              <div>
                <div className="flex items-center justify-between">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 group-hover:scale-105 transition-transform">
                    <Film className="h-5 w-5" />
                  </div>
                  <span className="rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 px-2 py-0.5 text-[10px] font-mono font-bold">
                    FILE / MP4
                  </span>
                </div>

                <h3 className="mt-4 text-base font-bold text-white tracking-tight">
                  Recorded Video
                </h3>
                <p className="mt-1 text-xs text-slate-400">
                  Upload an offline examination MP4 recording for retrospective YOLO and MediaPipe forensic auditing.
                </p>

                {/* Upload MP4 Dropzone */}
                <div className="relative mt-4 rounded-xl border border-dashed border-white/10 bg-slate-950/60 p-3 text-center cursor-pointer hover:border-cyan-500/40 transition-colors">
                  <input
                    type="file"
                    accept=".mp4"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        setVideoFile(e.target.files[0]);
                      }
                    }}
                    className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
                  />
                  <UploadCloud className="mx-auto h-5 w-5 text-indigo-400 mb-1" />
                  <span className="text-xs text-slate-300 font-medium block truncate">
                    {videoFile ? videoFile.name : 'Upload MP4'}
                  </span>
                  <span className="text-[10px] text-slate-500">
                    {videoFile ? `${(videoFile.size / (1024 * 1024)).toFixed(1)} MB` : 'Click or drop .mp4'}
                  </span>
                </div>
              </div>

              <div className="mt-5 pt-4 border-t border-white/5">
                <button
                  onClick={handleUploadVideo}
                  disabled={isUploading}
                  className="w-full rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white py-2.5 text-xs font-bold transition-all shadow-md shadow-indigo-950/50 disabled:opacity-50"
                >
                  {isUploading ? 'Uploading & Processing...' : 'Upload & Analyze'}
                </button>
              </div>
            </div>

            {/* CARD 3: IP Camera */}
            <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-slate-900/70 p-6 backdrop-blur-xl shadow-xl flex flex-col justify-between group hover:border-cyan-500/40 transition-all">
              <div>
                <div className="flex items-center justify-between">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 group-hover:scale-105 transition-transform">
                    <Globe className="h-5 w-5" />
                  </div>
                  <span className="rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-mono font-bold">
                    RTSP / ONVIF
                  </span>
                </div>

                <h3 className="mt-4 text-base font-bold text-white tracking-tight">
                  IP Camera
                </h3>
                <p className="mt-1 text-xs text-slate-400">
                  Connect high-framerate CCTV networks over RTSP, WebRTC, or HTTP MJPEG protocols.
                </p>

                <div className="mt-4 space-y-1.5">
                  <label className="block text-[11px] font-semibold text-slate-300">
                    Camera URL:
                  </label>
                  <input
                    type="text"
                    value={rtspUrl}
                    onChange={(e) => setRtspUrl(e.target.value)}
                    placeholder="rtsp://example"
                    className="w-full rounded-xl bg-slate-950/80 border border-white/10 px-3 py-2 text-xs font-mono text-cyan-300 placeholder-slate-500 focus:outline-none focus:border-cyan-500/80"
                  />
                  <span className="text-[10px] text-slate-500 font-mono">
                    Example: rtsp://192.168.1.120:554/live/ch0
                  </span>
                </div>
              </div>

              <div className="mt-5 pt-4 border-t border-white/5">
                <button
                  onClick={handleConnectIp}
                  disabled={isConnectingIp}
                  className="w-full rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 py-2.5 text-xs font-bold transition-all shadow-md shadow-emerald-950/40 disabled:opacity-50"
                >
                  {isConnectingIp ? 'Connecting RTSP Feed...' : 'Connect'}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* ACTIVE CAMERA STATUS CARDS */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <Video className="h-4 w-4 text-cyan-400" />
                <span>Active Camera Nodes in Session</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Real-time telemetry showing FPS, latency, and hardware resolution status.
              </p>
            </div>
            <span className="text-xs font-mono text-cyan-400 bg-slate-900 px-3 py-1 rounded-xl border border-white/5">
              3 Streams Active
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {cameras.map((camera) => (
              <CameraCard
                key={camera.id}
                camera={camera}
                isSelected={selectedCamera?.id === camera.id}
                onSelect={(c) => setSelectedCamera(c)}
                onDisconnect={handleDisconnect}
              />
            ))}
          </div>
        </div>

        {/* Toast Notification */}
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
