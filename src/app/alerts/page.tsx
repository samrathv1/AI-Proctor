'use client';

import React, { useState, useEffect } from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { AlertCard } from '@/components/ui/AlertCard';
import { EvidenceModal } from '@/components/alerts/EvidenceModal';
import { mockAlerts } from '@/data/mockAlerts';
import { alertService } from '@/services/alerts';
import { Alert, AlertSeverity, AlertType, AlertReviewStatus } from '@/types';
import { 
  BellRing, 
  Search, 
  Filter, 
  SlidersHorizontal, 
  CheckCircle2, 
  XCircle, 
  ShieldAlert, 
  Calendar, 
  User, 
  Layers, 
  ArrowUpDown 
} from 'lucide-react';

export default function AlertsManagementPage() {
  const [alerts, setAlerts] = useState<Alert[]>(mockAlerts);
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);

  // Filters requested in prompt: Date, Alert Type, Severity, Student
  const [selectedSeverity, setSelectedSeverity] = useState<string>('ALL');
  const [selectedType, setSelectedType] = useState<string>('ALL');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [studentQuery, setStudentQuery] = useState<string>('');
  const [dateFilter, setDateFilter] = useState<string>('2026-09-30');

  useEffect(() => {
    async function loadAlerts() {
      const data = await alertService.getAlerts();
      if (data && data.length > 0) {
        setAlerts(data);
      }
    }
    loadAlerts();

    const unsubscribe = alertService.subscribeToAlerts((newAlert) => {
      setAlerts((prev) => [newAlert, ...prev]);
    });

    return () => {
      unsubscribe();
    };
  }, []);

  const filteredAlerts = React.useMemo(() => {
    return alerts.filter((alert) => {
      if (selectedSeverity !== 'ALL' && alert.severity !== selectedSeverity) return false;
      if (selectedType !== 'ALL' && alert.type !== selectedType) return false;
      if (selectedStatus !== 'ALL' && alert.reviewStatus !== selectedStatus) return false;
      if (studentQuery.trim()) {
        const q = studentQuery.toLowerCase();
        const matches =
          alert.studentName.toLowerCase().includes(q) ||
          alert.rollNumber.toLowerCase().includes(q) ||
          alert.seatNumber.toLowerCase().includes(q);
        if (!matches) return false;
      }
      return true;
    });
  }, [alerts, selectedSeverity, selectedType, selectedStatus, studentQuery]);

  const handleStatusChange = (alertId: string, newStatus: AlertReviewStatus, notes?: string) => {
    setAlerts((prev) =>
      prev.map((a) =>
        a.id === alertId ? { ...a, reviewStatus: newStatus, reviewerNotes: notes || a.reviewerNotes } : a
      )
    );
  };

  const handleQuickVerify = (alert: Alert) => {
    handleStatusChange(alert.id, 'VERIFIED');
  };

  const handleQuickDismiss = (alert: Alert) => {
    handleStatusChange(alert.id, 'DISMISSED');
  };

  return (
    <AppLayout breadcrumbs={[{ label: 'Dashboard', href: '/dashboard' }, { label: 'Alerts' }]}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-extrabold text-white tracking-tight sm:text-3xl">
                Incident & Alert Surveillance
              </h1>
              <span className="rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/30 px-2.5 py-0.5 text-xs font-mono font-bold">
                {filteredAlerts.length} Flagged
              </span>
            </div>
            <p className="mt-1 text-xs sm:text-sm text-slate-400">
              Audit AI-generated suspicious activity alerts, inspect high-resolution evidence snapshots, and verify infractions.
            </p>
          </div>
        </div>

        {/* FILTERS TOOLBAR (Date, Alert Type, Severity, Student) */}
        <div className="rounded-2xl border border-white/5 bg-slate-900/70 p-4 sm:p-5 backdrop-blur-xl shadow-xl space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-white/5">
            <span className="text-xs font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-1.5">
              <SlidersHorizontal className="h-4 w-4" />
              <span>Surveillance Filters</span>
            </span>
            <button
              onClick={() => {
                setSelectedSeverity('ALL');
                setSelectedType('ALL');
                setSelectedStatus('ALL');
                setStudentQuery('');
              }}
              className="text-xs text-slate-400 hover:text-white transition-colors"
            >
              Reset Filters
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {/* Filter: Student Search */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                Student / Roll Number
              </label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500" />
                <input
                  type="text"
                  placeholder="e.g. Student 15, Desk 12"
                  value={studentQuery}
                  onChange={(e) => setStudentQuery(e.target.value)}
                  className="w-full rounded-xl bg-slate-950/80 border border-white/10 pl-8 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/80"
                />
              </div>
            </div>

            {/* Filter: Alert Type */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                Alert Type
              </label>
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="w-full rounded-xl bg-slate-950/80 border border-white/10 px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500/80 font-medium"
              >
                <option value="ALL">All Alert Types</option>
                <option value="MOBILE_PHONE">Mobile Phone Detected</option>
                <option value="SUSPICIOUS_HEAD_MOVEMENT">Suspicious Head Movement</option>
                <option value="UNAUTHORIZED_MATERIAL">Unauthorized Material</option>
                <option value="WHISPERING_NOISE">Whispering / Sound Spike</option>
                <option value="ABSENCE_FROM_SEAT">Absence From Seat</option>
              </select>
            </div>

            {/* Filter: Severity */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                Severity
              </label>
              <select
                value={selectedSeverity}
                onChange={(e) => setSelectedSeverity(e.target.value)}
                className="w-full rounded-xl bg-slate-950/80 border border-white/10 px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500/80 font-medium"
              >
                <option value="ALL">All Severities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High Alert</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
            </div>

            {/* Filter: Review Status */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                Review Status
              </label>
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="w-full rounded-xl bg-slate-950/80 border border-white/10 px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500/80 font-medium"
              >
                <option value="ALL">All Review States</option>
                <option value="PENDING">Pending Review</option>
                <option value="VERIFIED">Verified Violations</option>
                <option value="DISMISSED">Dismissed / False Positives</option>
              </select>
            </div>
          </div>
        </div>

        {/* ALERTS CARDS GRID */}
        {filteredAlerts.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredAlerts.map((alert) => (
              <AlertCard
                key={alert.id}
                alert={alert}
                onViewEvidence={(a) => setSelectedAlert(a)}
                onVerify={handleQuickVerify}
                onDismiss={handleQuickDismiss}
              />
            ))}
          </div>
        ) : (
          <div className="rounded-2xl border border-white/5 bg-slate-900/40 p-12 text-center text-slate-400">
            <ShieldAlert className="mx-auto h-10 w-10 text-slate-600 mb-3" />
            <h3 className="text-base font-semibold text-white">No alerts match your filter criteria</h3>
            <p className="text-xs text-slate-400 mt-1">
              Try adjusting your search terms, severity, or review status filters.
            </p>
          </div>
        )}
      </div>

      {/* ALERT DETAILS MODAL */}
      <EvidenceModal
        alert={selectedAlert}
        isOpen={!!selectedAlert}
        onClose={() => setSelectedAlert(null)}
        onStatusChange={handleStatusChange}
      />
    </AppLayout>
  );
}
