-- AI-Proctor Supabase Initial Seed Data
-- Version: 1.0.0

-- 1. Initial Exam Session
INSERT INTO public.exams (
    id, exam_code, name, subject, exam_date, start_time, end_time, duration_minutes, room, status, invigilator_name
) VALUES (
    '00000000-0000-0000-0000-000000000001',
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
) ON CONFLICT (id) DO NOTHING;

-- 2. Initial Exam Session Execution
INSERT INTO public.exam_sessions (
    id, exam_id, started_at, status, active_camera_count
) VALUES (
    '00000000-0000-0000-0000-000000000010',
    '00000000-0000-0000-0000-000000000001',
    NOW() - INTERVAL '1 hour 24 minutes',
    'RUNNING',
    3
) ON CONFLICT (id) DO NOTHING;

-- 3. Initial Candidates
INSERT INTO public.students (id, student_code, name, roll_number, email, class_name, department, status) VALUES
('00000000-0000-0000-0000-000000000112', 'STD-012', 'Student 12 (Aarav Sharma)', 'CS2026-012', 'aarav.sharma@uni.edu', 'CS-2026', 'Computer Science', 'ACTIVE'),
('00000000-0000-0000-0000-000000000115', 'STD-015', 'Student 15 (Priya Nair)', 'CS2026-015', 'priya.nair@uni.edu', 'CS-2026', 'Computer Science', 'ACTIVE'),
('00000000-0000-0000-0000-000000000134', 'STD-034', 'Student 34 (Rohan Verma)', 'CS2026-034', 'rohan.verma@uni.edu', 'CS-2026', 'Computer Science', 'ACTIVE'),
('00000000-0000-0000-0000-000000000108', 'STD-008', 'Student 08 (Ananya Sen)', 'CS2026-008', 'ananya.sen@uni.edu', 'CS-2026', 'Computer Science', 'ACTIVE'),
('00000000-0000-0000-0000-000000000122', 'STD-022', 'Student 22 (Devansh Patel)', 'CS2026-022', 'devansh.patel@uni.edu', 'CS-2026', 'Computer Science', 'ACTIVE'),
('00000000-0000-0000-0000-000000000105', 'STD-005', 'Student 05 (Meera Iyer)', 'CS2026-005', 'meera.iyer@uni.edu', 'CS-2026', 'Computer Science', 'ACTIVE')
ON CONFLICT (id) DO NOTHING;

-- 4. Candidate Exam Enrollment
INSERT INTO public.exam_students (exam_id, student_id, seat_number, attendance_status, face_verified, risk_score) VALUES
('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000112', 'Desk 12', 'FLAGGED', TRUE, 92),
('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000115', 'Desk 15', 'FLAGGED', TRUE, 88),
('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000134', 'Desk 34', 'FLAGGED', TRUE, 78),
('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000108', 'Desk 08', 'PRESENT', TRUE, 45),
('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000122', 'Desk 22', 'PRESENT', TRUE, 32),
('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000105', 'Desk 05', 'PRESENT', TRUE, 28)
ON CONFLICT (exam_id, student_id) DO NOTHING;

-- 5. Physical Cameras
INSERT INTO public.cameras (id, name, camera_type, location, status) VALUES
('00000000-0000-0000-0000-000000000201', 'Camera 01 - Main Hall Wide View', 'IP_CAMERA', 'Hall 304 - Front Ceiling Center', 'ONLINE'),
('00000000-0000-0000-0000-000000000202', 'Camera 02 - Rows 1-3 Front Close-Up', 'WEBCAM', 'Invigilator Podium USB 3.0', 'ONLINE'),
('00000000-0000-0000-0000-000000000203', 'Camera 03 - Rows 4-6 Rear Angle', 'IP_CAMERA', 'Hall 304 - Rear Wall Corner Left', 'ONLINE')
ON CONFLICT (id) DO NOTHING;

-- 6. ESP32 Alert Actuator Node
INSERT INTO public.iot_devices (
    id, device_uid, device_name, location, ip_address, firmware_version, status, buzzer_status, led_status, led_color
) VALUES (
    '00000000-0000-0000-0000-000000000301',
    'ESP32-HALL304-NODE1',
    'ESP32 Hall Alert Node [Unit-A]',
    'Hall 304 - Engineering Wing B',
    '192.168.1.10',
    'v2.4.1-ai-proctor',
    'ONLINE',
    'READY',
    'READY',
    '#10b981'
) ON CONFLICT (id) DO NOTHING;

-- 7. Initial Suspicious Alerts
INSERT INTO public.alerts (
    id, exam_session_id, exam_id, student_id, camera_id, alert_type, severity, confidence, suspicion_score, title, description, occurred_at, status
) VALUES
(
    '00000000-0000-0000-0000-000000000401',
    '00000000-0000-0000-0000-000000000010',
    '00000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000115',
    '00000000-0000-0000-0000-000000000201',
    'MOBILE_PHONE',
    'HIGH',
    93,
    90,
    'Mobile Phone Detected',
    'Mobile device detected in left palm resting under exam desk.',
    NOW() - INTERVAL '15 minutes',
    'OPEN'
),
(
    '00000000-0000-0000-0000-000000000402',
    '00000000-0000-0000-0000-000000000010',
    '00000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000112',
    '00000000-0000-0000-0000-000000000201',
    'MOBILE_PHONE',
    'CRITICAL',
    94,
    95,
    'Mobile Phone Detected',
    'Student held smartphone vertically for 14 continuous seconds.',
    NOW() - INTERVAL '18 minutes',
    'CONFIRMED'
),
(
    '00000000-0000-0000-0000-000000000403',
    '00000000-0000-0000-0000-000000000010',
    '00000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000108',
    '00000000-0000-0000-0000-000000000202',
    'SUSPICIOUS_HEAD_MOVEMENT',
    'MEDIUM',
    86,
    80,
    'Suspicious Head Movement',
    'Yaw angle exceeded 45 degrees towards neighbor paper for 8 seconds.',
    NOW() - INTERVAL '10 minutes',
    'OPEN'
)
ON CONFLICT (id) DO NOTHING;
