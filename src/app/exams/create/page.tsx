'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { AppLayout } from '@/components/layout/AppLayout';
import { examService } from '@/services/exam';
import { 
  GraduationCap, 
  ArrowLeft, 
  Calendar, 
  Clock, 
  Users, 
  UploadCloud, 
  FileText, 
  Check, 
  Sparkles,
  Info
} from 'lucide-react';

export default function CreateExamPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    title: '',
    subject: '',
    code: '',
    date: '2026-10-05',
    startTime: '10:00 AM',
    endTime: '12:00 PM',
    durationMinutes: 120,
    totalStudents: 60,
    room: 'Hall 304 - Engineering Wing B',
    invigilator: 'Dr. Robert Vance, Ph.D.',
    description: '',
  });

  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successToast, setSuccessToast] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title || !formData.subject) {
      alert('Please fill out the Exam Name and Subject.');
      return;
    }

    setIsSubmitting(true);
    try {
      const created = await examService.createExam({
        title: formData.title,
        subject: formData.subject,
        code: formData.code || 'CS-500',
        date: formData.date,
        startTime: formData.startTime,
        endTime: formData.endTime,
        durationMinutes: Number(formData.durationMinutes),
        totalStudents: Number(formData.totalStudents),
        room: formData.room,
        invigilator: formData.invigilator,
        status: 'SCHEDULED',
        activeCameras: 3,
        description: formData.description,
      });

      setSuccessToast(true);
      setTimeout(() => {
        router.push(`/exams/${created.id}`);
      }, 1000);
    } catch (err) {
      console.error(err);
      setIsSubmitting(false);
    }
  };

  return (
    <AppLayout
      breadcrumbs={[
        { label: 'Dashboard', href: '/dashboard' },
        { label: 'Exams', href: '/exams' },
        { label: 'Create' },
      ]}
    >
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <Link
              href="/exams"
              className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-cyan-400 transition-colors mb-2"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>Back to Sessions</span>
            </Link>
            <h1 className="text-2xl font-extrabold text-white tracking-tight sm:text-3xl">
              Create Examination Session
            </h1>
            <p className="mt-1 text-xs sm:text-sm text-slate-400">
              Provision an AI surveillance session, register candidate roster, and bind exam cameras.
            </p>
          </div>
        </div>

        {/* Form Card */}
        <form
          onSubmit={handleSubmit}
          className="rounded-2xl border border-white/10 bg-slate-900/70 p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-6"
        >
          {/* Section 1: Basic Information */}
          <div className="space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-2">
              <GraduationCap className="h-4 w-4" />
              <span>Session Details</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="sm:col-span-2">
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Exam Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. DSGT Internal Examination"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="w-full rounded-xl bg-slate-950/80 border border-white/10 px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/40"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Subject *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Discrete Structures & Graph Theory"
                  value={formData.subject}
                  onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                  className="w-full rounded-xl bg-slate-950/80 border border-white/10 px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/40"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Course Code
                </label>
                <input
                  type="text"
                  placeholder="e.g. CS-402"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                  className="w-full rounded-xl bg-slate-950/80 border border-white/10 px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/40"
                />
              </div>
            </div>
          </div>

          {/* Section 2: Date, Time & Capacity */}
          <div className="pt-4 border-t border-white/5 space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              <span>Schedule & Capacity</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Date
                </label>
                <input
                  type="date"
                  value={formData.date}
                  onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                  className="w-full rounded-xl bg-slate-950/80 border border-white/10 px-4 py-2.5 text-xs text-white focus:outline-none focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/40"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Start Time
                </label>
                <input
                  type="text"
                  value={formData.startTime}
                  onChange={(e) => setFormData({ ...formData, startTime: e.target.value })}
                  placeholder="10:00 AM"
                  className="w-full rounded-xl bg-slate-950/80 border border-white/10 px-4 py-2.5 text-xs text-white focus:outline-none focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/40"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  End Time
                </label>
                <input
                  type="text"
                  value={formData.endTime}
                  onChange={(e) => setFormData({ ...formData, endTime: e.target.value })}
                  placeholder="12:00 PM"
                  className="w-full rounded-xl bg-slate-950/80 border border-white/10 px-4 py-2.5 text-xs text-white focus:outline-none focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/40"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Number of Students
                </label>
                <input
                  type="number"
                  min="1"
                  max="500"
                  value={formData.totalStudents}
                  onChange={(e) => setFormData({ ...formData, totalStudents: Number(e.target.value) })}
                  className="w-full rounded-xl bg-slate-950/80 border border-white/10 px-4 py-2.5 text-xs text-white focus:outline-none focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/40"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Exam Hall / Room
                </label>
                <input
                  type="text"
                  value={formData.room}
                  onChange={(e) => setFormData({ ...formData, room: e.target.value })}
                  className="w-full rounded-xl bg-slate-950/80 border border-white/10 px-4 py-2.5 text-xs text-white focus:outline-none focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/40"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Lead Invigilator
                </label>
                <input
                  type="text"
                  value={formData.invigilator}
                  onChange={(e) => setFormData({ ...formData, invigilator: e.target.value })}
                  className="w-full rounded-xl bg-slate-950/80 border border-white/10 px-4 py-2.5 text-xs text-white focus:outline-none focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/40"
                />
              </div>
            </div>
          </div>

          {/* Section 3: Upload Student CSV */}
          <div className="pt-4 border-t border-white/5 space-y-3">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-2">
                <UploadCloud className="h-4 w-4" />
                <span>Upload Student CSV</span>
              </label>
              <span className="text-[11px] text-slate-400">
                Format: RollNumber, FullName, DeskNumber, Email
              </span>
            </div>

            <div className="relative rounded-2xl border-2 border-dashed border-white/10 bg-slate-950/40 p-6 text-center hover:border-cyan-500/40 transition-colors cursor-pointer group">
              <input
                type="file"
                accept=".csv"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    setUploadedFile(e.target.files[0]);
                  }
                }}
                className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
              />
              <div className="flex flex-col items-center justify-center">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 group-hover:scale-110 transition-transform">
                  <FileText className="h-6 w-6" />
                </div>
                {uploadedFile ? (
                  <div className="mt-3">
                    <p className="text-xs font-bold text-emerald-400 flex items-center gap-1.5 justify-center">
                      <Check className="h-4 w-4" />
                      <span>{uploadedFile.name} ({(uploadedFile.size / 1024).toFixed(1)} KB)</span>
                    </p>
                    <span className="text-[11px] text-slate-400">Click to change file</span>
                  </div>
                ) : (
                  <>
                    <p className="mt-3 text-xs font-semibold text-slate-200">
                      Drag & drop your candidate roster CSV, or <span className="text-cyan-400">browse file</span>
                    </p>
                    <p className="text-[11px] text-slate-400 mt-1">
                      Supports .csv format up to 10MB
                    </p>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Submit Action */}
          <div className="pt-4 border-t border-white/5 flex items-center justify-end gap-3">
            <Link
              href="/exams"
              className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-2.5 text-xs font-semibold text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
            >
              Cancel
            </Link>

            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 px-6 py-2.5 text-xs font-bold text-slate-950 transition-all shadow-lg shadow-cyan-950/60 disabled:opacity-50 hover:scale-[1.02]"
            >
              {isSubmitting ? (
                <span>Provisioning Session...</span>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  <span>Create Exam</span>
                </>
              )}
            </button>
          </div>
        </form>

        {successToast && (
          <div className="fixed bottom-6 right-6 z-50 rounded-2xl border border-emerald-500/40 bg-slate-900/95 p-4 shadow-2xl backdrop-blur-xl flex items-center gap-3 animate-in fade-in slide-in-from-bottom-2">
            <div className="h-8 w-8 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
              <Check className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-bold text-white">Examination Session Created</p>
              <p className="text-[11px] text-slate-400">Redirecting to exam surveillance profile...</p>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
