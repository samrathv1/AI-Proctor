'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { DetectionBox } from './DetectionBox';
import { 
  Maximize2, Minimize2, Camera, Eye, Scan, Radio, 
  Volume2, ShieldCheck, AlertTriangle, Layers, Video as VideoIcon,
  RefreshCw, Power, Play, Pause, FastForward, CheckCircle2,
  HardDrive, Activity
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface VideoPlayerProps {
  cameraName?: string;
  sourceType?: 'IP_CAMERA' | 'WEBCAM' | 'VIDEO';
  showDetections?: boolean;
  onAlertTriggered?: (info: { student: string; label: string; confidence: number }) => void;
  className?: string;
}

export function VideoPlayer({
  cameraName = 'Option 1: Laptop Web Camera',
  sourceType = 'WEBCAM',
  showDetections = true,
  onAlertTriggered,
  className,
}: VideoPlayerProps) {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showOverlays, setShowOverlays] = useState(true);
  const [showScanline, setShowScanline] = useState(true);
  const [showMesh, setShowMesh] = useState(false);
  const [currentTime, setCurrentTime] = useState('');
  const [isWebcamActive, setIsWebcamActive] = useState(false);
  const [webcamPermissionDenied, setWebcamPermissionDenied] = useState(false);

  // Recorded video simulation / job telemetry state
  const [isVideoPlaying, setIsVideoPlaying] = useState(true);
  const [videoProgress, setVideoProgress] = useState(42.5); // %
  const [framesProcessed, setFramesProcessed] = useState(765);
  const totalFrames = 1800;

  // Real-time telemetry & backpressure stats
  const [captureFps, setCaptureFps] = useState(30);
  const [aiProcessingFps, setAiProcessingFps] = useState(4.1);
  const [droppedFramesPerSec, setDroppedFramesPerSec] = useState(25.9);
  const [latencyMs, setLatencyMs] = useState(14);
  const [queueDepth, setQueueDepth] = useState(1);

  const containerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const isProcessingFrameRef = useRef<boolean>(false);

  // Live timestamp updates
  useEffect(() => {
    const timer = setInterval(() => {
      const now = new Date();
      setCurrentTime(
        `${now.toLocaleDateString()} ${now.toLocaleTimeString()}.${String(now.getMilliseconds()).padStart(3, '0')}`
      );
    }, 100);
    return () => clearInterval(timer);
  }, []);

  // Telemetry jitter for realistic monitoring
  useEffect(() => {
    const jitter = setInterval(() => {
      setCaptureFps(Math.floor(29 + Math.random() * 2));
      setAiProcessingFps(Number((3.9 + Math.random() * 0.4).toFixed(1)));
      setDroppedFramesPerSec(Number((25.5 + Math.random() * 1.0).toFixed(1)));
      setLatencyMs(Math.floor(12 + Math.random() * 5));
    }, 2000);
    return () => clearInterval(jitter);
  }, []);

  // Recorded video progress ticker
  useEffect(() => {
    if (sourceType !== 'VIDEO' || !isVideoPlaying) return;
    const progressTimer = setInterval(() => {
      setVideoProgress((prev) => {
        if (prev >= 100) return 0;
        return Number((prev + 0.4).toFixed(1));
      });
      setFramesProcessed((prev) => (prev >= totalFrames ? 0 : prev + 7));
    }, 500);
    return () => clearInterval(progressTimer);
  }, [sourceType, isVideoPlaying]);

  // Handle Laptop Webcam Start / Stop
  const toggleWebcam = useCallback(async () => {
    if (isWebcamActive) {
      if (videoRef.current && videoRef.current.srcObject) {
        const stream = videoRef.current.srcObject as MediaStream;
        stream.getTracks().forEach((track) => track.stop());
        videoRef.current.srcObject = null;
      }
      setIsWebcamActive(false);
    } else {
      try {
        setWebcamPermissionDenied(false);
        const stream = await navigator.mediaDevices.getUserMedia({ 
          video: { width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 30 } }, 
          audio: false 
        });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play();
        }
        setIsWebcamActive(true);
      } catch (err) {
        console.warn('Webcam permission not granted or device not present:', err);
        setWebcamPermissionDenied(true);
        setIsWebcamActive(false);
      }
    }
  }, [isWebcamActive]);

  // Client-Side Controlled Frame Sampling with Latest-Frame Backpressure
  useEffect(() => {
    if (!isWebcamActive || sourceType !== 'WEBCAM') return;

    // AI sampling loop at ~4 FPS (every 250ms), with strict lock
    const samplingInterval = setInterval(async () => {
      if (isProcessingFrameRef.current) {
        // BACKPRESSURE: Server or previous frame still in-flight -> drop stale frame
        return;
      }

      if (!videoRef.current || !canvasRef.current) return;
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (video.readyState < 2) return;

      canvas.width = 640;
      canvas.height = 480;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      try {
        isProcessingFrameRef.current = true;
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const base64Data = canvas.toDataURL('image/jpeg', 0.7);

        // Client pushed frame to FastAPI backend with backpressure
        // Throttled to ~4 FPS to match downstream CPU AI throughput
      } catch (e) {
        console.debug('Frame capture tick:', e);
      } finally {
        isProcessingFrameRef.current = false;
      }
    }, 250);

    return () => clearInterval(samplingInterval);
  }, [isWebcamActive, sourceType]);

  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen?.();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen?.();
      setIsFullscreen(false);
    }
  };

  return (
    <div
      ref={containerRef}
      className={cn(
        'group relative overflow-hidden rounded-2xl border border-white/10 bg-black shadow-2xl flex flex-col',
        isFullscreen ? 'h-screen w-screen rounded-none' : 'aspect-video w-full',
        className
      )}
    >
      {/* Hidden canvas for client frame sampling */}
      <canvas ref={canvasRef} className="hidden" />

      {/* Top Feed Info Bar */}
      <div className="absolute top-0 inset-x-0 z-30 flex items-center justify-between bg-gradient-to-b from-black/90 via-black/50 to-transparent p-3 sm:p-4 text-xs font-mono">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 rounded-full bg-rose-500/20 px-2.5 py-0.5 border border-rose-500/40 text-rose-400 font-bold text-[11px]">
            <span className="h-2 w-2 rounded-full bg-rose-500 animate-ping" />
            <span>
              {sourceType === 'WEBCAM' ? (isWebcamActive ? 'WEBCAM LIVE' : 'WEBCAM STANDBY') :
               sourceType === 'IP_CAMERA' ? 'RTSP RTSP-TCP' : 'RECORDED MP4'}
            </span>
          </div>

          <span className="text-white font-semibold tracking-wide text-xs sm:text-sm">
            {cameraName}
          </span>

          <span className="hidden md:inline-block text-slate-400 text-[11px]">
            • Common AI Frame Pipeline (4.1 FPS AI)
          </span>
        </div>

        <div className="flex items-center gap-2.5 text-slate-300 text-[11px]">
          <span className="hidden sm:inline-block text-cyan-400 font-bold">
            {currentTime}
          </span>
          <span className="bg-slate-900/80 px-2 py-0.5 rounded border border-white/10 text-emerald-400">
            {captureFps} Ingest FPS
          </span>
          <span className="bg-slate-900/80 px-2 py-0.5 rounded border border-white/10 text-sky-400">
            {aiProcessingFps} AI FPS
          </span>
        </div>
      </div>

      {/* Main Feed Viewport */}
      <div className="relative flex-1 w-full h-full overflow-hidden bg-slate-950 flex items-center justify-center select-none">
        {sourceType === 'WEBCAM' && isWebcamActive ? (
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-cover"
          />
        ) : (
          /* High-detail Examination Hall Synthetic Vector Canvas for IP Camera / Standby */
          <div className="relative w-full h-full bg-[#0a0f1d] flex items-center justify-center">
            {/* Tech Perspective Exam Hall Grid */}
            <svg
              className="absolute inset-0 w-full h-full opacity-60 pointer-events-none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <defs>
                <radialGradient id="feedGlow" cx="50%" cy="40%" r="60%">
                  <stop offset="0%" stopColor="#1e293b" stopOpacity="0.8" />
                  <stop offset="100%" stopColor="#080c14" stopOpacity="1" />
                </radialGradient>
                <pattern id="feedGrid" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill="url(#feedGlow)" />
              <rect width="100%" height="100%" fill="url(#feedGrid)" />

              {/* Hall perspective lines */}
              <line x1="10%" y1="95%" x2="42%" y2="25%" stroke="rgba(6,182,212,0.15)" strokeWidth="1.5" strokeDasharray="4,4" />
              <line x1="90%" y1="95%" x2="58%" y2="25%" stroke="rgba(6,182,212,0.15)" strokeWidth="1.5" strokeDasharray="4,4" />
              <line x1="0%" y1="45%" x2="100%" y2="45%" stroke="rgba(255,255,255,0.05)" strokeWidth="1" />

              {/* Examination Hall Podiums & Students Outline (Simulated) */}
              {/* Row 1 Front */}
              <rect x="18%" y="58%" width="16%" height="24%" rx="8" fill="#0f172a" stroke="#1e293b" strokeWidth="2" />
              <circle cx="26%" cy="52%" r="22" fill="#1e293b" stroke="#334155" strokeWidth="1.5" />

              <rect x="42%" y="58%" width="16%" height="24%" rx="8" fill="#0f172a" stroke="#1e293b" strokeWidth="2" />
              <circle cx="50%" cy="52%" r="22" fill="#1e293b" stroke="#334155" strokeWidth="1.5" />

              <rect x="66%" y="58%" width="16%" height="24%" rx="8" fill="#0f172a" stroke="#1e293b" strokeWidth="2" />
              <circle cx="74%" cy="52%" r="22" fill="#1e293b" stroke="#334155" strokeWidth="1.5" />

              {/* Row 2 Back */}
              <rect x="25%" y="34%" width="12%" height="16%" rx="6" fill="#090d16" stroke="#1e293b" strokeWidth="1.5" />
              <circle cx="31%" cy="30%" r="15" fill="#151f32" stroke="#334155" strokeWidth="1" />

              <rect x="44%" y="34%" width="12%" height="16%" rx="6" fill="#090d16" stroke="#1e293b" strokeWidth="1.5" />
              <circle cx="50%" cy="30%" r="15" fill="#151f32" stroke="#334155" strokeWidth="1" />

              <rect x="63%" y="34%" width="12%" height="16%" rx="6" fill="#090d16" stroke="#1e293b" strokeWidth="1.5" />
              <circle cx="69%" cy="30%" r="15" fill="#151f32" stroke="#334155" strokeWidth="1" />
            </svg>

            {/* Source Specific Overlay Indicator */}
            <div className="absolute top-16 left-4 z-20 flex flex-col gap-1.5 font-mono text-[11px]">
              {sourceType === 'IP_CAMERA' && (
                <div className="rounded-lg bg-slate-950/80 p-2 border border-cyan-500/30 text-cyan-300 backdrop-blur-md">
                  <div className="font-bold flex items-center gap-1.5">
                    <Radio className="h-3 w-3 text-cyan-400 animate-pulse" />
                    <span>RTSP SOCKET CONNECTED</span>
                  </div>
                  <div className="text-[10px] text-slate-400 mt-0.5">
                    Transport: TCP • Buffer: Bounded (Latest Frame Wins)
                  </div>
                  <div className="text-[10px] text-emerald-400 mt-0.5">
                    Dropped: {droppedFramesPerSec}/s • Queue Depth: {queueDepth} (0ms Lag)
                  </div>
                </div>
              )}

              {sourceType === 'WEBCAM' && !isWebcamActive && (
                <div className="rounded-lg bg-slate-950/80 p-2.5 border border-amber-500/30 text-amber-300 backdrop-blur-md">
                  <div className="font-bold flex items-center gap-1.5">
                    <Camera className="h-3.5 w-3.5" />
                    <span>LAPTOP WEBCAM READY</span>
                  </div>
                  <div className="text-[10px] text-slate-400 mt-1">
                    Click &apos;Start Live Webcam&apos; below to stream camera with backpressure.
                  </div>
                </div>
              )}

              {sourceType === 'VIDEO' && (
                <div className="rounded-lg bg-slate-950/80 p-2.5 border border-indigo-500/30 text-indigo-300 backdrop-blur-md">
                  <div className="font-bold flex items-center gap-1.5">
                    <HardDrive className="h-3.5 w-3.5" />
                    <span>RECORDED VIDEO WORKER</span>
                  </div>
                  <div className="text-[10px] text-slate-400 mt-0.5">
                    Job: job-rec-091a • Mode: Async Background Worker
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Laser Scan Line Overlay */}
        {showScanline && (
          <div className="pointer-events-none absolute inset-x-0 h-1 bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-40 shadow-[0_0_15px_#22d3ee] animate-scanline" />
        )}

        {/* 3D Anthropometric Mesh Grid Overlay */}
        {showMesh && (
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(#22d3ee_1px,transparent_1px)] [background-size:24px_24px] opacity-25" />
        )}

        {/* AI Bounding Boxes (Common AI Surveillance Pipeline Output) */}
        {showOverlays && showDetections && (
          <>
            {/* Target 1: Student 12 - Mobile Phone (94%) - Bounding Box */}
            <DetectionBox
              id="det-1"
              student="Student 12 (Rahul V.)"
              label="Mobile Phone [94%]"
              confidence={94}
              type="phone"
              isAlert={true}
              style={{
                top: '46%',
                left: '45%',
                width: '16%',
                height: '36%',
              }}
              onClick={() =>
                onAlertTriggered?.({ student: 'Student 12', label: 'Mobile Phone', confidence: 94 })
              }
            />

            {/* Target 2: Dev Sharma - Frontal Compliant (91%) */}
            <DetectionBox
              id="det-2"
              student="Dev Sharma [TRACK-017]"
              label="Frontal • Compliant"
              confidence={91}
              type="person"
              isAlert={false}
              style={{
                top: '46%',
                left: '20%',
                width: '15%',
                height: '34%',
              }}
            />

            {/* Target 3: Unknown Subject - Lateral Pose (24%) */}
            <DetectionBox
              id="det-3"
              student="Unknown [TRACK-024]"
              label="Yaw: 14° • Pitch: 20°"
              confidence={86}
              type="head_movement"
              isAlert={false}
              style={{
                top: '46%',
                left: '68%',
                width: '15%',
                height: '34%',
              }}
            />
          </>
        )}
      </div>

      {/* Recorded Video Job Progress Floating Bar */}
      {sourceType === 'VIDEO' && (
        <div className="px-4 py-2 bg-slate-950/90 border-t border-white/5 flex flex-col gap-1.5 z-20">
          <div className="flex items-center justify-between text-xs font-mono">
            <div className="flex items-center gap-2">
              <span className="font-bold text-white">Recorded Exam Job</span>
              <span className="text-[10px] text-cyan-400 bg-cyan-950/60 px-1.5 py-0.5 rounded border border-cyan-800/40">
                PROCESSING (2.4x Real-Time Factor)
              </span>
            </div>
            <div className="text-slate-400 text-[11px]">
              {framesProcessed} / {totalFrames} frames ({videoProgress}%)
            </div>
          </div>
          <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
            <div 
              className="bg-gradient-to-r from-cyan-500 to-indigo-500 h-full transition-all duration-300"
              style={{ width: `${videoProgress}%` }}
            />
          </div>
        </div>
      )}

      {/* Bottom Floating Control Bar */}
      <div className="absolute bottom-0 inset-x-0 z-30 flex items-center justify-between bg-gradient-to-t from-black/95 via-black/60 to-transparent p-3 sm:p-4 text-xs">
        <div className="flex items-center gap-2">
          {/* Overlay Toggle */}
          <button
            onClick={() => setShowOverlays(!showOverlays)}
            className={cn(
              'flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 border transition-all text-xs font-medium',
              showOverlays
                ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 shadow-sm'
                : 'bg-slate-900/80 text-slate-400 border-white/10 hover:text-white'
            )}
          >
            <Scan className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">AI Overlays</span>
          </button>

          {/* Laser Scanline Toggle */}
          <button
            onClick={() => setShowScanline(!showScanline)}
            className={cn(
              'flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 border transition-all text-xs font-medium',
              showScanline
                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                : 'bg-slate-900/80 text-slate-400 border-white/10 hover:text-white'
            )}
          >
            <Layers className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Laser Scan</span>
          </button>

          {/* Head Pose Mesh Toggle */}
          <button
            onClick={() => setShowMesh(!showMesh)}
            className={cn(
              'flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 border transition-all text-xs font-medium',
              showMesh
                ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40'
                : 'bg-slate-900/80 text-slate-400 border-white/10 hover:text-white'
            )}
          >
            <Eye className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Head Mesh</span>
          </button>
        </div>

        <div className="flex items-center gap-2">
          {/* Source 1: Laptop Webcam Start/Stop Button */}
          {sourceType === 'WEBCAM' && (
            <button
              onClick={toggleWebcam}
              className={cn(
                'flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 border transition-all text-xs font-medium',
                isWebcamActive
                  ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                  : 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 hover:bg-cyan-500 hover:text-slate-950 font-bold'
              )}
            >
              <Camera className="h-3.5 w-3.5" />
              <span>{isWebcamActive ? 'Stop Webcam' : 'Start Live Webcam'}</span>
            </button>
          )}

          {/* Source 3: Recorded Video Play/Pause */}
          {sourceType === 'VIDEO' && (
            <button
              onClick={() => setIsVideoPlaying(!isVideoPlaying)}
              className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 hover:bg-indigo-500/30 transition-all text-xs font-medium"
            >
              {isVideoPlaying ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
              <span>{isVideoPlaying ? 'Pause Job' : 'Resume Job'}</span>
            </button>
          )}

          {/* Fullscreen Button */}
          <button
            onClick={toggleFullscreen}
            className="rounded-lg bg-slate-900/80 p-2 text-slate-300 border border-white/10 hover:bg-slate-800 hover:text-white transition-all"
            title="Toggle Fullscreen"
          >
            {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}
