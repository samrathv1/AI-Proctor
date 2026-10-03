'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { AppLayout } from '@/components/layout/AppLayout';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { DataTable, Column } from '@/components/ui/DataTable';
import { examService } from '@/services/exam';
import { mockExams } from '@/data/mockExams';
import { Exam, Student, ExamSummary, StudentRosterItem } from '@/types';
import { FaceEnrollmentModal } from '@/components/enrollment/FaceEnrollmentModal';
import { 
  GraduationCap, 
  ArrowLeft, 
  Play, 
  Square, 
  FileText, 
  Calendar, 
  Clock, 
  Users, 
  ShieldAlert, 
  Video, 
  CheckCircle2, 
  AlertTriangle,
  Camera,
  MapPin,
  UserPlus,
  Radio,
  CheckCircle,
  HelpCircle,
  XCircle,
  Trash2
} from 'lucide-react';

export default function ExamDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const examId = (params?.id as string) || 'exam-01';

  const [exam, setExam] = useState<Exam | null>(null);
  const [roster, setRoster] = useState<StudentRosterItem[]>([]);
  const [summary, setSummary] = useState<ExamSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [enrollingStudent, setEnrollingStudent] = useState<Student | null>(null);
  const [isAddStudentOpen, setIsAddStudentOpen] = useState(false);
  const [newStudentId, setNewStudentId] = useState('');
  const [newSeatNumber, setNewSeatNumber] = useState('B4-16');
  const [newCameraId, setNewCameraId] = useState('cam-01');

  const loadData = async () => {
    try {
      const data = await examService.getExamById(examId);
      if (data) {
        setExam(data);
      } else {
        setExam(mockExams[0]);
      }

      const ros = await examService.getExamRoster(examId);
      setRoster(ros);

      if (data?.status === 'ENDED' || data?.status === 'COMPLETED') {
        const sum = await examService.getExamSummary(examId);
        setSummary(sum);
      }
    } catch (e) {
      console.warn('Error loading exam details:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [examId]);

  const handleStartExam = async () => {
    if (!exam) return;
    setActionLoading(true);
    setActionMessage('Validating exam roster, mounting SFace biometrics, and initiating surveillance...');
    try {
      const result = await examService.startExam(exam.id);
      setExam((prev) => prev ? { ...prev, status: 'LIVE' } : null);
      setActionMessage('Exam is now LIVE. Biometric cache mounted for enrolled candidates.');
      setTimeout(() => setActionMessage(null), 4000);
      await loadData();
    } catch (err: any) {
      alert(`Could not start exam: ${err.message}`);
      setActionMessage(null);
    } finally {
      setActionLoading(false);
    }
  };

  const handleEndExam = async () => {
    if (!exam) return;
    if (!confirm('Are you sure you want to end this examination? Active cameras and hardware beacons will be reset to safe standby.')) {
      return;
    }
    setActionLoading(true);
    setActionMessage('Stopping surveillance session, preserving evidence, and resetting hardware beacons...');
    try {
      const result = await examService.endExam(exam.id);
      setExam((prev) => prev ? { ...prev, status: 'ENDED' } : null);
      setActionMessage('Examination concluded. Hardware reset to safe state.');
      setTimeout(() => setActionMessage(null), 4000);
      await loadData();
    } catch (err: any) {
      alert(`Could not end exam: ${err.message}`);
      setActionMessage(null);
    } finally {
      setActionLoading(false);
    }
  };

  const handleAddStudent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newStudentId.trim()) return;
    try {
      await examService.addStudentToRoster(examId, {
        student_id: newStudentId.trim(),
        seat_number: newSeatNumber.trim(),
        camera_id: newCameraId,
      });
      setIsAddStudentOpen(false);
      setNewStudentId('');
      await loadData();
    } catch (err: any) {
      alert(`Failed to add student: ${err.message}`);
    }
  };

  const handleRemoveStudent = async (studentId: string) => {
    if (!confirm('Remove this student from the active exam roster?')) return;
    try {
      await examService.removeStudentFromRoster(examId, studentId);
      await loadData();
    } catch (err: any) {
      alert(`Failed to remove student: ${err.message}`);
    }
  };

  if (loading || !exam) {
    return (
      <AppLayout breadcrumbs={[{ label: 'Exams', href: '/exams' }, { label: 'Loading...' }]}>
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
        </div>
      </AppLayout>
    );
  }

  const rosterColumns: Column<StudentRosterItem>[] = [
    {
      key: 'name',
      header: 'Candidate Name',
      render: (st) => (
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-800 text-xs font-bold text-cyan-400 border border-white/5">
            {st.name.split(' ').map((n) => n[0]).slice(0, 2).join('').toUpperCase()}
          </div>
          <div>
            <div className="font-semibold text-white text-xs">{st.name}</div>
            <div className="text-[10px] text-slate-400 font-mono">{st.email || `ID: ${st.student_id}`}</div>
          </div>
        </div>
      ),
    },
    {
      key: 'roll_number',
      header: 'Roll No',
      render: (st) => <span className="font-mono text-cyan-300 font-medium">{st.roll_number}</span>,
    },
    {
      key: 'seat_number',
      header: 'Assigned Desk',
      render: (st) => (
        <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-200 border border-white/5">
          {st.seat_number || 'Unassigned'}
        </span>
      ),
    },
    {
      key: 'camera_id',
      header: 'Camera Coverage',
      render: (st) => (
        <span className="font-mono text-xs text-indigo-300">
          {st.camera_id ? st.camera_id.toUpperCase() : 'CAM-01'}
        </span>
      ),
    },
    {
      key: 'enrollment_status',
      header: 'Biometric Status',
      render: (st) => {
        const isEnrolled = st.enrollment_status === 'ENROLLED' || st.face_verified || st.face_enrolled;
        return isEnrolled ? (
          <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-bold font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <CheckCircle className="h-3 w-3" />
            <span>ENROLLED {st.quality_score ? `(${Math.round(st.quality_score)}%)` : ''}</span>
          </div>
        ) : (
          <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-bold font-mono bg-amber-500/10 text-amber-400 border border-amber-500/30">
            <HelpCircle className="h-3 w-3" />
            <span>PENDING</span>
          </div>
        );
      },
    },
    {
      key: 'attendance_status',
      header: 'Monitoring State',
      render: (st) => (
        <span
          className={`rounded-full px-2 py-0.5 text-[10px] font-bold font-mono ${
            st.attendance_status === 'FLAGGED'
              ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
              : st.attendance_status === 'PRESENT'
              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
              : 'bg-zinc-800 text-zinc-400 border border-zinc-700'
          }`}
        >
          {st.attendance_status || 'REGISTERED'}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (st) => (
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              setEnrollingStudent({
                id: st.student_id,
                name: st.name,
                rollNumber: st.roll_number,
                seatNumber: st.seat_number || 'B4-12',
                email: st.email || '',
                examId: examId,
                status: 'PRESENT',
                riskScore: 0,
                alertsCount: 0,
                avatar: st.name.slice(0, 2).toUpperCase(),
              });
            }}
            className="inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] font-semibold bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 transition-colors"
          >
            <Camera className="h-3 w-3" />
            <span>Enroll</span>
          </button>
          <button
            onClick={() => handleRemoveStudent(st.student_id)}
            title="Remove from roster"
            className="p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <AppLayout
      breadcrumbs={[
        { label: 'Dashboard', href: '/dashboard' },
        { label: 'Exams', href: '/exams' },
        { label: exam.title },
      ]}
    >
      <div className="space-y-6">
        {/* Status Notification Banner */}
        {actionMessage && (
          <div className="rounded-xl border border-cyan-500/40 bg-cyan-500/10 p-3.5 text-xs text-cyan-200 flex items-center gap-2 font-mono">
            <Radio className="h-4 w-4 text-cyan-400 animate-spin" />
            <span>{actionMessage}</span>
          </div>
        )}

        {/* Header Navigation & Lifecycle Actions */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <Link
              href="/exams"
              className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-cyan-400 transition-colors mb-2"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>Back to Sessions</span>
            </Link>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-extrabold text-white tracking-tight sm:text-3xl">
                {exam.title}
              </h1>
              <StatusBadge status={exam.status} size="md" />
            </div>
            <p className="mt-1 text-xs sm:text-sm text-cyan-300 font-medium">
              {exam.subject} ({exam.code}) • Room: {exam.room}
            </p>
          </div>

          {/* Invigilator Exam Lifecycle Actions */}
          <div className="flex flex-wrap items-center gap-2.5">
            {exam.status !== 'LIVE' && exam.status !== 'ENDED' && (
              <button
                onClick={handleStartExam}
                disabled={actionLoading}
                className="inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-xs sm:text-sm font-bold bg-emerald-500 hover:bg-emerald-400 text-slate-950 shadow-lg shadow-emerald-950/60 transition-all disabled:opacity-50"
              >
                <Play className="h-4 w-4" />
                <span>START EXAM</span>
              </button>
            )}

            {exam.status === 'LIVE' && (
              <button
                onClick={handleEndExam}
                disabled={actionLoading}
                className="inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-xs sm:text-sm font-bold bg-rose-600 hover:bg-rose-500 text-white shadow-lg shadow-rose-950/60 transition-all disabled:opacity-50"
              >
                <Square className="h-4 w-4" />
                <span>END EXAM</span>
              </button>
            )}

            {/* Launch Monitoring View */}
            <Link
              href="/monitoring"
              className="inline-flex items-center gap-1.5 rounded-xl border border-cyan-500/40 bg-cyan-500/10 px-4 py-2.5 text-xs sm:text-sm font-bold text-cyan-300 hover:bg-cyan-500/20 transition-all"
            >
              <Video className="h-4 w-4" />
              <span>Live Console</span>
            </Link>

            {/* Alerts Center */}
            <Link
              href="/alerts"
              className="inline-flex items-center gap-1.5 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-2.5 text-xs sm:text-sm font-semibold text-rose-300 hover:bg-rose-500/20 transition-colors"
            >
              <ShieldAlert className="h-4 w-4" />
              <span>Alert Center</span>
            </Link>
          </div>
        </div>

        {/* Exam Information Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-2xl border border-white/5 bg-slate-900/60 p-4 backdrop-blur-xl">
            <div className="flex items-center gap-2 text-xs text-slate-400 font-semibold uppercase tracking-wider">
              <Calendar className="h-4 w-4 text-cyan-400" />
              Date & Schedule
            </div>
            <div className="mt-2 text-base font-bold text-white">{exam.date}</div>
            <div className="text-xs text-slate-400 font-mono mt-0.5">
              {exam.startTime} – {exam.endTime}
            </div>
          </div>

          <div className="rounded-2xl border border-white/5 bg-slate-900/60 p-4 backdrop-blur-xl">
            <div className="flex items-center gap-2 text-xs text-slate-400 font-semibold uppercase tracking-wider">
              <Clock className="h-4 w-4 text-emerald-400" />
              Duration
            </div>
            <div className="mt-2 text-base font-bold text-white">{exam.durationMinutes} Minutes</div>
            <div className="text-xs text-emerald-400 font-mono mt-0.5">
              Status: {exam.status}
            </div>
          </div>

          <div className="rounded-2xl border border-white/5 bg-slate-900/60 p-4 backdrop-blur-xl">
            <div className="flex items-center gap-2 text-xs text-slate-400 font-semibold uppercase tracking-wider">
              <Users className="h-4 w-4 text-indigo-400" />
              Candidate Roster
            </div>
            <div className="mt-2 text-base font-bold text-white">
              {roster.length} Assigned Candidates
            </div>
            <div className="text-xs text-slate-400 mt-0.5">
              Authoritative Biometric Scope
            </div>
          </div>

          <div className="rounded-2xl border border-white/5 bg-slate-900/60 p-4 backdrop-blur-xl">
            <div className="flex items-center gap-2 text-xs text-slate-400 font-semibold uppercase tracking-wider">
              <Camera className="h-4 w-4 text-rose-400" />
              Hardware & Beacons
            </div>
            <div className="mt-2 text-base font-bold text-emerald-400 font-mono flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>ESP32-HALL304-01 ONLINE</span>
            </div>
            <div className="text-xs text-slate-400 mt-0.5">
              GPIO 27 LED • GPIO 15 Buzzer
            </div>
          </div>
        </div>

        {/* OFFICIAL EXAM COMPLETION SUMMARY CARD (When ENDED) */}
        {exam.status === 'ENDED' && summary && (
          <div className="rounded-2xl border border-emerald-500/30 bg-emerald-950/20 p-6 backdrop-blur-xl space-y-4">
            <div className="flex items-center justify-between border-b border-emerald-500/20 pb-3">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-emerald-400" />
                <h3 className="text-base font-extrabold text-white uppercase tracking-wider">
                  Official Examination Completion Summary
                </h3>
              </div>
              <span className="text-[11px] font-mono bg-emerald-500/20 text-emerald-300 px-2.5 py-0.5 rounded border border-emerald-500/30">
                {summary.reporting_standard}
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
              <div className="p-3 rounded-xl bg-slate-900/80 border border-white/5">
                <div className="text-slate-400 uppercase text-[10px]">Candidates Enrolled</div>
                <div className="text-base font-bold text-white mt-1">{summary.total_students_enrolled}</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/80 border border-white/5">
                <div className="text-slate-400 uppercase text-[10px]">Camera Sources</div>
                <div className="text-base font-bold text-white mt-1">{summary.camera_sources_count}</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/80 border border-white/5">
                <div className="text-slate-400 uppercase text-[10px]">Observable Events</div>
                <div className="text-base font-bold text-cyan-300 mt-1">{summary.observable_events_count}</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/80 border border-white/5">
                <div className="text-slate-400 uppercase text-[10px]">Alerts Recorded</div>
                <div className="text-base font-bold text-amber-300 mt-1">{summary.alerts_count}</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/80 border border-white/5">
                <div className="text-slate-400 uppercase text-[10px]">Hardware Actuations</div>
                <div className="text-base font-bold text-rose-300 mt-1">{summary.hardware_alerts_dispatched}</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/80 border border-white/5">
                <div className="text-slate-400 uppercase text-[10px]">Unknown Persons</div>
                <div className="text-base font-bold text-white mt-1">{summary.unknown_identities_detected}</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/80 border border-white/5">
                <div className="text-slate-400 uppercase text-[10px]">Uncertain Ident.</div>
                <div className="text-base font-bold text-white mt-1">{summary.uncertain_identities_detected}</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/80 border border-white/5">
                <div className="text-slate-400 uppercase text-[10px]">Reviewed Alerts</div>
                <div className="text-base font-bold text-emerald-400 mt-1">{summary.reviewed_alerts_count}</div>
              </div>
            </div>

            <p className="text-[11px] text-slate-400 italic">
              Note: AI-Proctor strictly logs objective physical sensor observations. Final academic disciplinary determination is preserved exclusively for human examination authority.
            </p>
          </div>
        )}

        {/* Authoritative Examination Roster Table */}
        <div className="space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h3 className="text-base font-bold text-white">Authoritative Biometric Roster</h3>
              <p className="text-xs text-slate-400">
                Only candidates assigned to this roster are considered for live biometric recognition.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsAddStudentOpen(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 transition-colors"
              >
                <UserPlus className="h-3.5 w-3.5" />
                <span>Assign Candidate</span>
              </button>
              <span className="text-xs text-slate-400 font-mono">
                {roster.length} Assigned
              </span>
            </div>
          </div>

          <DataTable
            data={roster}
            columns={rosterColumns}
            searchKey="name"
            searchPlaceholder="Filter candidate by name..."
            emptyMessage="No candidates assigned to this exam roster."
          />
        </div>

        {/* Modal: Add Student to Roster */}
        {isAddStudentOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
            <div className="w-full max-w-md rounded-2xl border border-white/10 bg-slate-900 p-6 space-y-4 shadow-2xl">
              <h3 className="text-lg font-bold text-white">Assign Candidate to Exam Roster</h3>
              <form onSubmit={handleAddStudent} className="space-y-4 text-xs">
                <div>
                  <label className="block text-slate-300 mb-1 font-semibold">Student ID or Roll Number</label>
                  <input
                    type="text"
                    required
                    value={newStudentId}
                    onChange={(e) => setNewStudentId(e.target.value)}
                    placeholder="e.g. s-01, s-02, CS-2026-042"
                    className="w-full rounded-xl bg-slate-950 border border-white/10 px-3 py-2 text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 mb-1 font-semibold">Seat Number / Desk</label>
                  <input
                    type="text"
                    required
                    value={newSeatNumber}
                    onChange={(e) => setNewSeatNumber(e.target.value)}
                    placeholder="e.g. B4-16"
                    className="w-full rounded-xl bg-slate-950 border border-white/10 px-3 py-2 text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 mb-1 font-semibold">Assigned Camera</label>
                  <select
                    value={newCameraId}
                    onChange={(e) => setNewCameraId(e.target.value)}
                    className="w-full rounded-xl bg-slate-950 border border-white/10 px-3 py-2 text-white font-mono"
                  >
                    <option value="cam-01">CAM-01 (Hall 304 Desk Coverage)</option>
                    <option value="cam-02">CAM-02 (Hall 304 Wide CCTV)</option>
                    <option value="cctv-hall304-01">CCTV-HALL304-01</option>
                  </select>
                </div>
                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setIsAddStudentOpen(false)}
                    className="px-4 py-2 rounded-xl text-slate-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-xl font-bold bg-cyan-500 text-slate-950 hover:bg-cyan-400"
                  >
                    Assign to Roster
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Biometric Face Enrollment Modal */}
        <FaceEnrollmentModal
          isOpen={!!enrollingStudent}
          onClose={() => setEnrollingStudent(null)}
          student={enrollingStudent}
          onSuccess={() => {
            loadData();
          }}
        />
      </div>
    </AppLayout>
  );
}
