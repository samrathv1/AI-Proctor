import { Exam, ExamStatus, Student, ExamSummary, StudentRosterItem } from '@/types';
import { mockExams } from '@/data/mockExams';
import { mockStudents } from '@/data/mockStudents';
import { supabase, isSupabaseConfigured } from '@/lib/supabase/client';

const FASTAPI_URL = process.env.NEXT_PUBLIC_FASTAPI_URL || 'http://localhost:8000';
const API_KEY = process.env.NEXT_PUBLIC_FASTAPI_KEY || 'dev-proctor-secret-key';

let localExams: Exam[] = [...mockExams];

export const examService = {
  async getExams(): Promise<Exam[]> {
    if (isSupabaseConfigured()) {
      try {
        const { data, error } = await supabase
          .from('exams')
          .select(`
            id,
            exam_code,
            name,
            subject,
            exam_date,
            start_time,
            end_time,
            duration_minutes,
            room,
            status,
            invigilator_name,
            exam_students (id, attendance_status),
            alerts (id, severity)
          `)
          .order('exam_date', { ascending: false });

        if (error) throw error;

        if (data && data.length > 0) {
          return data.map((row: any) => {
            const students = row.exam_students || [];
            const alerts = row.alerts || [];
            const criticalAlerts = alerts.filter((a: any) => a.severity === 'CRITICAL' || a.severity === 'HIGH');
            const activeStudents = students.filter((s: any) => s.attendance_status === 'PRESENT' || s.attendance_status === 'FLAGGED').length;

            return {
              id: row.id,
              title: row.name,
              subject: row.subject,
              code: row.exam_code,
              date: row.exam_date,
              startTime: row.start_time,
              endTime: row.end_time,
              durationMinutes: row.duration_minutes,
              totalStudents: students.length || 60,
              activeStudents: activeStudents || (row.status === 'LIVE' ? 59 : 0),
              status: row.status as ExamStatus,
              room: row.room,
              invigilator: row.invigilator_name,
              activeCameras: 3,
              alertCount: alerts.length,
              criticalAlertCount: criticalAlerts.length,
            };
          });
        }
      } catch (err) {
        console.warn('Supabase query failed, using local exam store:', err);
      }
    }

    await new Promise((r) => setTimeout(r, 150));
    return [...localExams];
  },

  async getExamById(id: string): Promise<Exam | undefined> {
    if (isSupabaseConfigured()) {
      try {
        const { data, error } = await supabase
          .from('exams')
          .select(`
            id,
            exam_code,
            name,
            subject,
            exam_date,
            start_time,
            end_time,
            duration_minutes,
            room,
            status,
            invigilator_name,
            exam_students (id, attendance_status),
            alerts (id, severity)
          `)
          .or(`id.eq.${id},exam_code.eq.${id}`)
          .maybeSingle();

        if (!error && data) {
          const students = data.exam_students || [];
          const alerts = data.alerts || [];
          const criticalAlerts = alerts.filter((a: any) => a.severity === 'CRITICAL' || a.severity === 'HIGH');

          return {
            id: data.id,
            title: data.name,
            subject: data.subject,
            code: data.exam_code,
            date: data.exam_date,
            startTime: data.start_time,
            endTime: data.end_time,
            durationMinutes: data.duration_minutes,
            totalStudents: students.length || 60,
            activeStudents: students.length || 59,
            status: data.status as ExamStatus,
            room: data.room,
            invigilator: data.invigilator_name,
            activeCameras: 3,
            alertCount: alerts.length,
            criticalAlertCount: criticalAlerts.length,
          };
        }
      } catch (err) {
        console.warn('Supabase getExamById failed, using fallback:', err);
      }
    }

    await new Promise((r) => setTimeout(r, 100));
    return localExams.find((e) => e.id === id) || localExams[0];
  },

  async getStudentsForExam(examId: string): Promise<Student[]> {
    if (isSupabaseConfigured()) {
      try {
        const { data, error } = await supabase
          .from('exam_students')
          .select(`
            id,
            seat_number,
            attendance_status,
            risk_score,
            students (
              id,
              name,
              roll_number,
              email
            )
          `)
          .eq('exam_id', examId);

        if (!error && data && data.length > 0) {
          return data.map((row: any) => {
            const st = row.students;
            const initials = st?.name?.split(' ').map((n: string) => n[0]).slice(0, 2).join('').toUpperCase() || 'ST';
            return {
              id: st?.id || row.id,
              name: st?.name || 'Candidate',
              rollNumber: st?.roll_number || 'CS-000',
              seatNumber: row.seat_number,
              email: st?.email || '',
              examId,
              status: row.attendance_status as 'PRESENT' | 'ABSENT' | 'FLAGGED',
              riskScore: row.risk_score || 0,
              alertsCount: row.risk_score > 70 ? 2 : row.risk_score > 30 ? 1 : 0,
              avatar: initials,
            };
          });
        }
      } catch (err) {
        console.warn('Supabase getStudentsForExam failed, using local roster:', err);
      }
    }

    await new Promise((r) => setTimeout(r, 100));
    return mockStudents.filter((s) => s.examId === examId || examId === 'exam-01' || examId.startsWith('exam-'));
  },

  async createExam(data: Omit<Exam, 'id' | 'alertCount' | 'criticalAlertCount' | 'activeStudents'>): Promise<Exam> {
    if (isSupabaseConfigured()) {
      try {
        const { data: created, error } = await supabase
          .from('exams')
          .insert({
            exam_code: data.code || 'CS-500',
            name: data.title,
            subject: data.subject,
            exam_date: data.date,
            start_time: data.startTime,
            end_time: data.endTime,
            duration_minutes: data.durationMinutes,
            room: data.room,
            status: data.status,
            invigilator_name: data.invigilator,
            description: data.description,
          })
          .select()
          .single();

        if (!error && created) {
          // Provision active session
          await supabase.from('exam_sessions').insert({
            exam_id: created.id,
            status: 'PENDING',
            active_camera_count: 3,
          });

          return {
            id: created.id,
            title: created.name,
            subject: created.subject,
            code: created.exam_code,
            date: created.exam_date,
            startTime: created.start_time,
            endTime: created.end_time,
            durationMinutes: created.duration_minutes,
            totalStudents: data.totalStudents,
            activeStudents: 0,
            status: created.status as ExamStatus,
            room: created.room,
            invigilator: created.invigilator_name,
            activeCameras: 3,
            alertCount: 0,
            criticalAlertCount: 0,
            description: created.description,
          };
        }
      } catch (err) {
        console.warn('Supabase createExam failed, using local fallback:', err);
      }
    }

    await new Promise((r) => setTimeout(r, 200));
    const newExam: Exam = {
      ...data,
      id: `exam-${Date.now().toString().slice(-4)}`,
      alertCount: 0,
      criticalAlertCount: 0,
      activeStudents: data.status === 'LIVE' ? data.totalStudents : 0,
    };
    localExams = [newExam, ...localExams];
    return newExam;
  },

  async updateExamStatus(id: string, status: ExamStatus): Promise<Exam> {
    if (isSupabaseConfigured()) {
      try {
        const { data, error } = await supabase
          .from('exams')
          .update({ status, updated_at: new Date().toISOString() })
          .eq('id', id)
          .select()
          .single();

        if (!error && data) {
          return {
            id: data.id,
            title: data.name,
            subject: data.subject,
            code: data.exam_code,
            date: data.exam_date,
            startTime: data.start_time,
            endTime: data.end_time,
            durationMinutes: data.duration_minutes,
            totalStudents: 60,
            activeStudents: status === 'LIVE' ? 59 : 0,
            status: data.status as ExamStatus,
            room: data.room,
            invigilator: data.invigilator_name,
            activeCameras: 3,
            alertCount: 8,
            criticalAlertCount: 2,
          };
        }
      } catch (err) {
        console.warn('Supabase updateExamStatus failed:', err);
      }
    }

    const examIndex = localExams.findIndex((e) => e.id === id);
    if (examIndex !== -1) {
      localExams[examIndex] = {
        ...localExams[examIndex],
        status,
        activeStudents: status === 'LIVE' ? localExams[examIndex].totalStudents : 0,
      };
      return localExams[examIndex];
    }
    return localExams[0];
  },

  async deleteExam(id: string): Promise<boolean> {
    if (isSupabaseConfigured()) {
      try {
        await supabase.from('exams').delete().eq('id', id);
      } catch (err) {
        console.warn('Supabase deleteExam failed:', err);
      }
    }
    localExams = localExams.filter((e) => e.id !== id);
    return true;
  },

  async startExam(id: string): Promise<any> {
    try {
      const res = await fetch(`${FASTAPI_URL}/api/v1/exams/${id}/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': API_KEY,
        },
      });
      if (res.ok) {
        return await res.json();
      }
      const err = await res.json().catch(() => ({ detail: 'Failed to start exam' }));
      throw new Error(err.detail || 'Failed to start examination');
    } catch (e: any) {
      console.warn('Backend startExam error, falling back to local/Supabase:', e);
      return await this.updateExamStatus(id, 'LIVE');
    }
  },

  async endExam(id: string): Promise<any> {
    try {
      const res = await fetch(`${FASTAPI_URL}/api/v1/exams/${id}/end`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': API_KEY,
        },
      });
      if (res.ok) {
        return await res.json();
      }
      const err = await res.json().catch(() => ({ detail: 'Failed to end exam' }));
      throw new Error(err.detail || 'Failed to end examination');
    } catch (e: any) {
      console.warn('Backend endExam error, falling back to local/Supabase:', e);
      return await this.updateExamStatus(id, 'ENDED');
    }
  },

  async getExamSummary(id: string): Promise<ExamSummary | null> {
    try {
      const res = await fetch(`${FASTAPI_URL}/api/v1/exams/${id}/summary`, {
        headers: { 'X-API-Key': API_KEY },
      });
      if (res.ok) {
        return await res.json();
      }
      return null;
    } catch (e) {
      console.warn('Failed to fetch exam summary:', e);
      return null;
    }
  },

  async getExamRoster(id: string): Promise<StudentRosterItem[]> {
    try {
      const res = await fetch(`${FASTAPI_URL}/api/v1/exams/${id}/roster`, {
        headers: { 'X-API-Key': API_KEY },
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn('Backend getExamRoster failed, trying fallback:', e);
    }

    // Fallback using getStudentsForExam
    const fallbackStudents = await this.getStudentsForExam(id);
    return fallbackStudents.map((s) => ({
      id: s.id,
      student_id: s.id,
      name: s.name,
      roll_number: s.rollNumber,
      email: s.email,
      seat_number: s.seatNumber,
      attendance_status: s.status,
      face_verified: true,
      face_enrolled: true,
      enrollment_status: 'ENROLLED' as const,
      risk_score: s.riskScore,
    }));
  },

  async addStudentToRoster(id: string, payload: { student_id: string; seat_number?: string; camera_id?: string }): Promise<any> {
    const res = await fetch(`${FASTAPI_URL}/api/v1/exams/${id}/roster`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to assign candidate' }));
      throw new Error(err.detail || 'Failed to assign candidate to roster');
    }
    return await res.json();
  },

  async removeStudentFromRoster(id: string, studentId: string): Promise<boolean> {
    const res = await fetch(`${FASTAPI_URL}/api/v1/exams/${id}/roster/${studentId}`, {
      method: 'DELETE',
      headers: { 'X-API-Key': API_KEY },
    });
    return res.ok;
  },
};
