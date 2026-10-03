'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { ExamStatus, AlertSeverity, CameraStatus } from '@/types';

type BadgeType = ExamStatus | AlertSeverity | CameraStatus | 'ONLINE' | 'OFFLINE' | 'VERIFIED' | 'PENDING' | 'DISMISSED' | 'READY' | 'TRIGGERED' | 'WARNING' | 'ALERT';

interface StatusBadgeProps {
  status: BadgeType;
  label?: string;
  size?: 'sm' | 'md' | 'lg';
  showDot?: boolean;
  className?: string;
}

export function StatusBadge({
  status,
  label,
  size = 'md',
  showDot = true,
  className,
}: StatusBadgeProps) {
  const displayLabel = label || status;

  // Determine styling based on status
  let colorStyles = 'bg-slate-800/80 text-slate-300 border-slate-700/60';
  let dotStyles = 'bg-slate-400';
  let pulse = false;

  switch (status) {
    case 'LIVE':
    case 'ONLINE':
    case 'VERIFIED':
    case 'READY':
      colorStyles = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      dotStyles = 'bg-emerald-400';
      pulse = status === 'LIVE' || status === 'ONLINE';
      break;

    case 'CRITICAL':
    case 'TRIGGERED':
    case 'ALERT':
      colorStyles = 'bg-rose-500/15 text-rose-400 border-rose-500/40 shadow-sm shadow-rose-950/50';
      dotStyles = 'bg-rose-500';
      pulse = true;
      break;

    case 'HIGH':
    case 'WARNING':
      colorStyles = 'bg-amber-500/15 text-amber-400 border-amber-500/30';
      dotStyles = 'bg-amber-400';
      pulse = status === 'HIGH';
      break;

    case 'MEDIUM':
    case 'CONNECTING':
      colorStyles = 'bg-sky-500/10 text-sky-400 border-sky-500/30';
      dotStyles = 'bg-sky-400';
      pulse = status === 'CONNECTING';
      break;

    case 'LOW':
    case 'SCHEDULED':
      colorStyles = 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30';
      dotStyles = 'bg-indigo-400';
      break;

    case 'OFFLINE':
    case 'DISMISSED':
    case 'COMPLETED':
      colorStyles = 'bg-zinc-800/60 text-zinc-400 border-zinc-700/40';
      dotStyles = 'bg-zinc-500';
      break;

    case 'PENDING':
      colorStyles = 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30';
      dotStyles = 'bg-yellow-400';
      pulse = true;
      break;
  }

  const sizeClasses = {
    sm: 'text-[11px] px-2 py-0.5 gap-1.5',
    md: 'text-xs px-2.5 py-1 gap-1.5 font-medium',
    lg: 'text-sm px-3 py-1.5 gap-2 font-semibold',
  }[size];

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border transition-all select-none',
        colorStyles,
        sizeClasses,
        className
      )}
    >
      {showDot && (
        <span className="relative flex h-2 w-2 items-center justify-center">
          {pulse && (
            <span
              className={cn(
                'absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping',
                dotStyles
              )}
            />
          )}
          <span className={cn('relative inline-flex rounded-full h-1.5 w-1.5', dotStyles)} />
        </span>
      )}
      <span>{displayLabel}</span>
    </span>
  );
}
