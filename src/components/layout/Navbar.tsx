'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  Menu, 
  Bell, 
  Clock, 
  Cpu, 
  Radio, 
  ShieldAlert, 
  Volume2, 
  CheckCircle2,
  ExternalLink,
  ChevronRight,
  ShieldCheck,
  AlertTriangle,
  User
} from 'lucide-react';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { mockAlerts } from '@/data/mockAlerts';
import { iotService } from '@/services/iot';
import { alertService } from '@/services/alerts';
import { useStudentAuth } from '@/context/StudentContext';
import { Alert } from '@/types';
import { cn } from '@/lib/utils';

interface NavbarProps {
  onOpenMobile: () => void;
  title?: string;
  breadcrumbs?: { label: string; href?: string }[];
}

export function Navbar({ onOpenMobile, title, breadcrumbs }: NavbarProps) {
  const { student, isFaceEnrolled } = useStudentAuth();
  const [time, setTime] = useState('');
  const [showNotifications, setShowNotifications] = useState(false);
  const [buzzerTriggered, setBuzzerTriggered] = useState(false);
  const [liveAlerts, setLiveAlerts] = useState<Alert[]>(mockAlerts);

  useEffect(() => {
    async function loadAlerts() {
      const data = await alertService.getAlerts();
      if (data && data.length > 0) {
        setLiveAlerts(data);
      }
    }
    loadAlerts();

    const unsubscribe = alertService.subscribeToAlerts((newAlert) => {
      setLiveAlerts((prev) => [newAlert, ...prev]);
    });

    return () => {
      unsubscribe();
    };
  }, []);

  useEffect(() => {
    const update = () => {
      setTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleQuickBuzzer = async () => {
    setBuzzerTriggered(true);
    await iotService.sendIoTAlert({ reason: 'Manual Invigilator Trigger' });
    setTimeout(() => setBuzzerTriggered(false), 3000);
  };

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-white/5 bg-[#080c14]/80 px-4 sm:px-6 backdrop-blur-xl">
      {/* Left: Mobile Toggle & Breadcrumbs */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobile}
          className="rounded-xl border border-white/5 bg-slate-900/60 p-2 text-slate-400 hover:text-white lg:hidden"
        >
          <Menu className="h-5 w-5" />
        </button>

        {breadcrumbs && breadcrumbs.length > 0 ? (
          <nav className="flex items-center gap-1.5 text-xs text-slate-400">
            {breadcrumbs.map((crumb, idx) => (
              <React.Fragment key={crumb.label}>
                {idx > 0 && <ChevronRight className="h-3 w-3 text-slate-600" />}
                {crumb.href ? (
                  <Link
                    href={crumb.href}
                    className="hover:text-cyan-400 transition-colors"
                  >
                    {crumb.label}
                  </Link>
                ) : (
                  <span className="font-semibold text-white">{crumb.label}</span>
                )}
              </React.Fragment>
            ))}
          </nav>
        ) : (
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-white tracking-tight">
              {title || 'Smart Examination Surveillance System'}
            </span>
          </div>
        )}
      </div>

      {/* Center: Active Exam Live Pill & Face Enrollment Badge (Desktop) */}
      <div className="hidden md:flex items-center gap-2.5">
        <div className="flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1 text-xs shadow-sm">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
          </span>
          <span className="font-semibold text-white">DSGT Internal Exam</span>
          <span className="text-slate-400">•</span>
          <span className="font-mono text-emerald-400 font-bold">01:24:30</span>
        </div>

        {/* Student Face ID Status Badge */}
        {student && (
          <Link
            href="/enrollment"
            className={cn(
              'flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-mono font-semibold border transition-all duration-200 hover:scale-105',
              isFaceEnrolled
                ? 'border-emerald-500/40 bg-emerald-950/40 text-emerald-300 hover:border-emerald-400'
                : 'border-amber-500/50 bg-amber-950/40 text-amber-300 hover:border-amber-400 animate-pulse'
            )}
            title={isFaceEnrolled ? 'Face biometric profile active' : 'Biometric enrollment required'}
          >
            {isFaceEnrolled ? (
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
            ) : (
              <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
            )}
            <span>Face ID: {isFaceEnrolled ? 'Verified' : 'Required'}</span>
            <span className="text-slate-400 font-sans font-normal truncate max-w-[90px]">
              ({student.name.split(' ')[0]})
            </span>
          </Link>
        )}
      </div>

      {/* Right: Quick Actions, Clock, Notifications */}
      <div className="flex items-center gap-2.5">
        {/* Quick ESP32 Buzzer test button */}
        <button
          onClick={handleQuickBuzzer}
          disabled={buzzerTriggered}
          className={cn(
            'hidden sm:flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-semibold border transition-all duration-200',
            buzzerTriggered
              ? 'bg-rose-600 text-white border-rose-500 shadow-md shadow-rose-950/60 animate-pulse'
              : 'bg-slate-900/80 text-rose-400 border-rose-500/30 hover:bg-rose-500/10 hover:border-rose-500/50'
          )}
          title="Send immediate buzzer alarm signal to ESP32 hardware"
        >
          <Volume2 className="h-3.5 w-3.5" />
          <span>{buzzerTriggered ? 'BUZZER ACTIVE' : 'Trigger Buzzer'}</span>
        </button>

        {/* Live Clock Chip */}
        <div className="hidden lg:flex items-center gap-1.5 rounded-xl border border-white/5 bg-slate-950/60 px-3 py-1.5 text-xs font-mono text-cyan-400">
          <Clock className="h-3.5 w-3.5 text-slate-400" />
          <span>{time}</span>
        </div>

        {/* Notification Bell with Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-slate-900/80 text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
            title="Surveillance Notifications"
          >
            <Bell className="h-4 w-4" />
            <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 text-[9px] font-bold text-white shadow-sm shadow-rose-900/60">
              {liveAlerts.length}
            </span>
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl border border-white/10 bg-slate-900/95 p-4 shadow-2xl backdrop-blur-2xl z-50 animate-in fade-in slide-in-from-top-2">
              <div className="flex items-center justify-between pb-3 border-b border-white/5">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-white uppercase tracking-wider">
                    Recent AI Incidents
                  </span>
                  <span className="rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/30 px-2 py-0.5 text-[10px] font-mono font-bold">
                    {liveAlerts.length} Recorded
                  </span>
                </div>
                <Link
                  href="/alerts"
                  onClick={() => setShowNotifications(false)}
                  className="text-[11px] text-cyan-400 hover:underline font-medium"
                >
                  View All
                </Link>
              </div>

              <div className="mt-3 space-y-2.5 max-h-72 overflow-y-auto pr-1">
                {liveAlerts.slice(0, 4).map((alert) => (
                  <Link
                    key={alert.id}
                    href="/alerts"
                    onClick={() => setShowNotifications(false)}
                    className="flex items-start gap-3 rounded-xl bg-slate-950/60 p-2.5 border border-white/5 hover:border-cyan-500/30 transition-all block"
                  >
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/30">
                      <ShieldAlert className="h-3.5 w-3.5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1">
                        <span className="text-xs font-semibold text-white truncate">
                          {alert.studentName}
                        </span>
                        <span className="text-[10px] font-mono text-slate-400">
                          {alert.time}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-300 font-medium truncate">
                        {alert.typeLabel}
                      </p>
                      <span className="text-[10px] font-mono text-cyan-400">
                        {alert.confidence}% confidence
                      </span>
                    </div>
                  </Link>
                ))}
              </div>

              <div className="mt-3 pt-2.5 border-t border-white/5 flex items-center justify-between text-[11px] text-slate-400">
                <span>Hardware: ESP32 Connected</span>
                <Link
                  href="/monitoring"
                  onClick={() => setShowNotifications(false)}
                  className="text-cyan-400 hover:underline flex items-center gap-1 font-semibold"
                >
                  <span>Go to Monitoring</span>
                  <ExternalLink className="h-3 w-3" />
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
