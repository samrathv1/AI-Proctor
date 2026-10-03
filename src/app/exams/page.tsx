'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { AppLayout } from '@/components/layout/AppLayout';
import { DataTable, Column } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { mockExams } from '@/data/mockExams';
import { examService } from '@/services/exam';
import { Exam, ExamStatus } from '@/types';
import { 
  GraduationCap, 
  Plus, 
  Eye, 
  Video, 
  FileText, 
  Calendar, 
  Clock, 
  Users, 
  Search, 
  SlidersHorizontal 
} from 'lucide-react';

export default function ExamsListPage() {
  const [exams, setExams] = useState<Exam[]>(mockExams);
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');

  useEffect(() => {
    async function load() {
      const data = await examService.getExams();
      if (data && data.length > 0) {
        setExams(data);
      }
    }
    load();
  }, []);

  const filteredExams = React.useMemo(() => {
    if (selectedStatus === 'ALL') return exams;
    return exams.filter((e) => e.status === selectedStatus);
  }, [exams, selectedStatus]);

  const columns: Column<Exam>[] = [
    {
      key: 'title',
      header: 'Exam Name',
      render: (exam) => (
        <div>
          <div className="font-bold text-white text-sm hover:text-cyan-400 transition-colors">
            <Link href={`/exams/${exam.id}`}>{exam.title}</Link>
          </div>
          <div className="text-[11px] text-slate-400 font-mono flex items-center gap-1.5 mt-0.5">
            <span className="text-cyan-400 font-semibold">{exam.code}</span>
            <span>•</span>
            <span>{exam.room}</span>
          </div>
        </div>
      ),
    },
    {
      key: 'subject',
      header: 'Subject',
      render: (exam) => (
        <span className="text-slate-300 font-medium">{exam.subject}</span>
      ),
    },
    {
      key: 'date',
      header: 'Date & Time',
      render: (exam) => (
        <div className="text-xs">
          <div className="text-white font-medium flex items-center gap-1">
            <Calendar className="h-3 w-3 text-slate-400" />
            <span>{exam.date}</span>
          </div>
          <div className="text-slate-400 font-mono text-[11px] mt-0.5 flex items-center gap-1">
            <Clock className="h-3 w-3 text-slate-500" />
            <span>{exam.startTime} - {exam.endTime}</span>
          </div>
        </div>
      ),
    },
    {
      key: 'totalStudents',
      header: 'Students',
      render: (exam) => (
        <div className="text-xs">
          <span className="font-bold text-white font-mono">{exam.totalStudents}</span>
          <span className="text-slate-400 text-[11px] ml-1">Enrolled</span>
          {exam.status === 'LIVE' && (
            <div className="text-[10px] text-emerald-400 font-medium">
              {exam.activeStudents} Present
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (exam) => <StatusBadge status={exam.status} size="sm" />,
    },
    {
      key: 'actions',
      header: 'Actions',
      className: 'text-right',
      render: (exam) => (
        <div className="flex items-center justify-end gap-1.5">
          <Link
            href={`/exams/${exam.id}`}
            className="rounded-lg p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title="View Details"
          >
            <Eye className="h-4 w-4" />
          </Link>

          {exam.status === 'LIVE' ? (
            <Link
              href="/monitoring"
              className="inline-flex items-center gap-1 rounded-lg bg-cyan-500/10 px-2.5 py-1 text-[11px] font-semibold text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/20 transition-all"
            >
              <Video className="h-3.5 w-3.5" />
              <span>Monitor</span>
            </Link>
          ) : (
            <Link
              href="/reports"
              className="rounded-lg p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
              title="View Report"
            >
              <FileText className="h-4 w-4" />
            </Link>
          )}
        </div>
      ),
    },
  ];

  return (
    <AppLayout breadcrumbs={[{ label: 'Dashboard', href: '/dashboard' }, { label: 'Exams' }]}>
      <div className="space-y-6">
        {/* Top Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-extrabold text-white tracking-tight sm:text-3xl">
              Examination Sessions
            </h1>
            <p className="mt-1 text-xs sm:text-sm text-slate-400">
              Manage scheduled, active, and completed proctored examination halls.
            </p>
          </div>

          <Link
            href="/exams/create"
            className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 px-4 py-2.5 text-xs sm:text-sm font-bold text-slate-950 shadow-lg shadow-cyan-950/40 transition-all hover:scale-[1.02]"
          >
            <Plus className="h-4 w-4" />
            <span>Create New Exam</span>
          </Link>
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap items-center gap-2">
          {['ALL', 'LIVE', 'SCHEDULED', 'COMPLETED'].map((status) => (
            <button
              key={status}
              onClick={() => setSelectedStatus(status)}
              className={`rounded-xl px-3.5 py-1.5 text-xs font-semibold transition-all ${
                selectedStatus === status
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                  : 'bg-slate-900/60 text-slate-400 border border-white/5 hover:text-white hover:bg-slate-800'
              }`}
            >
              {status === 'ALL' ? 'All Sessions' : status}
            </button>
          ))}
        </div>

        {/* Data Table */}
        <DataTable
          data={filteredExams}
          columns={columns}
          searchKey="title"
          searchPlaceholder="Search examination by name..."
          emptyMessage="No examinations found matching your criteria."
        />
      </div>
    </AppLayout>
  );
}
