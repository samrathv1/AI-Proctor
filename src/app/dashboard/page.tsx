'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { AppLayout } from '@/components/layout/AppLayout';
import { StatCard } from '@/components/ui/StatCard';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Timeline } from '@/components/ui/Timeline';
import { AlertCard } from '@/components/ui/AlertCard';
import { EvidenceModal } from '@/components/alerts/EvidenceModal';
import { mockExams } from '@/data/mockExams';
import { mockAlerts } from '@/data/mockAlerts';
import { mockActivities } from '@/data/mockActivities';
import { examService } from '@/services/exam';
import { alertService } from '@/services/alerts';
import { useStudentAuth } from '@/context/StudentContext';
import { Alert, Exam } from '@/types';
import { 
  Users, 
  Camera, 
  BellRing, 
  AlertOctagon, 
  Clock, 
  ArrowRight, 
  Play, 
  MapPin, 
  Video, 
  Radio, 
  Cpu, 
  Sparkles,
  ShieldCheck,
  Smartphone,
  CheckCircle2,
  AlertTriangle,
  UserCheck
} from 'lucide-react';

export default function DashboardPage() {
  const { student, isFaceEnrolled } = useStudentAuth();
  const [currentExam, setCurrentExam] = useState<Exam>(mockExams[0]);
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>(mockAlerts);

  useEffect(() => {
    async function loadData() {
      const exams = await examService.getExams();
      if (exams && exams.length > 0) {
        const liveExam = exams.find((e) => e.status === 'LIVE') || exams[0];
        setCurrentExam(liveExam);
      }
      const fetchedAlerts = await alertService.getAlerts();
      if (fetchedAlerts && fetchedAlerts.length > 0) {
        setAlerts(fetchedAlerts);
      }
    }
    loadData();

    // Subscribe to realtime alerts
    const unsubscribe = alertService.subscribeToAlerts((newAlert) => {
      setAlerts((prev) => [newAlert, ...prev]);
    });

    return () => {
      unsubscribe();
    };
  }, []);

  const handleStatusChange = async (alertId: string, newStatus: 'VERIFIED' | 'DISMISSED', notes?: string) => {
    await alertService.updateAlertStatus(alertId, newStatus, notes);
    setAlerts((prev) =>
      prev.map((a) =>
        a.id === alertId ? { ...a, reviewStatus: newStatus, reviewerNotes: notes || a.reviewerNotes } : a
      )
    );
  };

  return (
    <AppLayout breadcrumbs={[{ label: 'Dashboard' }]}>
      <div className="space-y-6">
        {/* Header Title & Status */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
                Surveillance Command Center
              </h1>
              <span className="flex items-center gap-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-0.5 text-xs font-mono font-semibold text-emerald-400">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                ACTIVE SESSION
              </span>
            </div>
            <p className="mt-1 text-xs sm:text-sm text-slate-400">
              Autonomous AI vision surveillance, behavioral anomaly detection & IoT hardware dispatch.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <Link
              href="/monitoring"
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold text-xs sm:text-sm px-4 py-2.5 shadow-lg shadow-cyan-950/60 transition-all hover:scale-[1.02]"
            >
              <Video className="h-4 w-4" />
              <span>Launch Live Monitoring</span>
            </Link>
          </div>
        </div>

        {/* 1. CURRENT EXAM CARD */}
        <div className="relative overflow-hidden rounded-2xl border border-cyan-500/30 bg-gradient-to-br from-slate-900/90 via-slate-900/60 to-slate-950/90 p-5 sm:p-6 backdrop-blur-xl shadow-2xl">
          {/* Subtle Cyber Grid Background */}
          <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(6,182,212,0.03)_1px,transparent_1px),linear-gradient(to_bottom,rgba(6,182,212,0.03)_1px,transparent_1px)] bg-[size:24px_24px] pointer-events-none" />
          
          <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div className="space-y-3 max-w-2xl">
              <div className="flex flex-wrap items-center gap-2.5">
                <StatusBadge status="LIVE" label="LIVE" size="md" />
                <span className="font-mono text-xs text-slate-400 bg-slate-800/80 px-2.5 py-0.5 rounded-full border border-slate-700">
                  Code: {currentExam.code}
                </span>
                <span className="text-xs text-slate-400">
                  Hall 304 - Engineering Wing B
                </span>
              </div>

              <div>
                <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                  {currentExam.title}
                </h2>
                <p className="mt-1 text-xs sm:text-sm text-cyan-300/80 font-medium">
                  {currentExam.subject}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-slate-300">
                <div className="flex items-center gap-1.5 font-mono">
                  <Clock className="h-4 w-4 text-emerald-400" />
                  <span>Duration: <strong className="text-white">01:24:30</strong></span>
                  <span className="text-slate-500">/ 02:00:00</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <MapPin className="h-4 w-4 text-cyan-400" />
                  <span>{currentExam.room}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Users className="h-4 w-4 text-indigo-400" />
                  <span>Invigilator: {currentExam.invigilator}</span>
                </div>
              </div>
            </div>

            {/* Quick Action & Live Radar Widget */}
            <div className="flex flex-row lg:flex-col items-center lg:items-end justify-between gap-3 pt-4 lg:pt-0 border-t lg:border-t-0 border-white/5">
              <div className="flex items-center gap-2 rounded-xl bg-slate-950/80 px-3 py-2 border border-white/10 font-mono text-xs">
                <span className="h-2 w-2 rounded-full bg-cyan-400 animate-ping" />
                <span className="text-slate-400">AI Feed:</span>
                <span className="text-white font-bold">YOLOv8 + MediaPipe</span>
              </div>

              <div className="flex items-center gap-2">
                <Link
                  href={`/exams/${currentExam.id}`}
                  className="rounded-xl border border-white/10 bg-slate-800/80 px-3.5 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 hover:text-white transition-colors"
                >
                  Exam Details
                </Link>
                <Link
                  href="/monitoring"
                  className="inline-flex items-center gap-1.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 px-4 py-2 text-xs font-bold text-slate-950 transition-all shadow-md shadow-cyan-500/20"
                >
                  <span>Monitor Now</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            </div>
          </div>
        </div>

        {/* 1.5 CANDIDATE BIOMETRIC STATUS BANNER */}
        {student && (
          <div className="rounded-2xl border border-white/5 bg-slate-900/60 p-4 sm:p-5 backdrop-blur-xl shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3.5">
              <div className="h-11 w-11 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center font-bold text-cyan-400">
                <UserCheck className="h-5 w-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-white tracking-tight">
                    Candidate Profile: {student.name}
                  </span>
                  <span className="font-mono text-xs text-cyan-400">
                    ({student.roll_number})
                  </span>
                  {isFaceEnrolled ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-mono font-bold text-emerald-400">
                      <CheckCircle2 className="h-2.5 w-2.5" />
                      Face Enrollment ✓ Completed
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 text-[10px] font-mono font-bold text-amber-400 animate-pulse">
                      <AlertTriangle className="h-2.5 w-2.5" />
                      Face Enrollment ⚠ Required
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  Biometric Engine: SFace 128-D ONNX • Scope: exam-01 Biometric Cache • Zero Client Leakage Protected
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2.5 self-end md:self-auto">
              <Link
                href="/enrollment"
                className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-slate-800/80 hover:bg-slate-700 text-slate-200 px-3.5 py-1.5 text-xs font-semibold transition-colors"
              >
                <ShieldCheck className="h-3.5 w-3.5 text-cyan-400" />
                <span>{isFaceEnrolled ? 'Update Face Biometrics' : 'Enroll Face Now'}</span>
              </Link>
            </div>
          </div>
        )}

        {/* 2. STATISTICS CARDS (Students: 60, Cameras: 3, Alerts: 8, Critical: 2) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Students"
            value={60}
            subtitle="Registered Students"
            icon={Users}
            accentColor="cyan"
            badge="59 Present"
            trend={{ value: '98% Turnout', isPositive: true }}
          />

          <StatCard
            title="Cameras"
            value={3}
            subtitle="Active Cameras"
            icon={Camera}
            accentColor="emerald"
            badge="1080p 30FPS"
            trend={{ value: '100% Online', isPositive: true }}
          />

          <StatCard
            title="Alerts"
            value={8}
            subtitle="Generated Alerts"
            icon={BellRing}
            accentColor="amber"
            badge="YOLO Inferences"
            trend={{ value: '+2 in last 15m', isPositive: false }}
          />

          <StatCard
            title="Critical"
            value={2}
            subtitle="Require Attention"
            icon={AlertOctagon}
            accentColor="rose"
            badge="Immediate Action"
            trend={{ value: '2 Mobile Phones', isPositive: false }}
          />
        </div>

        {/* Main Grid: Live Timeline & Recent High Alerts */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* 3. LIVE ACTIVITY TIMELINE (Left 7 Cols) */}
          <div className="lg:col-span-7 rounded-2xl border border-white/5 bg-slate-900/60 p-5 sm:p-6 backdrop-blur-xl shadow-xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-white/5">
              <div>
                <h3 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
                  <span>Live Activity Timeline</span>
                  <span className="flex h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Real-time event stream from Hall 304 AI sensors
                </p>
              </div>

              <Link
                href="/monitoring"
                className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
              >
                <span>Live Feed</span>
                <ArrowRight className="h-3 w-3" />
              </Link>
            </div>

            <Timeline activities={mockActivities} />
          </div>

          {/* Right Column: Mini Live Camera Preview & Critical Attention Queue (5 Cols) */}
          <div className="lg:col-span-5 space-y-6">
            {/* Live Camera Mini-View */}
            <div className="rounded-2xl border border-white/5 bg-slate-900/60 p-5 backdrop-blur-xl shadow-xl space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-rose-500 animate-ping" />
                  <h3 className="text-sm font-bold text-white">Camera 01 Preview</h3>
                </div>
                <span className="text-[11px] font-mono text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/40">
                  Hall 304 Wide
                </span>
              </div>

              <Link
                href="/monitoring"
                className="group relative block aspect-video w-full overflow-hidden rounded-xl border border-white/10 bg-black"
              >
                {/* Simulated Snapshot */}
                <div className="absolute inset-0 bg-[#090d16] flex items-center justify-center">
                  <div className="relative text-center p-4">
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-500/20 px-2.5 py-0.5 text-[10px] font-mono font-bold text-rose-400 border border-rose-500/30">
                      <Smartphone className="h-3 w-3" />
                      YOLO DETECT: MOBILE (94%)
                    </span>
                    <div className="mt-2 text-xs font-semibold text-white group-hover:text-cyan-400 transition-colors">
                      Click to open full AI Monitoring Console →
                    </div>
                  </div>
                </div>

                <div className="absolute bottom-2 left-2 text-[10px] font-mono text-slate-400 bg-black/70 px-2 py-0.5 rounded">
                  30 FPS • 14ms
                </div>
              </Link>
            </div>

            {/* Critical Alert Cards List */}
            <div className="rounded-2xl border border-white/5 bg-slate-900/60 p-5 backdrop-blur-xl shadow-xl space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-white/5">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-white">Action Required</span>
                  <span className="rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/30 px-2 py-0.5 text-[10px] font-mono font-bold">
                    2 Critical
                  </span>
                </div>
                <Link href="/alerts" className="text-xs text-cyan-400 hover:underline">
                  View All Alerts
                </Link>
              </div>

              <div className="space-y-3">
                {alerts.slice(0, 2).map((alert) => (
                  <AlertCard
                    key={alert.id}
                    alert={alert}
                    onViewEvidence={(a) => setSelectedAlert(a)}
                    onVerify={(a) => handleStatusChange(a.id, 'VERIFIED')}
                    onDismiss={(a) => handleStatusChange(a.id, 'DISMISSED')}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Evidence Snapshot Modal */}
      <EvidenceModal
        alert={selectedAlert}
        isOpen={!!selectedAlert}
        onClose={() => setSelectedAlert(null)}
        onStatusChange={handleStatusChange}
      />
    </AppLayout>
  );
}
