'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { LucideIcon, TrendingUp, TrendingDown } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: {
    value: string;
    isPositive: boolean;
    label?: string;
  };
  accentColor?: 'cyan' | 'emerald' | 'rose' | 'amber' | 'violet';
  className?: string;
  badge?: string;
}

export function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  accentColor = 'cyan',
  className,
  badge,
}: StatCardProps) {
  const accentGlow = {
    cyan: 'from-cyan-500/10 to-transparent border-cyan-500/20 text-cyan-400 group-hover:border-cyan-500/40',
    emerald: 'from-emerald-500/10 to-transparent border-emerald-500/20 text-emerald-400 group-hover:border-emerald-500/40',
    rose: 'from-rose-500/10 to-transparent border-rose-500/20 text-rose-400 group-hover:border-rose-500/40',
    amber: 'from-amber-500/10 to-transparent border-amber-500/20 text-amber-400 group-hover:border-amber-500/40',
    violet: 'from-violet-500/10 to-transparent border-violet-500/20 text-violet-400 group-hover:border-violet-500/40',
  }[accentColor];

  const iconBg = {
    cyan: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
    emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    rose: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
    amber: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    violet: 'bg-violet-500/10 text-violet-400 border-violet-500/30',
  }[accentColor];

  return (
    <div
      className={cn(
        'group relative overflow-hidden rounded-2xl bg-slate-900/60 p-5 backdrop-blur-xl border border-white/5 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-xl',
        className
      )}
    >
      {/* Background Gradient Accent */}
      <div
        className={cn(
          'pointer-events-none absolute -inset-px bg-gradient-to-b opacity-0 transition-opacity duration-300 group-hover:opacity-100 rounded-2xl',
          accentGlow
        )}
      />

      <div className="relative z-10 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              {title}
            </span>
            {badge && (
              <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] font-medium text-slate-300 border border-slate-700">
                {badge}
              </span>
            )}
          </div>
          <div className="mt-2.5 flex items-baseline gap-2">
            <span className="text-3xl font-bold tracking-tight text-white">{value}</span>
            {trend && (
              <span
                className={cn(
                  'flex items-center text-xs font-medium',
                  trend.isPositive ? 'text-emerald-400' : 'text-rose-400'
                )}
              >
                {trend.isPositive ? (
                  <TrendingUp className="mr-0.5 h-3.5 w-3.5" />
                ) : (
                  <TrendingDown className="mr-0.5 h-3.5 w-3.5" />
                )}
                {trend.value}
              </span>
            )}
          </div>
          {subtitle && (
            <p className="mt-1.5 text-xs text-slate-400 font-medium">{subtitle}</p>
          )}
        </div>

        <div className={cn('rounded-xl p-3 border shadow-inner transition-transform group-hover:scale-105', iconBg)}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}
