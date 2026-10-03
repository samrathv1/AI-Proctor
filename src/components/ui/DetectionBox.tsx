'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { AlertCircle, Smartphone, User, HelpCircle } from 'lucide-react';

export interface DetectionBoxProps {
  id: string;
  student: string;
  label: string;
  confidence: number;
  type: 'phone' | 'person' | 'head_movement' | 'book' | 'suspicious';
  style: {
    top: string;
    left: string;
    width: string;
    height: string;
  };
  isAlert?: boolean;
  onClick?: () => void;
}

export function DetectionBox({
  student,
  label,
  confidence,
  type,
  style,
  isAlert = false,
  onClick,
}: DetectionBoxProps) {
  const colorMap = {
    phone: {
      border: 'border-rose-500',
      glow: 'shadow-[0_0_15px_rgba(244,63,94,0.4)]',
      bg: 'bg-rose-500/10',
      badge: 'bg-rose-600 text-white',
      corner: '#f43f5e',
      icon: Smartphone,
    },
    head_movement: {
      border: 'border-amber-500',
      glow: 'shadow-[0_0_15px_rgba(245,158,11,0.4)]',
      bg: 'bg-amber-500/10',
      badge: 'bg-amber-600 text-white',
      corner: '#f59e0b',
      icon: AlertCircle,
    },
    suspicious: {
      border: 'border-red-600',
      glow: 'shadow-[0_0_20px_rgba(220,38,38,0.6)] animate-pulse',
      bg: 'bg-red-500/15',
      badge: 'bg-red-600 text-white',
      corner: '#dc2626',
      icon: AlertCircle,
    },
    person: {
      border: 'border-cyan-500/70',
      glow: 'shadow-[0_0_10px_rgba(6,182,212,0.2)]',
      bg: 'bg-cyan-500/5',
      badge: 'bg-cyan-600/90 text-white',
      corner: '#06b6d4',
      icon: User,
    },
    book: {
      border: 'border-emerald-500/70',
      glow: 'shadow-[0_0_10px_rgba(16,185,129,0.2)]',
      bg: 'bg-emerald-500/5',
      badge: 'bg-emerald-600/90 text-white',
      corner: '#10b981',
      icon: HelpCircle,
    },
  }[type];

  const Icon = colorMap.icon;

  return (
    <div
      onClick={onClick}
      style={style}
      className={cn(
        'absolute z-20 cursor-pointer rounded-sm border transition-all duration-300 pointer-events-auto',
        colorMap.border,
        colorMap.bg,
        colorMap.glow,
        isAlert && 'animate-pulse'
      )}
    >
      {/* Sci-Fi Target Corner Brackets */}
      <span className="absolute -top-1 -left-1 h-2.5 w-2.5 border-t-2 border-l-2 border-inherit" />
      <span className="absolute -top-1 -right-1 h-2.5 w-2.5 border-t-2 border-r-2 border-inherit" />
      <span className="absolute -bottom-1 -left-1 h-2.5 w-2.5 border-b-2 border-l-2 border-inherit" />
      <span className="absolute -bottom-1 -right-1 h-2.5 w-2.5 border-b-2 border-r-2 border-inherit" />

      {/* Top Floating Badge */}
      <div className="absolute -top-7 left-0 flex items-center gap-1.5 whitespace-nowrap rounded px-1.5 py-0.5 shadow-md">
        <span
          className={cn(
            'flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-bold font-mono tracking-tight',
            colorMap.badge
          )}
        >
          <Icon className="h-2.5 w-2.5" />
          <span>{student}</span>
          <span className="opacity-70">|</span>
          <span>{label}</span>
          <span className="bg-black/30 rounded px-1 text-[9px]">{confidence}%</span>
        </span>
      </div>

      {/* Subtle Crosshairs in Center */}
      <div className="absolute inset-0 flex items-center justify-center opacity-30 pointer-events-none">
        <div className="h-2 w-2 rounded-full border border-current" />
      </div>
    </div>
  );
}
