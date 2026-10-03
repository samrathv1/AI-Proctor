-- AI-Proctor Supabase Production Database Schema
-- Version: 1.0.0
-- Generated: 2026-10-01

-- ========================================================
-- 0. EXTENSIONS & PREREQUISITES
-- ========================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ========================================================
-- 1. ENUM TYPES
-- ========================================================
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('ADMIN', 'INVIGILATOR');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE exam_status AS ENUM ('DRAFT', 'SCHEDULED', 'LIVE', 'COMPLETED', 'CANCELLED');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE session_status AS ENUM ('PENDING', 'RUNNING', 'PAUSED', 'COMPLETED', 'ABORTED');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE camera_type AS ENUM ('WEBCAM', 'RECORDED_VIDEO', 'IP_CAMERA');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE camera_status AS ENUM ('ONLINE', 'OFFLINE', 'CONNECTING', 'ERROR');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE alert_severity AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE alert_status AS ENUM ('OPEN', 'REVIEWING', 'CONFIRMED', 'DISMISSED');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE iot_status AS ENUM ('ONLINE', 'OFFLINE', 'CONNECTING', 'ERROR');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE iot_event_type AS ENUM (
        'HEARTBEAT', 
        'BUZZER_TRIGGER', 
        'LED_WARNING', 
        'LED_ALARM', 
        'DEVICE_CONNECTED', 
        'DEVICE_DISCONNECTED'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- ========================================================
-- 2. AUTH & PROFILES DOMAIN
-- ========================================================
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'INVIGILATOR',
    department VARCHAR(255),
    avatar_initials VARCHAR(4) DEFAULT 'IP',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ========================================================
-- 3. STUDENT IDENTITY & FACE BIOMETRIC ENROLLMENT DOMAIN
-- ========================================================
CREATE TABLE IF NOT EXISTS public.students (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_code VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    roll_number VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    class_name VARCHAR(100) DEFAULT 'CS-2026',
    department VARCHAR(255) DEFAULT 'Computer Science & Engineering',
    profile_photo_path TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Sensitive Biometric Table: Strictly Server-Side / AI engine access
CREATE TABLE IF NOT EXISTS public.student_face_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES public.students(id) ON DELETE CASCADE,
    enrollment_status VARCHAR(50) NOT NULL DEFAULT 'ENROLLED', -- 'ENROLLED', 'PENDING', 'REJECTED'
    model_version VARCHAR(100) NOT NULL DEFAULT 'insightface-v2.1-arcface',
    quality_score NUMERIC(5,2) DEFAULT 95.00,
    face_embedding BYTEA, -- Protected binary vector representation; NEVER exposed to public browser
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_student_face_profile UNIQUE (student_id)
);

-- ========================================================
-- 4. EXAM LIFECYCLE & SESSIONS DOMAIN
-- ========================================================
CREATE TABLE IF NOT EXISTS public.exams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    exam_code VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    exam_date DATE NOT NULL,
    start_time VARCHAR(20) NOT NULL,
    end_time VARCHAR(20) NOT NULL,
    duration_minutes INT NOT NULL DEFAULT 120,
    room VARCHAR(100) DEFAULT 'Hall 304 - Engineering Wing B',
    status exam_status NOT NULL DEFAULT 'SCHEDULED',
    created_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.exam_students (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    exam_id UUID NOT NULL REFERENCES public.exams(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES public.students(id) ON DELETE CASCADE,
    seat_number VARCHAR(100) NOT NULL,
    attendance_status VARCHAR(50) NOT NULL DEFAULT 'PRESENT', -- 'PRESENT', 'ABSENT', 'FLAGGED'
    face_verified BOOLEAN NOT NULL DEFAULT FALSE,
    risk_score INT NOT NULL DEFAULT 0 CHECK (risk_score >= 0 AND risk_score <= 100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_exam_student_enrollment UNIQUE (exam_id, student_id)
);

CREATE TABLE IF NOT EXISTS public.exam_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    exam_id UUID NOT NULL REFERENCES public.exams(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    status session_status NOT NULL DEFAULT 'PENDING',
    active_camera_count INT NOT NULL DEFAULT 3,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ========================================================
-- 5. CAMERA & STREAM SOURCE DOMAIN
-- ========================================================
CREATE TABLE IF NOT EXISTS public.cameras (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    camera_type camera_type NOT NULL DEFAULT 'IP_CAMERA',
    location VARCHAR(255) NOT NULL,
    status camera_status NOT NULL DEFAULT 'ONLINE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.camera_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    camera_id UUID NOT NULL REFERENCES public.cameras(id) ON DELETE CASCADE,
    source_type VARCHAR(100) NOT NULL, -- 'WEBRTC', 'FILE_MP4', 'RTSP_STREAM'
    source_reference TEXT NOT NULL,     -- RTSP URL, file path, device URI (passwords abstracted)
    resolution VARCHAR(50) DEFAULT '1080p (1920x1080)',
    fps INT DEFAULT 30,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_camera_source UNIQUE (camera_id)
);

-- ========================================================
-- 6. AI VISION & OBSERVABLE BEHAVIOUR DOMAIN
-- ========================================================
CREATE TABLE IF NOT EXISTS public.detections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    exam_session_id UUID NOT NULL REFERENCES public.exam_sessions(id) ON DELETE CASCADE,
    camera_id UUID REFERENCES public.cameras(id) ON DELETE SET NULL,
    student_id UUID REFERENCES public.students(id) ON DELETE SET NULL,
    detection_type VARCHAR(100) NOT NULL, -- 'PERSON', 'MOBILE_PHONE', 'UNKNOWN_PERSON', 'UNWANTED_OBJECT', 'FACE'
    confidence INT NOT NULL CHECK (confidence >= 0 AND confidence <= 100),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    bounding_box JSONB, -- { "x": 0.45, "y": 0.46, "width": 0.16, "height": 0.36 }
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.student_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    exam_session_id UUID NOT NULL REFERENCES public.exam_sessions(id) ON DELETE CASCADE,
    camera_id UUID REFERENCES public.cameras(id) ON DELETE SET NULL,
    student_id UUID REFERENCES public.students(id) ON DELETE SET NULL,
    tracking_reference VARCHAR(100) NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    confidence INT NOT NULL DEFAULT 95,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.behaviour_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    exam_session_id UUID NOT NULL REFERENCES public.exam_sessions(id) ON DELETE CASCADE,
    student_id UUID REFERENCES public.students(id) ON DELETE SET NULL,
    camera_id UUID REFERENCES public.cameras(id) ON DELETE SET NULL,
    behaviour_type VARCHAR(100) NOT NULL, -- 'HEAD_TURN', 'LOOKING_AWAY', 'MULTIPLE_PERSONS', 'MOBILE_DETECTED'
    confidence INT NOT NULL CHECK (confidence >= 0 AND confidence <= 100),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    duration_ms INT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ========================================================
-- 7. ALERTS & EVIDENCE DOMAIN
-- ========================================================
CREATE TABLE IF NOT EXISTS public.alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    exam_session_id UUID REFERENCES public.exam_sessions(id) ON DELETE CASCADE,
    exam_id UUID NOT NULL REFERENCES public.exams(id) ON DELETE CASCADE,
    student_id UUID REFERENCES public.students(id) ON DELETE SET NULL,
    camera_id UUID REFERENCES public.cameras(id) ON DELETE SET NULL,
    alert_type VARCHAR(100) NOT NULL, -- 'MOBILE_PHONE', 'SUSPICIOUS_HEAD_MOVEMENT', etc.
    severity alert_severity NOT NULL DEFAULT 'HIGH',
    confidence INT NOT NULL CHECK (confidence >= 0 AND confidence <= 100),
    suspicion_score INT DEFAULT 85,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status alert_status NOT NULL DEFAULT 'OPEN',
    reviewed_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    reviewer_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.alert_evidence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id UUID NOT NULL REFERENCES public.alerts(id) ON DELETE CASCADE,
    storage_path TEXT NOT NULL,
    media_type VARCHAR(50) NOT NULL DEFAULT 'IMAGE_SVG', -- 'IMAGE_JPEG', 'IMAGE_SVG', 'VIDEO_MP4'
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ========================================================
-- 8. IOT HARDWARE DOMAIN (ESP32 ACTUATORS)
-- ========================================================
CREATE TABLE IF NOT EXISTS public.iot_devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_uid VARCHAR(100) UNIQUE NOT NULL,
    device_name VARCHAR(255) NOT NULL,
    location VARCHAR(255) NOT NULL DEFAULT 'Hall 304 - Engineering Wing B',
    ip_address VARCHAR(50) NOT NULL DEFAULT '192.168.1.10',
    firmware_version VARCHAR(50) NOT NULL DEFAULT 'v2.4.1-ai-proctor',
    status iot_status NOT NULL DEFAULT 'ONLINE',
    buzzer_status VARCHAR(50) NOT NULL DEFAULT 'READY',
    led_status VARCHAR(50) NOT NULL DEFAULT 'READY',
    led_color VARCHAR(10) NOT NULL DEFAULT '#10b981',
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.iot_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID NOT NULL REFERENCES public.iot_devices(id) ON DELETE CASCADE,
    exam_session_id UUID REFERENCES public.exam_sessions(id) ON DELETE SET NULL,
    alert_id UUID REFERENCES public.alerts(id) ON DELETE SET NULL,
    event_type iot_event_type NOT NULL,
    command JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(50) NOT NULL DEFAULT 'COMPLETED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ========================================================
-- 9. SYSTEM EVENTS & AUDIT LOGS DOMAIN
-- ========================================================
CREATE TABLE IF NOT EXISTS public.system_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor VARCHAR(255) NOT NULL DEFAULT 'System Invigilator',
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ========================================================
-- 10. INDEXES FOR HIGH FREQUENCY REALTIME & QUERY PATTERNS
-- ========================================================
CREATE INDEX IF NOT EXISTS idx_exams_status ON public.exams(status);
CREATE INDEX IF NOT EXISTS idx_exam_students_exam ON public.exam_students(exam_id);
CREATE INDEX IF NOT EXISTS idx_exam_students_student ON public.exam_students(student_id);
CREATE INDEX IF NOT EXISTS idx_exam_sessions_exam ON public.exam_sessions(exam_id);
CREATE INDEX IF NOT EXISTS idx_detections_session ON public.detections(exam_session_id);
CREATE INDEX IF NOT EXISTS idx_detections_time ON public.detections(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_exam ON public.alerts(exam_id);
CREATE INDEX IF NOT EXISTS idx_alerts_session ON public.alerts(exam_session_id);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON public.alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON public.alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_time ON public.alerts(occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_evidence_alert ON public.alert_evidence(alert_id);
CREATE INDEX IF NOT EXISTS idx_iot_events_device ON public.iot_events(device_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON public.audit_logs(timestamp DESC);

-- ========================================================
-- 11. ROW LEVEL SECURITY (RLS) POLICIES
-- ========================================================
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.students ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.student_face_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exams ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exam_students ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exam_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cameras ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.camera_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.detections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.student_tracking ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.behaviour_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alert_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.iot_devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.iot_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.system_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

-- Helper function: Is Authenticated
CREATE OR REPLACE FUNCTION public.is_authenticated()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN auth.role() = 'authenticated';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Profiles: Authenticated users can view profiles; only self/admin can update
CREATE POLICY "profiles_select" ON public.profiles FOR SELECT USING (true);
CREATE POLICY "profiles_update" ON public.profiles FOR UPDATE USING (auth.uid() = id);

-- Students & Enrollment: Authorized users can read/write student rosters
CREATE POLICY "students_select" ON public.students FOR SELECT USING (true);
CREATE POLICY "students_insert" ON public.students FOR INSERT WITH CHECK (public.is_authenticated() OR auth.role() = 'anon');
CREATE POLICY "students_update" ON public.students FOR UPDATE USING (public.is_authenticated() OR auth.role() = 'anon');

-- BIOMETRICS SECURITY RULE:
-- Face embeddings are NEVER selectable by client browser users.
-- Only server-side service role key (FastAPI AI engine) can access biometric data.
CREATE POLICY "face_profiles_service_role_only" ON public.student_face_profiles
    FOR ALL USING (auth.role() = 'service_role');

-- Exams & Sessions
CREATE POLICY "exams_all" ON public.exams FOR ALL USING (true);
CREATE POLICY "exam_students_all" ON public.exam_students FOR ALL USING (true);
CREATE POLICY "exam_sessions_all" ON public.exam_sessions FOR ALL USING (true);

-- Cameras & Sources (Passwords/Tokens remain hidden)
CREATE POLICY "cameras_all" ON public.cameras FOR ALL USING (true);
CREATE POLICY "camera_sources_select" ON public.camera_sources FOR SELECT USING (true);
CREATE POLICY "camera_sources_insert" ON public.camera_sources FOR INSERT WITH CHECK (true);

-- Detections, Behaviour & Tracking
CREATE POLICY "detections_all" ON public.detections FOR ALL USING (true);
CREATE POLICY "behaviour_events_all" ON public.behaviour_events FOR ALL USING (true);
CREATE POLICY "student_tracking_all" ON public.student_tracking FOR ALL USING (true);

-- Alerts & Evidence
CREATE POLICY "alerts_all" ON public.alerts FOR ALL USING (true);
CREATE POLICY "alert_evidence_all" ON public.alert_evidence FOR ALL USING (true);

-- IoT & Audit
CREATE POLICY "iot_devices_all" ON public.iot_devices FOR ALL USING (true);
CREATE POLICY "iot_events_all" ON public.iot_events FOR ALL USING (true);
CREATE POLICY "system_events_all" ON public.system_events FOR ALL USING (true);
CREATE POLICY "audit_logs_all" ON public.audit_logs FOR ALL USING (true);

-- ========================================================
-- 12. REALTIME CONFIGURATION
-- ========================================================
-- Enable Supabase Realtime publication on high-priority monitoring tables
DO $$ BEGIN
    ALTER PUBLICATION supabase_realtime ADD TABLE public.alerts;
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    ALTER PUBLICATION supabase_realtime ADD TABLE public.iot_devices;
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    ALTER PUBLICATION supabase_realtime ADD TABLE public.iot_events;
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    ALTER PUBLICATION supabase_realtime ADD TABLE public.exam_sessions;
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    ALTER PUBLICATION supabase_realtime ADD TABLE public.cameras;
EXCEPTION WHEN duplicate_object THEN null; END $$;
