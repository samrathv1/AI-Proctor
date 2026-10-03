const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

export interface TimelineEvent {
  id: string;
  timestamp: string;
  category: 'IDENTITY' | 'BEHAVIOUR' | 'ALERT' | 'REVIEW' | 'HARDWARE' | 'AUDIT' | 'SYSTEM';
  event_type: string;
  title: string;
  description: string;
  student_id?: string | null;
  student_name?: string;
  roll_number?: string;
  seat_number?: string;
  camera_id?: string;
  severity?: 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  metadata?: Record<string, any>;
}

export interface CandidateSummary {
  student_id: string;
  name: string;
  roll_number: string;
  seat_number: string;
  camera_id: string;
  events_count: number;
  peak_score: number;
  alerts_count: number;
  review_status: string;
}

export interface ExamIntegrityReport {
  exam_overview: {
    exam_id: string;
    title: string;
    subject: string;
    code: string;
    hall: string;
    date: string;
    start_time: string;
    end_time: string;
    duration_minutes: number;
    invigilator: string;
    status: string;
  };
  statistics: {
    candidates_count: number;
    cameras_count: number;
    total_observable_events: number;
    alerts_generated: number;
    alerts_reviewed: number;
    alerts_dismissed: number;
    alerts_escalated: number;
    unknown_identities: number;
    uncertain_identities: number;
    esp32_hardware_alerts: number;
    esp32_acknowledged_alerts: number;
  };
  candidates_summary: CandidateSummary[];
  timeline: TimelineEvent[];
  alerts: any[];
  hardware_activity: Array<{
    id: string;
    device_id: string;
    alert_id: string;
    action: string;
    command: string;
    dispatched_at: string;
    acknowledged_at: string;
    status: string;
  }>;
  audit_summary: Array<{
    id: string;
    timestamp: string;
    actor: string;
    action: string;
    entity_type: string;
    entity_id: string;
  }>;
  system_limitations: string;
  generated_at: string;
}

export interface CandidateIntegrityReport {
  exam_id: string;
  exam_title: string;
  student_id: string;
  name: string;
  roll_number: string;
  seat_number: string;
  camera_id: string;
  identity_status: 'IDENTIFIED' | 'UNCERTAIN' | 'UNKNOWN';
  attendance_status: string;
  observed_events: Array<{
    event_type: string;
    occurrences: number;
    total_duration_seconds: number;
    confidence: number;
    latest_timestamp: string;
  }>;
  advisory_summary: {
    peak_advisory_score: number;
    contributing_signals: string[];
    score_trend: Array<{
      timestamp: string;
      score: number;
      factor: string;
    }>;
  };
  invigilator_review: {
    status: string;
    action: string;
    reviewer: string;
    notes: string;
  };
  alerts: any[];
  evidence_frames: Array<{
    alert_id: string;
    event_type: string;
    timestamp: string;
    storage_path: string;
    confidence?: number;
    advisory_score?: number;
    review_status?: string;
  }>;
  total_alerts: number;
  generated_at: string;
}

// Fallback legacy structure for backwards compatibility
export interface ReportSummary {
  examId: string;
  examTitle: string;
  subject: string;
  date: string;
  totalStudents: number;
  totalAlerts: number;
  mobileDetectionCount: number;
  suspiciousMovementCount: number;
  unauthorizedMaterialCount: number;
  whisperNoiseCount: number;
  flaggedStudentsCount: number;
  alertDistribution: { name: string; value: number; color: string }[];
  timelineData: { minute: string; alerts: number; mobile: number; headMovement: number }[];
  hourlyTrend: { hour: string; count: number }[];
  studentIntegrityStats: { name: string; roll: string; score: number; alerts: number }[];
}

export const mockReportSummary: ReportSummary = {
  examId: 'exam-01',
  examTitle: 'DSGT Internal Examination',
  subject: 'Discrete Structures & Graph Theory (CS-402)',
  date: 'October 03, 2026',
  totalStudents: 15,
  totalAlerts: 3,
  mobileDetectionCount: 1,
  suspiciousMovementCount: 2,
  unauthorizedMaterialCount: 0,
  whisperNoiseCount: 0,
  flaggedStudentsCount: 2,
  alertDistribution: [
    { name: 'Mobile Phone', value: 1, color: '#ef4444' },
    { name: 'Head Turn / Gaze', value: 2, color: '#f59e0b' },
  ],
  timelineData: [
    { minute: '10:00', alerts: 0, mobile: 0, headMovement: 0 },
    { minute: '10:15', alerts: 1, mobile: 0, headMovement: 1 },
    { minute: '10:30', alerts: 2, mobile: 1, headMovement: 1 },
  ],
  hourlyTrend: [
    { hour: '10:00 - 10:30', count: 2 },
    { hour: '10:30 - 11:00', count: 1 },
  ],
  studentIntegrityStats: [
    { name: 'Dev Sharma', roll: 'CS-2026-042', score: 76, alerts: 1 },
    { name: 'Aarav Sharma', roll: 'CS-2026-001', score: 45, alerts: 1 },
    { name: 'Priya Nair', roll: 'CS-2026-002', score: 15, alerts: 0 },
  ],
};

export const reportsService = {
  async getExamReport(examId: string): Promise<ExamIntegrityReport> {
    const res = await fetch(`${API_BASE}/api/v1/reports/exams/${examId}`);
    if (!res.ok) {
      throw new Error(`Failed to fetch exam report: ${res.statusText}`);
    }
    return res.json();
  },

  async getCandidateReport(examId: string, studentId: string): Promise<CandidateIntegrityReport> {
    const res = await fetch(`${API_BASE}/api/v1/reports/exams/${examId}/candidates/${studentId}`);
    if (!res.ok) {
      throw new Error(`Failed to fetch candidate report: ${res.statusText}`);
    }
    return res.json();
  },

  async getExamTimeline(examId: string): Promise<TimelineEvent[]> {
    const res = await fetch(`${API_BASE}/api/v1/reports/exams/${examId}/timeline`);
    if (!res.ok) {
      throw new Error(`Failed to fetch exam timeline: ${res.statusText}`);
    }
    return res.json();
  },

  async downloadPDFReport(examId: string, studentId?: string): Promise<{ blobUrl: string; filename: string }> {
    const url = studentId
      ? `${API_BASE}/api/v1/reports/exams/${examId}/export/pdf?student_id=${studentId}`
      : `${API_BASE}/api/v1/reports/exams/${examId}/export/pdf`;
    
    const res = await fetch(url);
    if (!res.ok) {
      throw new Error(`PDF export failed with status ${res.status}`);
    }
    const blob = await res.blob();
    const blobUrl = URL.createObjectURL(blob);
    const filename = `AI-Proctor-Audit-${examId}${studentId ? `-${studentId.slice(0, 8)}` : ''}.pdf`;
    return { blobUrl, filename };
  },

  async downloadJSONReport(examId: string, studentId?: string): Promise<{ blobUrl: string; filename: string }> {
    const url = studentId
      ? `${API_BASE}/api/v1/reports/exams/${examId}/export/json?student_id=${studentId}`
      : `${API_BASE}/api/v1/reports/exams/${examId}/export/json`;
    
    const res = await fetch(url);
    if (!res.ok) {
      throw new Error(`JSON export failed with status ${res.status}`);
    }
    const data = await res.json();
    const jsonStr = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const blobUrl = URL.createObjectURL(blob);
    const filename = `AI-Proctor-Audit-${examId}${studentId ? `-${studentId.slice(0, 8)}` : ''}.json`;
    return { blobUrl, filename };
  },

  async recordEvidenceViewed(alertId: string, studentId?: string, evidencePath?: string): Promise<void> {
    try {
      await fetch(`${API_BASE}/api/v1/reports/evidence/view`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alert_id: alertId, student_id: studentId, evidence_path: evidencePath }),
      });
    } catch (e) {
      console.warn('Failed to record evidence viewed audit:', e);
    }
  },

  // Legacy method for backward compatibility
  async getReports(examId?: string): Promise<ReportSummary> {
    try {
      const eid = examId || 'exam-01';
      const report = await this.getExamReport(eid);
      return {
        examId: report.exam_overview.exam_id,
        examTitle: report.exam_overview.title,
        subject: report.exam_overview.subject,
        date: report.exam_overview.date,
        totalStudents: report.statistics.candidates_count,
        totalAlerts: report.statistics.alerts_generated,
        mobileDetectionCount: report.alerts.filter((a: any) => a.alert_type === 'MOBILE_PHONE').length,
        suspiciousMovementCount: report.alerts.filter((a: any) => a.alert_type?.includes('HEAD') || a.alert_type?.includes('GAZE')).length,
        unauthorizedMaterialCount: 0,
        whisperNoiseCount: 0,
        flaggedStudentsCount: report.candidates_summary.filter((c) => c.alerts_count > 0).length,
        alertDistribution: [
          { name: 'Mobile Phone', value: report.alerts.filter((a: any) => a.alert_type === 'MOBILE_PHONE').length || 1, color: '#ef4444' },
          { name: 'Head / Gaze Anomaly', value: report.alerts.filter((a: any) => a.alert_type?.includes('HEAD') || a.alert_type?.includes('GAZE')).length || 1, color: '#f59e0b' },
          { name: 'Desk Peeking', value: report.alerts.filter((a: any) => a.alert_type?.includes('DESK')).length || 1, color: '#38bdf8' }
        ],
        timelineData: mockReportSummary.timelineData,
        hourlyTrend: mockReportSummary.hourlyTrend,
        studentIntegrityStats: report.candidates_summary.map((c) => ({
          name: c.name,
          roll: c.roll_number,
          score: c.peak_score,
          alerts: c.alerts_count,
        })),
      };
    } catch (err) {
      console.warn('Backend exam report failed, using fallback mock:', err);
      return { ...mockReportSummary, examId: examId || 'exam-01' };
    }
  },

  // Legacy method
  async generatePDFReport(examId: string): Promise<{ blobUrl: string; filename: string }> {
    return this.downloadPDFReport(examId);
  }
};
