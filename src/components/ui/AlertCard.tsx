'use client';

import React from 'react';
import { Alert } from '@/types';
import { StatusBadge } from './StatusBadge';
import { ShieldAlert, Clock, Eye, MapPin, CheckCircle2, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AlertCardProps {
  alert: Alert;
  onViewEvidence: (alert: Alert) => void;
  onVerify?: (alert: Alert) => void;
  onDismiss?: (alert: Alert) => void;
  className?: string;
}

export function AlertCard({
  alert,
  onViewEvidence,
  onVerify,
  onDismiss,
  className,
}: AlertCardProps) {
  const isCritical = alert.severity === 'CRITICAL' || alert.severity === 'HIGH';

  return (
    <div
      className={cn(
        'group relative overflow-hidden rounded-xl border bg-slate-900/70 p-4 backdrop-blur-md transition-all duration-200 hover:border-slate-600',
        isCritical ? 'border-rose-500/30 hover:border-rose-500/50' : 'border-white/10',
        className
      )}
    >
      {/* Top row: Severity badge & Timestamp */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <StatusBadge
            status={alert.severity}
            label={alert.severity === 'CRITICAL' ? 'CRITICAL ALERT' : `${alert.severity} ALERT`}
            size="sm"
          />
          <StatusBadge
            status={alert.reviewStatus}
            size="sm"
            showDot={false}
          />
        </div>
        <div className="flex items-center text-xs text-slate-400 gap-1 font-mono">
          <Clock className="h-3.5 w-3.5 text-slate-500" />
          <span>{alert.time}</span>
        </div>
      </div>

      {/* Main info */}
      <div className="mt-3 flex items-start gap-3">
        <div className={cn(
          'flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border',
          isCritical ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
        )}>
          <ShieldAlert className="h-5 w-5" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className="font-semibold text-white text-sm truncate">
              {alert.studentName}
            </h4>
            <span className="text-xs text-slate-400 font-mono">
              ({alert.rollNumber})
            </span>
          </div>

          <p className="mt-0.5 text-xs font-medium text-slate-200">
            {alert.typeLabel}
          </p>

          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-400">
            <span className="flex items-center gap-1">
              <MapPin className="h-3 w-3 text-slate-500" />
              {alert.seatNumber}
            </span>
            <span>•</span>
            <span className="font-mono text-cyan-400">
              Confidence: {alert.confidence}%
            </span>
          </div>
        </div>
      </div>

      {/* Bottom actions */}
      <div className="mt-3.5 pt-3 border-t border-white/5 flex items-center justify-between gap-2">
        <div className="text-[11px] text-slate-400 truncate max-w-[200px]">
          Source: <span className="text-slate-300">{alert.cameraSource.split('-')[0]}</span>
        </div>

        <div className="flex items-center gap-1.5">
          {onVerify && alert.reviewStatus === 'PENDING' && (
            <button
              onClick={() => onVerify(alert)}
              title="Verify Violation"
              className="inline-flex items-center justify-center rounded-lg p-1.5 text-emerald-400 hover:bg-emerald-500/10 transition-colors"
            >
              <CheckCircle2 className="h-4 w-4" />
            </button>
          )}

          {onDismiss && alert.reviewStatus === 'PENDING' && (
            <button
              onClick={() => onDismiss(alert)}
              title="Dismiss False Positive"
              className="inline-flex items-center justify-center rounded-lg p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              <XCircle className="h-4 w-4" />
            </button>
          )}

          <button
            onClick={() => onViewEvidence(alert)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 px-3 py-1.5 text-xs font-semibold transition-all hover:border-cyan-500/50 shadow-sm"
          >
            <Eye className="h-3.5 w-3.5" />
            <span>View Evidence</span>
          </button>
        </div>
      </div>
    </div>
  );
}
