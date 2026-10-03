'use client';

import React, { useState } from 'react';
import { Alert } from '@/types';
import { Modal } from '@/components/ui/Modal';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { CheckCircle2, XCircle, AlertTriangle, Download, Shield, Clock, MapPin, User, Cpu } from 'lucide-react';

interface EvidenceModalProps {
  alert: Alert | null;
  isOpen: boolean;
  onClose: () => void;
  onStatusChange?: (alertId: string, newStatus: 'VERIFIED' | 'DISMISSED', notes?: string) => void;
}

export function EvidenceModal({
  alert,
  isOpen,
  onClose,
  onStatusChange,
}: EvidenceModalProps) {
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (!alert) return null;

  const handleUpdate = (status: 'VERIFIED' | 'DISMISSED') => {
    setSubmitting(true);
    setTimeout(() => {
      onStatusChange?.(alert.id, status, notes || alert.reviewerNotes);
      setSubmitting(false);
      onClose();
    }, 300);
  };

  const handleDownloadSnapshot = () => {
    const link = document.createElement('a');
    link.href = alert.evidenceImage;
    link.download = `AI-Evidence-${alert.studentName}-${alert.type}-${Date.now()}.svg`;
    link.click();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Surveillance Incident Evidence Record"
      subtitle={`Incident ID: ${alert.id.toUpperCase()} • ${alert.examName}`}
      maxWidth="2xl"
      footer={
        <div className="flex flex-wrap items-center justify-between w-full gap-3">
          <button
            onClick={handleDownloadSnapshot}
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white px-3 py-2 rounded-xl border border-white/10 hover:bg-slate-800 transition-colors"
          >
            <Download className="h-3.5 w-3.5" />
            <span>Export Snapshot</span>
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handleUpdate('DISMISSED')}
              disabled={submitting}
              className="inline-flex items-center gap-1.5 text-xs font-semibold px-4 py-2 rounded-xl border border-slate-700 bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
            >
              <XCircle className="h-4 w-4 text-slate-400" />
              <span>Dismiss False Positive</span>
            </button>

            <button
              onClick={() => handleUpdate('VERIFIED')}
              disabled={submitting}
              className="inline-flex items-center gap-1.5 text-xs font-semibold px-4 py-2 rounded-xl bg-gradient-to-r from-rose-600 to-red-600 text-white hover:from-rose-500 hover:to-red-500 transition-all shadow-md shadow-rose-950/60"
            >
              <CheckCircle2 className="h-4 w-4" />
              <span>Confirm & Verify Violation</span>
            </button>
          </div>
        </div>
      }
    >
      <div className="space-y-4">
        {/* High-Resolution Evidence Frame */}
        <div className="relative overflow-hidden rounded-xl border border-white/10 bg-black aspect-video flex items-center justify-center shadow-inner">
          <img
            src={alert.evidenceImage}
            alt="AI Violation Snapshot"
            className="w-full h-full object-contain"
          />
          <div className="absolute top-2 right-2 bg-slate-950/80 px-2.5 py-1 rounded border border-white/10 text-[10px] font-mono text-cyan-400 flex items-center gap-1.5">
            <Cpu className="h-3 w-3" />
            <span>CONFIDENCE: {alert.confidence}%</span>
          </div>
        </div>

        {/* Detailed Metadata Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
          <div className="rounded-xl bg-slate-950/60 p-3 border border-white/5">
            <div className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold flex items-center gap-1">
              <User className="h-3 w-3 text-cyan-400" />
              Student
            </div>
            <div className="mt-1 font-bold text-white truncate">{alert.studentName}</div>
            <div className="text-[10px] text-slate-400 font-mono">{alert.rollNumber}</div>
          </div>

          <div className="rounded-xl bg-slate-950/60 p-3 border border-white/5">
            <div className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold flex items-center gap-1">
              <Shield className="h-3 w-3 text-rose-400" />
              Detection Type
            </div>
            <div className="mt-1 font-bold text-rose-300 truncate">{alert.typeLabel}</div>
            <div className="mt-0.5">
              <StatusBadge status={alert.severity} size="sm" showDot={false} />
            </div>
          </div>

          <div className="rounded-xl bg-slate-950/60 p-3 border border-white/5">
            <div className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold flex items-center gap-1">
              <Clock className="h-3 w-3 text-amber-400" />
              Timestamp
            </div>
            <div className="mt-1 font-bold text-white font-mono">{alert.time}</div>
            <div className="text-[10px] text-slate-400">Sept 30, 2026</div>
          </div>

          <div className="rounded-xl bg-slate-950/60 p-3 border border-white/5">
            <div className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold flex items-center gap-1">
              <MapPin className="h-3 w-3 text-emerald-400" />
              Seat Location
            </div>
            <div className="mt-1 font-bold text-emerald-300 truncate">{alert.seatNumber}</div>
            <div className="text-[10px] text-slate-400 truncate">{alert.cameraSource.split('-')[0]}</div>
          </div>
        </div>

        {/* Invigilator Notes Input */}
        <div className="rounded-xl bg-slate-950/40 p-3.5 border border-white/5">
          <label className="block text-xs font-semibold text-slate-300 mb-1.5">
            Invigilator Review Notes & Observations:
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder={alert.reviewerNotes || 'Enter proctor observations, desk inspection notes, or corroborating facts...'}
            rows={2}
            className="w-full rounded-lg bg-slate-900 border border-white/10 p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 resize-none font-sans"
          />
        </div>
      </div>
    </Modal>
  );
}
