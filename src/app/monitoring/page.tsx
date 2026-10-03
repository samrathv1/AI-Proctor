'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { AppLayout } from '@/components/layout/AppLayout';
import { VideoPlayer } from '@/components/ui/VideoPlayer';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { EvidenceModal } from '@/components/alerts/EvidenceModal';
import { mockAlerts } from '@/data/mockAlerts';
import { iotService } from '@/services/iot';
import { alertService } from '@/services/alerts';
import { Alert } from '@/types';
import { 
  Users, 
  Smartphone, 
  BookOpen, 
  ShieldAlert, 
  CheckCircle2, 
  AlertTriangle, 
  Eye, 
  Cpu, 
  Radio, 
  Sliders, 
  Volume2, 
  Layers, 
  Sparkles, 
  Maximize2 
} from 'lucide-react';

export default function LiveMonitoringPage() {
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [activeCameraId, setActiveCameraId] = useState('cam-01');
  const [buzzerActive, setBuzzerActive] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);
  const [selectedSubjectId, setSelectedSubjectId] = useState('trk-cam-01-002');

  const temporalSubjects = [
    {
      trackingId: 'trk-cam-01-002',
      shortLabel: 'Desk B4-12 (Dev)',
      seat: 'B4-12',
      studentName: 'Dev Sharma',
      rollNumber: 'CS-2026-042',
      camera: 'cam-01',
      identityStatus: 'IDENTIFIED',
      similarity: '91%',
      identityBadgeClass: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
      postureLabel: 'HEAD_TURN_LEFT (Lateral Divergence)',
      yaw: -32.4,
      pitch: 14.1,
      suspicionScore: 68,
      severity: 'HIGH',
      severityBadgeClass: 'bg-rose-500/20 text-rose-400 border border-rose-500/30',
      recommendedAction: 'REQUIRES REVIEW',
      activeEvents: [
        { type: 'SIDEWAYS_GAZE', description: 'Persistent sideways gaze towards adjacent desk', duration: '4.2s', weight: '20', isContinuous: true },
        { type: 'REPEATED_HEAD_TURN', description: 'Lateral movement towards neighboring examination desk', duration: '3 occurrences', weight: '15', isContinuous: false },
      ],
      evidenceTimeline: [
        { time: '10:14:02', label: 'SIDEWAYS_GAZE', detail: '4.2s lateral gaze divergence', duration: '4.2s' },
        { time: '10:14:17', label: 'REPEATED_HEAD_TURN', detail: '3 occurrences in 60s window', duration: 'event' },
        { time: '10:14:24', label: 'ADVISORY_INDEX', detail: 'Advisory Score: 68 (Requires Review)', duration: 'active' },
      ],
    },
    {
      trackingId: 'trk-cam-01-005',
      shortLabel: 'Desk B4-14 (Ananya)',
      seat: 'DESK B4-14',
      studentName: 'Ananya Roy',
      rollNumber: 'CS-2026-018',
      camera: 'CAM-01',
      identityStatus: 'IDENTIFIED',
      similarity: '94.5%',
      identityBadgeClass: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
      postureLabel: 'FRONTAL (Compliant)',
      yaw: 1.8,
      pitch: -1.2,
      suspicionScore: 12,
      severity: 'LOW',
      severityBadgeClass: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
      recommendedAction: 'NONE (Candidate Compliant)',
      activeEvents: [
        { type: 'FRONTAL_COMPLIANT', description: 'Normal exam posture maintained', duration: 'Active', weight: '0', isContinuous: true },
      ],
      evidenceTimeline: [
        { time: '10:00:15', label: 'Biometric verified', detail: 'Matched CS-2026-018 in active roster', duration: '0.0s' },
        { time: '10:15:00', label: 'Normal examination activity', detail: 'Writing script continuously', duration: 'active' },
      ],
    },
    {
      trackingId: 'trk-cam-02-003',
      shortLabel: 'Desk B4-15 (Rahul)',
      seat: 'DESK B4-15',
      studentName: 'Rahul Verma',
      rollNumber: 'CS-2026-031',
      camera: 'CAM-02',
      identityStatus: 'IDENTITY UNCERTAIN',
      similarity: '53%',
      identityBadgeClass: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
      postureLabel: 'LOOKING_AWAY (Frequent)',
      yaw: 22.1,
      pitch: 8.5,
      suspicionScore: 45,
      severity: 'MEDIUM',
      severityBadgeClass: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
      recommendedAction: 'ADVISORY: CONFIRM IDENTITY AT DESK B4-15',
      activeEvents: [
        { type: 'UNCERTAIN_BIOMETRIC_MATCH', description: 'Similarity 53% falls in uncertain range (45-60%)', duration: 'Persistent', weight: '25', isContinuous: true },
        { type: 'LOOKING_AWAY', description: 'Gaze diverted from exam paper', duration: '6.2s', weight: '20', isContinuous: true },
      ],
      evidenceTimeline: [
        { time: '10:02:10', label: 'IDENTITY UNCERTAIN', detail: 'SFace similarity 53% (Threshold: 60%)', duration: 'started' },
        { time: '10:14:30', label: 'LOOKING_AWAY', detail: 'Yaw: 22.1° towards aisle', duration: '6.2s' },
      ],
    },
    {
      trackingId: 'trk-cam-02-004',
      shortLabel: 'Aisle (Unknown)',
      seat: 'DESK B4-AISLE',
      studentName: 'UNKNOWN PERSON',
      rollNumber: 'N/A',
      camera: 'CAM-02',
      identityStatus: 'UNKNOWN',
      similarity: '21%',
      identityBadgeClass: 'bg-rose-500/20 text-rose-400 border border-rose-500/30',
      postureLabel: 'MOBILE_PERSON (Transiting)',
      yaw: 14.2,
      pitch: 19.5,
      suspicionScore: 50,
      severity: 'MEDIUM',
      severityBadgeClass: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
      recommendedAction: 'ADVISORY: IDENTITY VERIFICATION REQUIRED',
      activeEvents: [
        { type: 'UNKNOWN_PERSON', description: 'Face embedding does not match any enrolled roster profile', duration: '18.4s', weight: '50', isContinuous: true },
      ],
      evidenceTimeline: [
        { time: '10:13:50', label: 'Unrecognized subject in examination hall', detail: 'No match in exam roster cache (Sim: 21%)', duration: 'started' },
        { time: '10:14:08', label: 'Aisle spatial tracking', detail: 'Independent tracklet trk-cam-02-004', duration: '18.4s' },
      ],
    },
  ];

  const currentSubject = temporalSubjects.find((s) => s.trackingId === selectedSubjectId) || temporalSubjects[0];

  useEffect(() => {
    const unsubscribe = alertService.subscribeToAlerts((newAlert) => {
      setNotification(`REALTIME ALERT: ${newAlert.typeLabel || newAlert.type} (${newAlert.studentName})`);
      setTimeout(() => setNotification(null), 4000);
    });

    return () => {
      unsubscribe();
    };
  }, []);

  // Exact numbers requested in prompt:
  // Object Detection: Person: 60, Mobile: 1, Books: 60
  // Behaviour Analysis: Normal: 58, Suspicious: 2
  const detectionStats = {
    persons: 60,
    mobiles: 1,
    books: 60,
    notes: 2,
    normalBehavior: 58,
    suspiciousBehavior: 2,
  };

  const handleTriggerBuzzer = async (studentName?: string) => {
    setBuzzerActive(true);
    await iotService.sendIoTAlert({
      reason: `Flagged infraction on ${studentName || 'Student 12'}`,
      studentName: studentName || 'Student 12',
    });
    setNotification(`ESP32 hardware buzzer & alert LED dispatched to Hall 304!`);
    setTimeout(() => {
      setBuzzerActive(false);
      setNotification(null);
    }, 3500);
  };

  const cameraFeeds = [
    { id: 'webcam-01', label: 'WEBCAM', name: 'Option 1: Laptop Web Camera', fps: 30, res: '720p', type: 'WEBCAM' as const },
    { id: 'ip-cam-01', label: 'IP CCTV', name: 'Option 2: IP Camera / CCTV (RTSP Stream)', fps: 30, res: '1080p', type: 'IP_CAMERA' as const },
    { id: 'video-01', label: 'RECORDED', name: 'Option 3: Recorded Exam Video (MP4)', fps: 30, res: '1080p', type: 'VIDEO' as const },
  ];

  const currentCam = cameraFeeds.find((c) => c.id === activeCameraId) || cameraFeeds[0];

  return (
    <AppLayout breadcrumbs={[{ label: 'Dashboard', href: '/dashboard' }, { label: 'Live Monitoring' }]}>
      <div className="space-y-5">
        {/* Top Control Header */}
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
                  Real-Time AI Vision Surveillance
                </h1>
                <StatusBadge status="LIVE" label="FEED ONLINE" size="sm" />
              </div>
              <p className="mt-0.5 text-xs text-slate-400">
                DSGT Internal Examination • Hall 304 • YOLOv8 Detection + MediaPipe 3D Landmark Mesh
              </p>
            </div>
          </div>

          {/* Camera switcher tabs & hardware buzzer trigger */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center rounded-xl bg-slate-900/80 p-1 border border-white/5">
              {cameraFeeds.map((feed) => (
                <button
                  key={feed.id}
                  onClick={() => setActiveCameraId(feed.id)}
                  className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                    activeCameraId === feed.id
                      ? 'bg-cyan-500 text-slate-950 shadow-sm font-bold'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {feed.label}
                </button>
              ))}
            </div>

            <button
              onClick={() => handleTriggerBuzzer('Student 12')}
              disabled={buzzerActive}
              className={`inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-bold transition-all shadow-md ${
                buzzerActive
                  ? 'bg-rose-600 text-white animate-pulse shadow-rose-950/60'
                  : 'bg-rose-500/20 text-rose-400 border border-rose-500/40 hover:bg-rose-500 hover:text-white'
              }`}
            >
              <Volume2 className="h-4 w-4" />
              <span>{buzzerActive ? 'Buzzer Beeping...' : 'Trigger ESP32 Buzzer'}</span>
            </button>
          </div>
        </div>

        {/* MAIN PRODUCT SCREEN LAYOUT:
            LEFT / CENTER: Large Video Monitoring Area + AI Overlay Area
            RIGHT: AI Detection Panel
        */}
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
          {/* LEFT & CENTER: Large Video Area with AI Overlays (8 Cols on XL) */}
          <div className="xl:col-span-8 space-y-4">
            <VideoPlayer
              cameraName={currentCam.name}
              sourceType={currentCam.type}
              showDetections={true}
              onAlertTriggered={(info) => {
                const found = mockAlerts.find((a) => a.studentName.includes(info.student)) || mockAlerts[0];
                setSelectedAlert(found);
              }}
            />

            {/* Quick Stream & Hardware Telemetry Bar */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              <div className="rounded-xl bg-slate-900/60 p-3 border border-white/5 flex items-center gap-3">
                <div className="h-8 w-8 rounded-lg bg-cyan-500/10 text-cyan-400 flex items-center justify-center border border-cyan-500/20">
                  <Cpu className="h-4 w-4" />
                </div>
                <div>
                  <div className="text-[10px] uppercase font-bold text-slate-400">Inference Time</div>
                  <div className="text-xs font-bold text-white font-mono">18ms / Frame</div>
                </div>
              </div>

              <div className="rounded-xl bg-slate-900/60 p-3 border border-white/5 flex items-center gap-3">
                <div className="h-8 w-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center border border-emerald-500/20">
                  <Radio className="h-4 w-4" />
                </div>
                <div>
                  <div className="text-[10px] uppercase font-bold text-slate-400">Stream Protocol</div>
                  <div className="text-xs font-bold text-emerald-400 font-mono">WebRTC H.264</div>
                </div>
              </div>

              <div className="rounded-xl bg-slate-900/60 p-3 border border-white/5 flex items-center gap-3">
                <div className="h-8 w-8 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center border border-amber-500/20">
                  <ShieldAlert className="h-4 w-4" />
                </div>
                <div>
                  <div className="text-[10px] uppercase font-bold text-slate-400">Vision Model</div>
                  <div className="text-xs font-bold text-white font-mono">YuNet + YOLOv8n</div>
                </div>
              </div>

              <div className="rounded-xl bg-slate-900/60 p-3 border border-white/5 flex items-center gap-3">
                <div className="h-8 w-8 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center border border-indigo-500/20">
                  <Eye className="h-4 w-4" />
                </div>
                <div>
                  <div className="text-[10px] uppercase font-bold text-slate-400">Head Pose (solvePnP)</div>
                  <div className="text-xs font-bold text-indigo-400 font-mono">0.8ms Euler Angle</div>
                </div>
              </div>

              <div className="rounded-xl bg-slate-900/60 p-3 border border-emerald-500/30 flex items-center gap-3 col-span-2 sm:col-span-1 shadow-lg shadow-emerald-950/20">
                <div className="h-8 w-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center border border-emerald-500/20 relative">
                  <span className="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
                  <Radio className="h-4 w-4" />
                </div>
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] uppercase font-extrabold text-emerald-400">ONLINE</span>
                    <span className="text-[9px] font-mono text-slate-400">• ACK: 24ms</span>
                  </div>
                  <div className="text-xs font-bold text-white font-mono truncate">ESP32-HALL304-01</div>
                  <div className="text-[9px] text-slate-400 font-mono">GPIO 27 LED • GPIO 15 Buzz</div>
                </div>
              </div>
            </div>

            {/* TEMPORAL BEHAVIOUR & ADVISORY EVIDENCE TIMELINE */}
            <div className="rounded-2xl border border-white/5 bg-slate-900/70 p-5 backdrop-blur-xl shadow-xl space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-white/5 gap-2">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    Observable Event Analysis & Track Correlation
                  </h3>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/50 px-2 py-0.5 rounded border border-cyan-800/40">
                    60s ROLLING WINDOW
                  </span>
                  {/* Interactive Subject Switcher */}
                  <div className="flex items-center bg-slate-950/80 rounded-lg p-0.5 border border-white/10">
                    {temporalSubjects.map((sub) => (
                      <button
                        key={sub.trackingId}
                        onClick={() => setSelectedSubjectId(sub.trackingId)}
                        className={`px-2 py-1 text-[10px] font-bold rounded transition-all ${
                          selectedSubjectId === sub.trackingId
                            ? 'bg-cyan-500 text-slate-950 shadow-sm'
                            : 'text-slate-400 hover:text-white'
                        }`}
                      >
                        {sub.shortLabel}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Subject Details Header: Desk, Student, Roll, Camera, Identity, Advisory */}
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                <div className="rounded-xl bg-slate-950/60 p-3 border border-white/5">
                  <div className="text-[10px] font-mono uppercase text-slate-400">Desk & Camera</div>
                  <div className="text-xs font-bold text-cyan-300 font-mono mt-1">{currentSubject.seat}</div>
                  <div className="text-[10px] font-mono text-slate-400 mt-0.5">Camera: {currentSubject.camera}</div>
                </div>

                <div className="rounded-xl bg-slate-950/60 p-3 border border-white/5">
                  <div className="text-[10px] font-mono uppercase text-slate-400">Candidate Identity</div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs font-bold text-white truncate">{currentSubject.studentName}</span>
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded shrink-0 ${currentSubject.identityBadgeClass}`}>
                      {currentSubject.identityStatus}
                    </span>
                  </div>
                  <div className="text-[10px] font-mono text-slate-400 mt-0.5">
                    Roll: {currentSubject.rollNumber} • Track: {currentSubject.trackingId}
                  </div>
                </div>

                <div className="rounded-xl bg-slate-950/60 p-3 border border-white/5">
                  <div className="text-[10px] font-mono uppercase text-slate-400">Head Pose (solvePnP)</div>
                  <div className="text-xs font-bold text-white mt-1 truncate">
                    {currentSubject.postureLabel}
                  </div>
                  <div className="text-[10px] font-mono text-slate-400 mt-0.5">
                    Yaw: {currentSubject.yaw}° • Pitch: {currentSubject.pitch}°
                  </div>
                </div>

                <div className="rounded-xl bg-slate-950/60 p-3 border border-white/5">
                  <div className="text-[10px] font-mono uppercase text-slate-400">Advisory Score</div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-sm font-black font-mono text-white">{currentSubject.suspicionScore}/100</span>
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${currentSubject.severityBadgeClass}`}>
                      {currentSubject.severity}
                    </span>
                  </div>
                  <div className="text-[10px] text-slate-400 mt-0.5 truncate">{currentSubject.recommendedAction}</div>
                </div>
              </div>

              {/* Active Observable Events with Continuous Duration */}
              <div>
                <div className="text-[11px] font-bold uppercase tracking-wider text-slate-300 mb-2 flex items-center justify-between">
                  <span>Current Observable Events</span>
                  <span className="text-[10px] font-normal text-slate-400 font-mono">Anti-Double Counting Active</span>
                </div>
                <div className="space-y-2">
                  {currentSubject.activeEvents.map((ev, idx) => (
                    <div
                      key={idx}
                      className="rounded-xl bg-slate-950/70 p-2.5 border border-white/5 flex items-center justify-between"
                    >
                      <div className="flex items-center gap-2.5">
                        <div className={`h-2 w-2 rounded-full ${ev.isContinuous ? 'bg-amber-400 animate-ping' : 'bg-slate-400'}`} />
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-white font-mono">{ev.type}</span>
                            {Number(ev.weight) >= 30 ? (
                              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/30">
                                CRITICAL ALERT
                              </span>
                            ) : Number(ev.weight) >= 12 ? (
                              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">
                                ADVISORY EVENT
                              </span>
                            ) : (
                              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                                INFORMATIONAL
                              </span>
                            )}
                          </div>
                          <div className="text-[10px] text-slate-400">{ev.description}</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-xs font-mono font-bold text-cyan-400">{ev.duration}</div>
                        <div className="text-[10px] text-slate-400 font-mono">Weight: +{ev.weight}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Chronological Evidence Timeline */}
              <div>
                <div className="text-[11px] font-bold uppercase tracking-wider text-slate-300 mb-2">
                  Chronological Evidence Timeline
                </div>
                <div className="rounded-xl bg-slate-950/70 p-3 border border-white/5 space-y-2.5 max-h-48 overflow-y-auto">
                  {currentSubject.evidenceTimeline.map((item, idx) => (
                    <div key={idx} className="flex items-start gap-2.5 text-[11px] border-l-2 border-cyan-500/40 pl-2.5 py-0.5">
                      <span className="font-mono text-slate-400 whitespace-nowrap">{item.time}</span>
                      <div className="flex-1">
                        <span className="font-bold text-slate-200">{item.label}</span>
                        <span className="text-slate-400 ml-1.5">{item.detail}</span>
                      </div>
                      {item.duration && (
                        <span className="font-mono text-cyan-400 whitespace-nowrap text-[10px]">{item.duration}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* RIGHT: AI DETECTION PANEL (4 Cols on XL) */}
          <div className="xl:col-span-4 space-y-5">
            {/* 0. LIVE BIOMETRIC IDENTITY MATCHING & TRACKING */}
            <div className="rounded-2xl border border-white/5 bg-slate-900/70 p-5 backdrop-blur-xl shadow-xl space-y-3.5">
              <div className="flex items-center justify-between pb-3 border-b border-white/5">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    Biometric Identity Matching
                  </h3>
                </div>
                <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/50 px-2 py-0.5 rounded border border-emerald-800/40">
                  EXAM ROSTER CACHE
                </span>
              </div>

              <div className="space-y-2.5">
                {/* Dev Sharma - IDENTIFIED */}
                <div className="rounded-xl bg-slate-950/60 p-3 border border-emerald-500/20 hover:border-emerald-500/40 transition-all">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-white">Dev Sharma</span>
                      <span className="text-[10px] font-mono text-slate-400">CS-2026-042</span>
                    </div>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                      VERIFIED
                    </span>
                  </div>
                  <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
                    <span className="font-mono text-cyan-400">TRACK-017</span>
                    <span className="font-mono text-emerald-400 font-semibold">Similarity: 91%</span>
                  </div>
                </div>

                {/* Ananya Roy - IDENTIFIED */}
                <div className="rounded-xl bg-slate-950/60 p-3 border border-emerald-500/20 hover:border-emerald-500/40 transition-all">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-white">Ananya Roy</span>
                      <span className="text-[10px] font-mono text-slate-400">CS-2026-018</span>
                    </div>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                      VERIFIED
                    </span>
                  </div>
                  <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
                    <span className="font-mono text-cyan-400">TRACK-018</span>
                    <span className="font-mono text-emerald-400 font-semibold">Similarity: 88%</span>
                  </div>
                </div>

                {/* Candidate - UNCERTAIN */}
                <div className="rounded-xl bg-slate-950/60 p-3 border border-amber-500/20 hover:border-amber-500/40 transition-all">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-amber-200">Candidate Desk 19</span>
                      <span className="text-[10px] font-mono text-amber-400/80">Cand: Rahul V.</span>
                    </div>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">
                      UNCERTAIN
                    </span>
                  </div>
                  <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
                    <span className="font-mono text-cyan-400">TRACK-021</span>
                    <span className="font-mono text-amber-400 font-semibold">Similarity: 53%</span>
                  </div>
                </div>

                {/* UNKNOWN PERSON */}
                <div className="rounded-xl bg-slate-950/60 p-3 border border-rose-500/20 hover:border-rose-500/40 transition-all">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-rose-200">Unknown Person</span>
                      <span className="text-[10px] font-mono text-slate-400">No Roster Match</span>
                    </div>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/30">
                      UNKNOWN PERSON
                    </span>
                  </div>
                  <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
                    <span className="font-mono text-cyan-400">TRACK-024</span>
                    <span className="font-mono text-slate-400 font-semibold">Similarity: 24%</span>
                  </div>
                </div>
              </div>
            </div>

            {/* 1. OBJECT DETECTION METRICS */}
            <div className="rounded-2xl border border-white/5 bg-slate-900/70 p-5 backdrop-blur-xl shadow-xl space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-white/5">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-cyan-400" />
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    Object Detection
                  </h3>
                </div>
                <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/50 px-2 py-0.5 rounded border border-cyan-800/40">
                  REAL-TIME COUNTS
                </span>
              </div>

              {/* Exact Metrics requested in user prompt */}
              <div className="space-y-3">
                {/* Person: 60 */}
                <div className="flex items-center justify-between rounded-xl bg-slate-950/60 p-3 border border-white/5">
                  <div className="flex items-center gap-3">
                    <div className="h-8 w-8 rounded-lg bg-cyan-500/10 text-cyan-400 flex items-center justify-center border border-cyan-500/20">
                      <Users className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-white">Person</div>
                      <div className="text-[10px] text-slate-400">Class 0 • Students & Proctor</div>
                    </div>
                  </div>
                  <span className="font-mono text-xl font-extrabold text-cyan-400">
                    {detectionStats.persons}
                  </span>
                </div>

                {/* Mobile: 1 (Critical Flag) */}
                <div className="flex items-center justify-between rounded-xl bg-rose-950/40 p-3 border border-rose-500/30">
                  <div className="flex items-center gap-3">
                    <div className="h-8 w-8 rounded-lg bg-rose-500/20 text-rose-400 flex items-center justify-center border border-rose-500/30">
                      <Smartphone className="h-4 w-4 animate-bounce" />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-rose-200">Mobile Phone</div>
                      <div className="text-[10px] text-rose-400/80 font-mono">Student 12 • 94% Conf</div>
                    </div>
                  </div>
                  <span className="font-mono text-xl font-extrabold text-rose-400">
                    {detectionStats.mobiles}
                  </span>
                </div>

                {/* Books: 60 */}
                <div className="flex items-center justify-between rounded-xl bg-slate-950/60 p-3 border border-white/5">
                  <div className="flex items-center gap-3">
                    <div className="h-8 w-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center border border-emerald-500/20">
                      <BookOpen className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-white">Books / Question Sets</div>
                      <div className="text-[10px] text-slate-400">Standard Desk Material</div>
                    </div>
                  </div>
                  <span className="font-mono text-xl font-extrabold text-emerald-400">
                    {detectionStats.books}
                  </span>
                </div>
              </div>
            </div>

            {/* 2. BEHAVIOUR ANALYSIS METRICS */}
            <div className="rounded-2xl border border-white/5 bg-slate-900/70 p-5 backdrop-blur-xl shadow-xl space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-white/5">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-emerald-400" />
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    Behaviour Analysis
                  </h3>
                </div>
                <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/50 px-2 py-0.5 rounded border border-emerald-800/40">
                  MEDIAPIPE YAW & PITCH
                </span>
              </div>

              {/* Exact Metrics: Normal: 58, Suspicious: 2 */}
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-xl bg-slate-950/60 p-3.5 border border-emerald-500/20 text-center">
                  <div className="flex items-center justify-center gap-1.5 text-xs font-semibold text-emerald-400">
                    <CheckCircle2 className="h-4 w-4" />
                    <span>Normal</span>
                  </div>
                  <div className="mt-2 text-2xl font-black text-white font-mono">
                    {detectionStats.normalBehavior}
                  </div>
                  <div className="text-[10px] text-slate-400 mt-0.5">Compliant Candidates</div>
                </div>

                <div className="rounded-xl bg-slate-950/60 p-3.5 border border-rose-500/30 text-center">
                  <div className="flex items-center justify-center gap-1.5 text-xs font-semibold text-rose-400">
                    <AlertTriangle className="h-4 w-4" />
                    <span>Suspicious</span>
                  </div>
                  <div className="mt-2 text-2xl font-black text-rose-400 font-mono">
                    {detectionStats.suspiciousBehavior}
                  </div>
                  <div className="text-[10px] text-slate-400 mt-0.5">Anomalous Yaw & Pitch</div>
                </div>
              </div>
            </div>

            {/* 3. ACTIVE FLAGGED CANDIDATES */}
            <div className="rounded-2xl border border-white/5 bg-slate-900/70 p-5 backdrop-blur-xl shadow-xl space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-white/5">
                <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                  Live Flagged Targets
                </h3>
                <span className="text-[10px] font-mono text-rose-400">Requires Invigilation</span>
              </div>

              <div className="space-y-2.5">
                {/* Student 12 Card */}
                <div
                  onClick={() => setSelectedAlert(mockAlerts[1])}
                  className="rounded-xl bg-slate-950/70 p-3 border border-rose-500/30 hover:border-rose-500/60 cursor-pointer transition-all flex items-start justify-between gap-2"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-white">Student 12</span>
                      <span className="text-[10px] font-mono text-cyan-400">Desk 12</span>
                    </div>
                    <div className="text-[11px] text-rose-300 font-medium mt-0.5">
                      Mobile Phone Detected [94%]
                    </div>
                  </div>
                  <button className="text-[10px] font-bold text-cyan-400 hover:underline">
                    Evidence
                  </button>
                </div>

                {/* Student 15 Card */}
                <div
                  onClick={() => setSelectedAlert(mockAlerts[0])}
                  className="rounded-xl bg-slate-950/70 p-3 border border-amber-500/30 hover:border-amber-500/60 cursor-pointer transition-all flex items-start justify-between gap-2"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-white">Student 15</span>
                      <span className="text-[10px] font-mono text-cyan-400">Desk 15</span>
                    </div>
                    <div className="text-[11px] text-amber-300 font-medium mt-0.5">
                      Mobile Phone Detected [93%]
                    </div>
                  </div>
                  <button className="text-[10px] font-bold text-cyan-400 hover:underline">
                    Evidence
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Toast Notification */}
        {notification && (
          <div className="fixed bottom-6 right-6 z-50 rounded-2xl border border-rose-500/40 bg-slate-900/95 p-4 shadow-2xl backdrop-blur-xl flex items-center gap-3 animate-in fade-in slide-in-from-bottom-2">
            <div className="h-8 w-8 rounded-full bg-rose-500/20 text-rose-400 flex items-center justify-center">
              <Volume2 className="h-5 w-5" />
            </div>
            <p className="text-xs font-semibold text-white">{notification}</p>
          </div>
        )}
      </div>

      {/* Evidence Snapshot Modal */}
      <EvidenceModal
        alert={selectedAlert}
        isOpen={!!selectedAlert}
        onClose={() => setSelectedAlert(null)}
      />
    </AppLayout>
  );
}
