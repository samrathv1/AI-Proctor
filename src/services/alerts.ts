import { Alert, AlertReviewStatus, AlertSeverity, AlertType } from '@/types';
import { mockAlerts } from '@/data/mockAlerts';
import { supabase, isSupabaseConfigured } from '@/lib/supabase/client';

let localAlerts: Alert[] = [...mockAlerts];

export interface AlertFilterOptions {
  date?: string;
  type?: AlertType | 'ALL';
  severity?: AlertSeverity | 'ALL';
  student?: string;
  reviewStatus?: AlertReviewStatus | 'ALL';
}

export const alertService = {
  async getAlerts(filters?: AlertFilterOptions): Promise<Alert[]> {
    if (isSupabaseConfigured()) {
      try {
        let query = supabase
          .from('alerts')
          .select(`
            id,
            exam_id,
            alert_type,
            severity,
            confidence,
            title,
            description,
            occurred_at,
            status,
            reviewer_notes,
            students (
              id,
              name,
              roll_number
            ),
            cameras (
              id,
              name
            ),
            alert_evidence (
              storage_path
            )
          `)
          .order('occurred_at', { ascending: false });

        if (filters) {
          if (filters.severity && filters.severity !== 'ALL') {
            query = query.eq('severity', filters.severity);
          }
          if (filters.type && filters.type !== 'ALL') {
            query = query.eq('alert_type', filters.type);
          }
          if (filters.reviewStatus && filters.reviewStatus !== 'ALL') {
            const statusMap: Record<string, string> = {
              PENDING: 'OPEN',
              VERIFIED: 'CONFIRMED',
              DISMISSED: 'DISMISSED',
            };
            query = query.eq('status', statusMap[filters.reviewStatus] || filters.reviewStatus);
          }
        }

        const { data, error } = await query;

        if (!error && data && data.length > 0) {
          let results: Alert[] = data.map((row: any) => {
            const st = row.students;
            const cam = row.cameras;
            const evidence = Array.isArray(row.alert_evidence) ? row.alert_evidence[0] : row.alert_evidence;
            const timeStr = new Date(row.occurred_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

            const statusReverseMap: Record<string, AlertReviewStatus> = {
              OPEN: 'PENDING',
              REVIEWING: 'PENDING',
              CONFIRMED: 'VERIFIED',
              DISMISSED: 'DISMISSED',
            };

            return {
              id: row.id,
              examId: row.exam_id,
              examName: 'DSGT Internal Examination',
              studentId: st?.id || 'std-15',
              studentName: st?.name || 'Candidate',
              rollNumber: st?.roll_number || 'CS2026-000',
              seatNumber: 'Desk ' + (st?.roll_number ? st.roll_number.slice(-2) : '15'),
              type: row.alert_type as AlertType,
              typeLabel: row.title,
              severity: row.severity as AlertSeverity,
              confidence: row.confidence,
              timestamp: row.occurred_at,
              time: timeStr,
              evidenceImage: evidence?.storage_path || localAlerts[0].evidenceImage,
              reviewStatus: statusReverseMap[row.status] || 'PENDING',
              reviewerNotes: row.reviewer_notes || row.description,
              cameraSource: cam?.name || 'Camera 01 (Main Hall Wide)',
              boundingBox: { x: 240, y: 90, width: 160, height: 190 },
            };
          });

          if (filters?.student && filters.student.trim() !== '') {
            const q = filters.student.toLowerCase();
            results = results.filter(
              (a) =>
                a.studentName.toLowerCase().includes(q) ||
                a.rollNumber.toLowerCase().includes(q) ||
                a.seatNumber.toLowerCase().includes(q)
            );
          }

          return results;
        }
      } catch (err) {
        console.warn('Supabase getAlerts query failed, using local store:', err);
      }
    }

    // Local in-memory filter
    await new Promise((r) => setTimeout(r, 100));
    let list = [...localAlerts];

    if (!filters) return list;

    if (filters.severity && filters.severity !== 'ALL') {
      list = list.filter((a) => a.severity === filters.severity);
    }
    if (filters.type && filters.type !== 'ALL') {
      list = list.filter((a) => a.type === filters.type);
    }
    if (filters.reviewStatus && filters.reviewStatus !== 'ALL') {
      list = list.filter((a) => a.reviewStatus === filters.reviewStatus);
    }
    if (filters.student && filters.student.trim() !== '') {
      const q = filters.student.toLowerCase();
      list = list.filter(
        (a) =>
          a.studentName.toLowerCase().includes(q) ||
          a.rollNumber.toLowerCase().includes(q) ||
          a.seatNumber.toLowerCase().includes(q)
      );
    }

    return list;
  },

  async updateAlertStatus(
    alertId: string,
    status: AlertReviewStatus,
    notes?: string
  ): Promise<Alert> {
    const dbStatus = status === 'VERIFIED' ? 'CONFIRMED' : status === 'DISMISSED' ? 'DISMISSED' : 'OPEN';

    if (isSupabaseConfigured()) {
      try {
        await supabase
          .from('alerts')
          .update({
            status: dbStatus,
            reviewer_notes: notes,
            reviewed_at: new Date().toISOString(),
          })
          .eq('id', alertId);

        // Also record in audit log
        await supabase.from('audit_logs').insert({
          action: `ALERT_${dbStatus}`,
          entity_type: 'ALERT',
          entity_id: alertId,
          metadata: { new_status: status, notes },
        });
      } catch (err) {
        console.warn('Supabase updateAlertStatus failed:', err);
      }
    }

    const index = localAlerts.findIndex((a) => a.id === alertId);
    if (index !== -1) {
      localAlerts[index] = {
        ...localAlerts[index],
        reviewStatus: status,
        reviewerNotes: notes !== undefined ? notes : localAlerts[index].reviewerNotes,
      };
      return localAlerts[index];
    }
    return localAlerts[0];
  },

  // Real-time subscription hook for live alert feeds
  subscribeToAlerts(callback: (alert: Alert) => void) {
    if (!isSupabaseConfigured()) return () => {};

    const channel = supabase
      .channel('realtime:alerts')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'alerts' },
        (payload: any) => {
          const row = payload.new;
          const formatted: Alert = {
            id: row.id,
            examId: row.exam_id,
            examName: 'DSGT Internal Examination',
            studentId: row.student_id || 'std-15',
            studentName: row.title.includes('Student') ? row.title : 'Candidate',
            rollNumber: 'CS2026-000',
            seatNumber: 'Desk 12',
            type: row.alert_type as AlertType,
            typeLabel: row.title,
            severity: row.severity as AlertSeverity,
            confidence: row.confidence,
            timestamp: row.occurred_at,
            time: new Date(row.occurred_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            evidenceImage: localAlerts[0].evidenceImage,
            reviewStatus: 'PENDING',
            cameraSource: 'Camera 01 (Main Hall Wide)',
            reviewerNotes: row.description,
          };
          callback(formatted);
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  },

  async createSimulatedAlert(partial: Partial<Alert>): Promise<Alert> {
    const newAlert: Alert = {
      id: `alt-${Date.now().toString().slice(-4)}`,
      examId: '00000000-0000-0000-0000-000000000001',
      examName: 'DSGT Internal Examination',
      studentId: partial.studentId || 'std-12',
      studentName: partial.studentName || 'Student 12',
      rollNumber: 'CS2026-012',
      seatNumber: 'Desk 12',
      type: partial.type || 'MOBILE_PHONE',
      typeLabel: partial.typeLabel || 'Mobile Phone Detected',
      severity: partial.severity || 'CRITICAL',
      confidence: partial.confidence || 94,
      timestamp: new Date().toISOString(),
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      evidenceImage: partial.evidenceImage || localAlerts[0].evidenceImage,
      reviewStatus: 'PENDING',
      cameraSource: 'Camera 01 (Main Hall Wide)',
      reviewerNotes: 'Real-time alert triggered from live camera feed.',
    };

    if (isSupabaseConfigured()) {
      try {
        await supabase.from('alerts').insert({
          exam_id: '00000000-0000-0000-0000-000000000001',
          alert_type: newAlert.type,
          severity: newAlert.severity,
          confidence: newAlert.confidence,
          title: newAlert.typeLabel,
          description: newAlert.reviewerNotes,
          status: 'OPEN',
        });
      } catch (err) {
        console.warn('Supabase createAlert failed:', err);
      }
    }

    localAlerts = [newAlert, ...localAlerts];
    return newAlert;
  },
};
