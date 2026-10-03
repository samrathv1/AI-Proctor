-- ========================================================
-- AI-PROCTOR SCHEMA COMPATIBILITY PATCH
-- Supports both alphanumeric domain keys ('s-01', 'exam-01')
-- and standard 36-char UUIDs while preserving all FK constraints.
-- ========================================================

-- 1. Ensure invigilator_name exists on exams
ALTER TABLE public.exams ADD COLUMN IF NOT EXISTS invigilator_name VARCHAR(255) DEFAULT 'Dr. Robert Vance, Ph.D.';

-- 2. Drop FK constraints temporarily to alter types
ALTER TABLE public.student_face_profiles DROP CONSTRAINT IF EXISTS student_face_profiles_student_id_fkey;
ALTER TABLE public.exam_students DROP CONSTRAINT IF EXISTS exam_students_student_id_fkey;
ALTER TABLE public.exam_students DROP CONSTRAINT IF EXISTS exam_students_exam_id_fkey;
ALTER TABLE public.exam_sessions DROP CONSTRAINT IF EXISTS exam_sessions_exam_id_fkey;
ALTER TABLE public.detections DROP CONSTRAINT IF EXISTS detections_student_id_fkey;
ALTER TABLE public.student_tracking DROP CONSTRAINT IF EXISTS student_tracking_student_id_fkey;
ALTER TABLE public.behaviour_events DROP CONSTRAINT IF EXISTS behaviour_events_student_id_fkey;
ALTER TABLE public.alerts DROP CONSTRAINT IF EXISTS alerts_student_id_fkey;
ALTER TABLE public.alerts DROP CONSTRAINT IF EXISTS alerts_exam_id_fkey;

-- 3. Alter columns to VARCHAR(100)
ALTER TABLE public.students ALTER COLUMN id TYPE VARCHAR(100);
ALTER TABLE public.student_face_profiles ALTER COLUMN student_id TYPE VARCHAR(100);
ALTER TABLE public.exams ALTER COLUMN id TYPE VARCHAR(100);
ALTER TABLE public.exam_students ALTER COLUMN student_id TYPE VARCHAR(100);
ALTER TABLE public.exam_students ALTER COLUMN exam_id TYPE VARCHAR(100);
ALTER TABLE public.exam_sessions ALTER COLUMN exam_id TYPE VARCHAR(100);
ALTER TABLE public.detections ALTER COLUMN student_id TYPE VARCHAR(100);
ALTER TABLE public.student_tracking ALTER COLUMN student_id TYPE VARCHAR(100);
ALTER TABLE public.behaviour_events ALTER COLUMN student_id TYPE VARCHAR(100);
ALTER TABLE public.alerts ALTER COLUMN student_id TYPE VARCHAR(100);
ALTER TABLE public.alerts ALTER COLUMN exam_id TYPE VARCHAR(100);

-- 4. Re-establish all FK constraints with exact ON DELETE behavior
ALTER TABLE public.student_face_profiles 
    ADD CONSTRAINT student_face_profiles_student_id_fkey 
    FOREIGN KEY (student_id) REFERENCES public.students(id) ON DELETE CASCADE;

ALTER TABLE public.exam_students 
    ADD CONSTRAINT exam_students_student_id_fkey 
    FOREIGN KEY (student_id) REFERENCES public.students(id) ON DELETE CASCADE;

ALTER TABLE public.exam_students 
    ADD CONSTRAINT exam_students_exam_id_fkey 
    FOREIGN KEY (exam_id) REFERENCES public.exams(id) ON DELETE CASCADE;

ALTER TABLE public.exam_sessions 
    ADD CONSTRAINT exam_sessions_exam_id_fkey 
    FOREIGN KEY (exam_id) REFERENCES public.exams(id) ON DELETE CASCADE;

ALTER TABLE public.detections 
    ADD CONSTRAINT detections_student_id_fkey 
    FOREIGN KEY (student_id) REFERENCES public.students(id) ON DELETE SET NULL;

ALTER TABLE public.student_tracking 
    ADD CONSTRAINT student_tracking_student_id_fkey 
    FOREIGN KEY (student_id) REFERENCES public.students(id) ON DELETE SET NULL;

ALTER TABLE public.behaviour_events 
    ADD CONSTRAINT behaviour_events_student_id_fkey 
    FOREIGN KEY (student_id) REFERENCES public.students(id) ON DELETE SET NULL;

ALTER TABLE public.alerts 
    ADD CONSTRAINT alerts_student_id_fkey 
    FOREIGN KEY (student_id) REFERENCES public.students(id) ON DELETE SET NULL;

ALTER TABLE public.alerts 
    ADD CONSTRAINT alerts_exam_id_fkey 
    FOREIGN KEY (exam_id) REFERENCES public.exams(id) ON DELETE CASCADE;
