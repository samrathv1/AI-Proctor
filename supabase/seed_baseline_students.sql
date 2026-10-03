-- ========================================================
-- AI-PROCTOR BASELINE STUDENTS, EXAM & HARDWARE SEED DATA
-- Required by Phase 5 Specification
-- ========================================================

-- 1. Baseline Exam (exam-01)
INSERT INTO public.exams (
    id, exam_code, name, subject, exam_date, start_time, end_time, duration_minutes, room, status, invigilator_name
) VALUES (
    'exam-01',
    'CS-402',
    'DSGT Internal Examination',
    'Discrete Structures & Graph Theory',
    '2026-09-30',
    '10:00 AM',
    '12:00 PM',
    120,
    'Hall 304 - Engineering Wing B',
    'LIVE',
    'Dr. Robert Vance, Ph.D.'
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    status = EXCLUDED.status,
    room = EXCLUDED.room;

-- 2. Baseline Exam Session
INSERT INTO public.exam_sessions (
    id, exam_id, started_at, status, active_camera_count
) VALUES (
    '00000000-0000-0000-0000-000000000011',
    'exam-01',
    NOW() - INTERVAL '1 hour 24 minutes',
    'RUNNING',
    3
) ON CONFLICT (id) DO UPDATE SET
    status = EXCLUDED.status;

-- 3. Baseline Students: Dev Sharma (s-01), Ananya Roy (s-02), Rahul Verma (s-03)
INSERT INTO public.students (id, student_code, name, roll_number, email, class_name, department, profile_photo_path, status) VALUES
(
    's-01', 
    'STU-2026-042', 
    'Dev Sharma', 
    'CS-2026-042', 
    'dev.sharma@institution.edu', 
    'CS-2026', 
    'Computer Science & Engineering', 
    'student-photos/s-01.jpg', 
    'ACTIVE'
),
(
    's-02', 
    'STU-2026-018', 
    'Ananya Roy', 
    'CS-2026-018', 
    'ananya.roy@institution.edu', 
    'CS-2026', 
    'Computer Science & Engineering', 
    'student-photos/s-02.jpg', 
    'ACTIVE'
),
(
    's-03', 
    'STU-2026-031', 
    'Rahul Verma', 
    'CS-2026-031', 
    'rahul.verma@institution.edu', 
    'CS-2026', 
    'Computer Science & Engineering', 
    'student-photos/s-03.jpg', 
    'ACTIVE'
)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    roll_number = EXCLUDED.roll_number,
    email = EXCLUDED.email;

-- 4. Baseline Exam Roster (exam-01)
INSERT INTO public.exam_students (exam_id, student_id, seat_number, attendance_status, face_verified, risk_score) VALUES
('exam-01', 's-01', 'B4-12', 'FLAGGED', TRUE, 85),
('exam-01', 's-02', 'B4-14', 'PRESENT', TRUE, 15),
('exam-01', 's-03', 'B4-15', 'FLAGGED', TRUE, 68)
ON CONFLICT (exam_id, student_id) DO UPDATE SET
    attendance_status = EXCLUDED.attendance_status,
    risk_score = EXCLUDED.risk_score;

-- 5. Baseline ESP32 Device (ESP32-HALL304-01)
INSERT INTO public.iot_devices (
    id, device_uid, device_name, location, ip_address, firmware_version, status, buzzer_status, led_status, led_color
) VALUES (
    '00000000-0000-0000-0000-000000000302',
    'ESP32-HALL304-01',
    'ESP32 Hall Alert Node [Unit-01]',
    'Hall 304 - Engineering Wing B',
    '10.173.104.24',
    'v2.4.1-ai-proctor',
    'ONLINE',
    'READY',
    'READY',
    '#10b981'
) ON CONFLICT (device_uid) DO UPDATE SET
    ip_address = EXCLUDED.ip_address,
    status = EXCLUDED.status,
    last_seen_at = NOW();
