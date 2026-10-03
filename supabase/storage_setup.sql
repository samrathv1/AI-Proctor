-- ========================================================
-- AI-PROCTOR SECURE STORAGE BUCKETS & POLICIES
-- ========================================================

-- 1. Create Private Storage Buckets (Zero Public Access to Biometric / Surveillance Evidence)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES 
    (
        'student-photos', 
        'student-photos', 
        false, 
        10485760, -- 10MB limit
        ARRAY['image/jpeg', 'image/png', 'image/webp']
    ),
    (
        'alert-evidence', 
        'alert-evidence', 
        false, 
        20971520, -- 20MB limit
        ARRAY['image/jpeg', 'image/png', 'image/svg+xml', 'video/mp4']
    ),
    (
        'exam-videos', 
        'exam-videos', 
        false, 
        1073741824, -- 1GB limit
        ARRAY['video/mp4', 'video/webm']
    )
ON CONFLICT (id) DO UPDATE SET 
    public = false,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

-- 2. Storage Objects RLS Policies
-- Allow Authenticated Users (Invigilators/Admins) to read evidence and photos
DO $$ BEGIN
    CREATE POLICY "authenticated_select_student_photos" ON storage.objects
        FOR SELECT TO authenticated
        USING (bucket_id = 'student-photos');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE POLICY "authenticated_select_alert_evidence" ON storage.objects
        FOR SELECT TO authenticated
        USING (bucket_id = 'alert-evidence');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE POLICY "authenticated_select_exam_videos" ON storage.objects
        FOR SELECT TO authenticated
        USING (bucket_id = 'exam-videos');
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- Service Role (FastAPI AI Engine) has full bypass to manage storage objects
-- Supabase automatically grants service_role full storage permissions.
