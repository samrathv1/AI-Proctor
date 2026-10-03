export type ExamStatus = 'DRAFT' | 'SCHEDULED' | 'READY' | 'LIVE' | 'ENDED' | 'COMPLETED' | 'PAUSED' | 'ARCHIVED';

export interface Exam {
  id: string;
  title: string;
  name?: string;
  subject: string;
  code: string;
  date: string;
  startTime: string;
  endTime: string;
  durationMinutes: number;
  totalStudents: number;
  activeStudents: number;
  status: ExamStatus;
  room: string;
  invigilator: string;
  activeCameras: number;
  alertCount: number;
  criticalAlertCount: number;
  description?: string;
  biometrics_cached?: boolean;
}

export interface ExamSummary {
  exam_id: string;
  exam_name: string;
  subject: string;
  date: string;
  duration_minutes: number;
  room: string;
  invigilator: string;
  status: ExamStatus;
  total_students_enrolled: number;
  camera_sources_count: number;
  observable_events_count: number;
  alerts_count: number;
  critical_alerts_count: number;
  hardware_alerts_dispatched: number;
  unknown_identities_detected: number;
  uncertain_identities_detected: number;
  reviewed_alerts_count: number;
  reporting_standard: string;
}

export interface StudentRosterItem {
  id: string;
  student_id: string;
  name: string;
  roll_number: string;
  email?: string;
  seat_number?: string;
  camera_id?: string;
  attendance_status?: string;
  face_verified?: boolean;
  face_enrolled?: boolean;
  enrollment_status?: 'ENROLLED' | 'PENDING';
  quality_score?: number;
  model_version?: string;
  risk_score?: number;
}

export type AlertSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type AlertType = 
  | 'MOBILE_PHONE' 
  | 'SUSPICIOUS_HEAD_MOVEMENT' 
  | 'MULTIPLE_PERSONS' 
  | 'ABSENCE_FROM_SEAT' 
  | 'WHISPERING_NOISE' 
  | 'UNAUTHORIZED_MATERIAL'
  | 'SIDEWAYS_GAZE'
  | 'PROLONGED_SIDEWAYS_GAZE'
  | 'REPEATED_HEAD_TURN'
  | 'DESK_PEEKING'
  | 'PERSON_INTERACTION'
  | 'POSSIBLE_TALKING'
  | 'SUSPICIOUS_MOVEMENT_PATTERN'
  | 'LOOKING_AWAY';

export type AlertReviewStatus = 'PENDING' | 'VERIFIED' | 'DISMISSED';

export interface Alert {
  id: string;
  examId: string;
  examName: string;
  studentId: string;
  studentName: string;
  rollNumber: string;
  seatNumber: string;
  type: AlertType;
  typeLabel: string;
  severity: AlertSeverity;
  confidence: number;
  timestamp: string;
  time: string;
  evidenceImage: string;
  reviewStatus: AlertReviewStatus;
  reviewerNotes?: string;
  cameraSource: string;
  boundingBox?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

export type CameraType = 'WEBCAM' | 'VIDEO' | 'IP_CAMERA';
export type CameraStatus = 'ONLINE' | 'OFFLINE' | 'CONNECTING' | 'ERROR';

export interface Camera {
  id: string;
  name: string;
  type: CameraType;
  status: CameraStatus;
  location: string;
  fps: number;
  resolution: string;
  latencyMs: number;
  bitrate: string;
  url?: string;
  lastPing: string;
  assignedExamId?: string;
}

export interface Student {
  id: string;
  name: string;
  rollNumber: string;
  seatNumber: string;
  email: string;
  examId: string;
  status: 'PRESENT' | 'ABSENT' | 'FLAGGED';
  riskScore: number;
  alertsCount: number;
  avatar: string;
}

export interface IoTDevice {
  id: string;
  name: string;
  status: 'ONLINE' | 'OFFLINE';
  ip: string;
  mac: string;
  buzzerStatus: 'READY' | 'TRIGGERED' | 'DISABLED';
  ledStatus: 'READY' | 'WARNING' | 'ALERT' | 'OFF';
  ledColor: string;
  lastAlertTime: string;
  firmwareVersion: string;
  rssi: number;
  uptime: string;
}

export interface TimelineActivity {
  id: string;
  time: string;
  title: string;
  description: string;
  severity: AlertSeverity | 'INFO';
  student?: string;
  type: string;
}

export interface DetectionSummary {
  personCount: number;
  mobileCount: number;
  bookCount: number;
  notesCount: number;
  normalBehaviorCount: number;
  suspiciousBehaviorCount: number;
}

export interface AIConfigSettings {
  phoneDetectionThreshold: number;
  headMovementThreshold: number;
  gazeDeviationThreshold: number;
  audioNoiseThreshold: number;
  alertSoundEnabled: boolean;
  esp32AlertEnabled: boolean;
  autoRecordClips: boolean;
  emailAlertDigest: boolean;
  fastApiEndpoint: string;
  esp32IpAddress: string;
}

export interface StudentProfile {
  id: string;
  student_code: string;
  name: string;
  roll_number: string;
  email: string;
  class_name?: string;
  department?: string;
  profile_photo_path?: string;
  status: string;
}

export interface StudentFaceStatus {
  student_id: string;
  enrollment_status: 'ENROLLED' | 'PENDING' | 'REJECTED' | 'NOT_ENROLLED';
  model_version?: string;
  quality_score?: number;
  has_embedding: boolean;
}

export interface StudentLoginResult {
  success: boolean;
  student: StudentProfile;
  face_enrolled: boolean;
  enrollment_status: string;
  message: string;
}

export interface FaceEnrollmentResult {
  student_id: string;
  status: 'VERIFIED' | 'FAILED' | 'REJECTED';
  message: string;
  quality_score?: number;
  model_version?: string;
}

