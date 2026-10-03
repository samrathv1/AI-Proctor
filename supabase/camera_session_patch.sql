-- ========================================================
-- CAMERA & SESSION ID COMPATIBILITY PATCH
-- Supports alphanumeric IDs ('cam-01', 'ses-exam-01')
-- ========================================================

-- 1. Drop constraints
ALTER TABLE public.camera_sources DROP CONSTRAINT IF EXISTS camera_sources_camera_id_fkey;
ALTER TABLE public.student_tracking DROP CONSTRAINT IF EXISTS student_tracking_camera_id_fkey;
ALTER TABLE public.student_tracking DROP CONSTRAINT IF EXISTS student_tracking_exam_session_id_fkey;
ALTER TABLE public.detections DROP CONSTRAINT IF EXISTS detections_camera_id_fkey;
ALTER TABLE public.detections DROP CONSTRAINT IF EXISTS detections_exam_session_id_fkey;
ALTER TABLE public.behaviour_events DROP CONSTRAINT IF EXISTS behaviour_events_camera_id_fkey;
ALTER TABLE public.behaviour_events DROP CONSTRAINT IF EXISTS behaviour_events_exam_session_id_fkey;
ALTER TABLE public.alerts DROP CONSTRAINT IF EXISTS alerts_camera_id_fkey;
ALTER TABLE public.alerts DROP CONSTRAINT IF EXISTS alerts_exam_session_id_fkey;
ALTER TABLE public.iot_events DROP CONSTRAINT IF EXISTS iot_events_exam_session_id_fkey;

-- 2. Alter column types
ALTER TABLE public.cameras ALTER COLUMN id TYPE VARCHAR(100);
ALTER TABLE public.camera_sources ALTER COLUMN camera_id TYPE VARCHAR(100);
ALTER TABLE public.exam_sessions ALTER COLUMN id TYPE VARCHAR(100);

ALTER TABLE public.student_tracking ALTER COLUMN camera_id TYPE VARCHAR(100);
ALTER TABLE public.student_tracking ALTER COLUMN exam_session_id TYPE VARCHAR(100);

ALTER TABLE public.detections ALTER COLUMN camera_id TYPE VARCHAR(100);
ALTER TABLE public.detections ALTER COLUMN exam_session_id TYPE VARCHAR(100);

ALTER TABLE public.behaviour_events ALTER COLUMN camera_id TYPE VARCHAR(100);
ALTER TABLE public.behaviour_events ALTER COLUMN exam_session_id TYPE VARCHAR(100);

ALTER TABLE public.alerts ALTER COLUMN camera_id TYPE VARCHAR(100);
ALTER TABLE public.alerts ALTER COLUMN exam_session_id TYPE VARCHAR(100);

ALTER TABLE public.iot_events ALTER COLUMN exam_session_id TYPE VARCHAR(100);

-- 3. Re-add foreign key constraints
ALTER TABLE public.camera_sources 
    ADD CONSTRAINT camera_sources_camera_id_fkey 
    FOREIGN KEY (camera_id) REFERENCES public.cameras(id) ON DELETE CASCADE;

ALTER TABLE public.student_tracking 
    ADD CONSTRAINT student_tracking_camera_id_fkey 
    FOREIGN KEY (camera_id) REFERENCES public.cameras(id) ON DELETE SET NULL;

ALTER TABLE public.detections 
    ADD CONSTRAINT detections_camera_id_fkey 
    FOREIGN KEY (camera_id) REFERENCES public.cameras(id) ON DELETE SET NULL;

ALTER TABLE public.behaviour_events 
    ADD CONSTRAINT behaviour_events_camera_id_fkey 
    FOREIGN KEY (camera_id) REFERENCES public.cameras(id) ON DELETE SET NULL;

ALTER TABLE public.alerts 
    ADD CONSTRAINT alerts_camera_id_fkey 
    FOREIGN KEY (camera_id) REFERENCES public.cameras(id) ON DELETE SET NULL;
