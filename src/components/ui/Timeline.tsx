'use client';

import React from 'react';
import { TimelineActivity } from '@/types';
import { cn } from '@/lib/utils';
import { ShieldAlert, AlertTriangle, Info, Smartphone, Eye, CheckCircle2 } from 'lucide-react';

interface TimelineProps {
  activities: TimelineActivity[];
  onSelectActivity?: (activity: TimelineActivity) => void;
  className?: string;
}

export function Timeline({
  activities,
  onSelectActivity,
  className,
}: TimelineProps) {
  const getIcon = (type: string, severity: string) => {
    if (type === 'PHONE_DETECTED') return Smartphone;
    if (type === 'HEAD_MOVEMENT' || type === 'PEEKING_DETECTED') return Eye;
    if (severity === 'CRITICAL' || severity === 'HIGH') return ShieldAlert;
    if (severity === 'MEDIUM') return AlertTriangle;
    return Info;
  };

  const getMarkerColor = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return 'border-rose-500 bg-rose-950 text-rose-400 shadow-[0_0_10px_rgba(244,63,94,0.5)]';
      case 'HIGH':
        return 'border-amber-500 bg-amber-950 text-amber-400 shadow-[0_0_8px_rgba(245,158,11,0.4)]';
      case 'MEDIUM':
        return 'border-sky-500 bg-sky-950 text-sky-400';
      default:
        return 'border-emerald-500 bg-emerald-950 text-emerald-400';
    }
  };

  return (
    <div className={cn('relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-gradient-to-b before:from-cyan-500/40 before:via-slate-700/40 before:to-transparent', className)}>
      {activities.map((act) => {
        const Icon = getIcon(act.type, act.severity);
        const markerClass = getMarkerColor(act.severity);

        return (
          <div
            key={act.id}
            onClick={() => onSelectActivity && onSelectActivity(act)}
            className="group relative cursor-pointer"
          >
            {/* Timeline Marker Pin */}
            <div
              className={cn(
                'absolute -left-6 top-0.5 flex h-5 w-5 items-center justify-center rounded-full border-2 transition-transform duration-200 group-hover:scale-125 z-10',
                markerClass
              )}
            >
              <Icon className="h-2.5 w-2.5" />
            </div>

            {/* Content card */}
            <div className="rounded-xl border border-white/5 bg-slate-900/40 p-3.5 backdrop-blur-sm transition-all duration-200 group-hover:border-cyan-500/30 group-hover:bg-slate-900/70">
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-xs font-semibold text-cyan-400">
                  {act.time}
                </span>
                <span
                  className={cn(
                    'rounded-full px-2 py-0.5 text-[10px] font-bold font-mono tracking-wider',
                    act.severity === 'CRITICAL' && 'bg-rose-500/20 text-rose-300 border border-rose-500/30',
                    act.severity === 'HIGH' && 'bg-amber-500/20 text-amber-300 border border-amber-500/30',
                    act.severity === 'MEDIUM' && 'bg-sky-500/20 text-sky-300 border border-sky-500/30',
                    act.severity === 'INFO' && 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                  )}
                >
                  {act.severity}
                </span>
              </div>

              <h4 className="mt-1 text-sm font-semibold text-white group-hover:text-cyan-300 transition-colors">
                {act.title}
              </h4>

              {act.student && (
                <div className="mt-1 text-xs font-medium text-slate-300 flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-slate-500" />
                  <span>{act.student}</span>
                </div>
              )}

              <p className="mt-1 text-xs text-slate-400 leading-relaxed">
                {act.description}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
