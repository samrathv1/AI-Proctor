import { Alert } from '@/types';

// High-tech simulated evidence snapshots
const createEvidenceSvg = (label: string, confidence: number, student: string, color: string) => {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360" style="background:#090d16">
    <defs>
      <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#111827"/>
        <stop offset="100%" stop-color="#030712"/>
      </linearGradient>
      <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
        <path d="M 30 0 L 0 0 0 30" fill="none" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
      </pattern>
    </defs>
    <rect width="640" height="360" fill="url(#g)"/>
    <rect width="640" height="360" fill="url(#grid)"/>
    
    <!-- Simulated Exam Hall Student Silhouette -->
    <circle cx="320" cy="150" r="50" fill="#1e293b" stroke="#334155" stroke-width="2"/>
    <path d="M 230 290 Q 320 220 410 290 Z" fill="#1e293b" stroke="#334155" stroke-width="2"/>
    <rect x="250" y="270" width="140" height="40" rx="4" fill="#0f172a" stroke="#475569" stroke-width="1.5"/>

    <!-- High Tech Bounding Box -->
    <rect x="240" y="90" width="160" height="190" fill="none" stroke="${color}" stroke-width="2.5" stroke-dasharray="6,4"/>
    <!-- Target Brackets -->
    <path d="M 235 110 L 235 85 L 260 85" fill="none" stroke="${color}" stroke-width="3"/>
    <path d="M 405 110 L 405 85 L 380 85" fill="none" stroke="${color}" stroke-width="3"/>
    <path d="M 235 260 L 235 285 L 260 285" fill="none" stroke="${color}" stroke-width="3"/>
    <path d="M 405 260 L 405 285 L 380 285" fill="none" stroke="${color}" stroke-width="3"/>

    <!-- Detection Tag -->
    <rect x="235" y="58" width="170" height="24" rx="4" fill="${color}"/>
    <text x="245" y="74" fill="#ffffff" font-family="monospace" font-size="11" font-weight="bold">${label} [${confidence}%]</text>

    <!-- Overlay Info -->
    <rect x="15" y="15" width="220" height="48" rx="6" fill="rgba(15,23,42,0.85)" stroke="rgba(255,255,255,0.1)"/>
    <circle cx="28" cy="30" r="4" fill="#ef4444"/>
    <text x="38" y="34" fill="#f87171" font-family="sans-serif" font-size="11" font-weight="bold">AI-PROCTOR CCTV-01 LIVE</text>
    <text x="28" y="52" fill="#94a3b8" font-family="monospace" font-size="10">EVIDENCE SNAPSHOT // ${student}</text>

    <text x="460" y="340" fill="#64748b" font-family="monospace" font-size="10">YOLOv8 + MediaPipe Vision</text>
  </svg>`;
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
};

export const mockAlerts: Alert[] = [
  {
    id: 'alt-01',
    examId: 'exam-01',
    examName: 'DSGT Internal Examination',
    studentId: 'std-15',
    studentName: 'Student 15',
    rollNumber: 'CS2026-015',
    seatNumber: 'Desk 15 (Row 3, Col 3)',
    type: 'MOBILE_PHONE',
    typeLabel: 'Mobile Phone Detected',
    severity: 'HIGH',
    confidence: 93,
    timestamp: '2026-09-30T10:45:00',
    time: '10:45 AM',
    evidenceImage: createEvidenceSvg('MOBILE_PHONE', 93, 'Student 15', '#ef4444'),
    reviewStatus: 'PENDING',
    reviewerNotes: 'Mobile device detected in left palm resting under exam desk.',
    cameraSource: 'Camera 01 (Main Hall Wide)',
    boundingBox: { x: 240, y: 90, width: 160, height: 190 },
  },
  {
    id: 'alt-02',
    examId: 'exam-01',
    examName: 'DSGT Internal Examination',
    studentId: 'std-12',
    studentName: 'Student 12',
    rollNumber: 'CS2026-012',
    seatNumber: 'Desk 12 (Row 2, Col 4)',
    type: 'MOBILE_PHONE',
    typeLabel: 'Mobile Phone Detected',
    severity: 'CRITICAL',
    confidence: 94,
    timestamp: '2026-09-30T10:42:00',
    time: '10:42 AM',
    evidenceImage: createEvidenceSvg('MOBILE_PHONE', 94, 'Student 12', '#dc2626'),
    reviewStatus: 'VERIFIED',
    reviewerNotes: 'Student held smartphone vertically for 14 continuous seconds.',
    cameraSource: 'Camera 01 (Main Hall Wide)',
    boundingBox: { x: 220, y: 100, width: 170, height: 180 },
  },
  {
    id: 'alt-03',
    examId: 'exam-01',
    examName: 'DSGT Internal Examination',
    studentId: 'std-08',
    studentName: 'Student 08',
    rollNumber: 'CS2026-008',
    seatNumber: 'Desk 08 (Row 2, Col 1)',
    type: 'SUSPICIOUS_HEAD_MOVEMENT',
    typeLabel: 'Suspicious Head Movement',
    severity: 'MEDIUM',
    confidence: 86,
    timestamp: '2026-09-30T10:50:00',
    time: '10:50 AM',
    evidenceImage: createEvidenceSvg('HEAD_TURN_48DEG', 86, 'Student 08', '#f59e0b'),
    reviewStatus: 'PENDING',
    reviewerNotes: 'Yaw angle exceeded 45 degrees towards neighbor paper for 8 seconds.',
    cameraSource: 'Camera 02 (Row 1-3 Front)',
    boundingBox: { x: 250, y: 80, width: 140, height: 160 },
  },
  {
    id: 'alt-04',
    examId: 'exam-01',
    examName: 'DSGT Internal Examination',
    studentId: 'std-12',
    studentName: 'Student 12',
    rollNumber: 'CS2026-012',
    seatNumber: 'Desk 12 (Row 2, Col 4)',
    type: 'SUSPICIOUS_HEAD_MOVEMENT',
    typeLabel: 'Frequent Desk Peeking',
    severity: 'HIGH',
    confidence: 89,
    timestamp: '2026-09-30T10:30:00',
    time: '10:30 AM',
    evidenceImage: createEvidenceSvg('PEEKING_DOWNWARD', 89, 'Student 12', '#f97316'),
    reviewStatus: 'VERIFIED',
    reviewerNotes: 'Head pitch angled downwards below desk level repeatedly.',
    cameraSource: 'Camera 01 (Main Hall Wide)',
    boundingBox: { x: 230, y: 95, width: 155, height: 185 },
  },
  {
    id: 'alt-05',
    examId: 'exam-01',
    examName: 'DSGT Internal Examination',
    studentId: 'std-34',
    studentName: 'Student 34',
    rollNumber: 'CS2026-034',
    seatNumber: 'Desk 34 (Row 4, Col 2)',
    type: 'UNAUTHORIZED_MATERIAL',
    typeLabel: 'Unauthorized Notes / Sheet',
    severity: 'HIGH',
    confidence: 91,
    timestamp: '2026-09-30T10:18:00',
    time: '10:18 AM',
    evidenceImage: createEvidenceSvg('CHIT_PAPER', 91, 'Student 34', '#e11d48'),
    reviewStatus: 'PENDING',
    reviewerNotes: 'Unfolded miniature white paper detected beside question booklet.',
    cameraSource: 'Camera 03 (Row 4-6 Rear)',
    boundingBox: { x: 260, y: 110, width: 130, height: 170 },
  },
  {
    id: 'alt-06',
    examId: 'exam-01',
    examName: 'DSGT Internal Examination',
    studentId: 'std-22',
    studentName: 'Student 22',
    rollNumber: 'CS2026-022',
    seatNumber: 'Desk 22 (Row 3, Col 6)',
    type: 'WHISPERING_NOISE',
    typeLabel: 'Verbal Communication Sound',
    severity: 'MEDIUM',
    confidence: 78,
    timestamp: '2026-09-30T10:08:00',
    time: '10:08 AM',
    evidenceImage: createEvidenceSvg('AUDIO_SPIKE_72dB', 78, 'Student 22', '#38bdf8'),
    reviewStatus: 'DISMISSED',
    reviewerNotes: 'Student asked invigilator for additional answer twine sheets.',
    cameraSource: 'Camera 02 (Row 1-3 Front)',
    boundingBox: { x: 240, y: 85, width: 150, height: 175 },
  },
  {
    id: 'alt-07',
    examId: 'exam-01',
    examName: 'DSGT Internal Examination',
    studentId: 'std-41',
    studentName: 'Student 41',
    rollNumber: 'CS2026-041',
    seatNumber: 'Desk 41 (Row 5, Col 3)',
    type: 'SUSPICIOUS_HEAD_MOVEMENT',
    typeLabel: 'Repetitive Glances Right',
    severity: 'LOW',
    confidence: 74,
    timestamp: '2026-09-30T09:55:00',
    time: '09:55 AM',
    evidenceImage: createEvidenceSvg('GAZE_OFFSET_32DEG', 74, 'Student 41', '#a855f7'),
    reviewStatus: 'DISMISSED',
    reviewerNotes: 'Invigilator verified clock on right wall was being checked.',
    cameraSource: 'Camera 03 (Row 4-6 Rear)',
    boundingBox: { x: 250, y: 90, width: 140, height: 165 },
  },
  {
    id: 'alt-08',
    examId: 'exam-01',
    examName: 'DSGT Internal Examination',
    studentId: 'std-05',
    studentName: 'Student 05',
    rollNumber: 'CS2026-005',
    seatNumber: 'Desk 05 (Row 1, Col 5)',
    type: 'ABSENCE_FROM_SEAT',
    typeLabel: 'Candidate Out of Frame',
    severity: 'HIGH',
    confidence: 96,
    timestamp: '2026-09-30T09:40:00',
    time: '09:40 AM',
    evidenceImage: createEvidenceSvg('ZERO_PERSON_FRAME', 96, 'Student 05', '#f43f5e'),
    reviewStatus: 'VERIFIED',
    reviewerNotes: 'Authorized washroom pass documented by invigilator.',
    cameraSource: 'Camera 02 (Row 1-3 Front)',
    boundingBox: { x: 200, y: 70, width: 220, height: 210 },
  },
];
