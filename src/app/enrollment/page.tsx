'use client';

import React, { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { AppLayout } from '@/components/layout/AppLayout';
import { useStudentAuth } from '@/context/StudentContext';
import { studentApiService } from '@/services/student';
import { StudentProfile, FaceEnrollmentResult } from '@/types';
import { 
  Camera, 
  Upload, 
  CheckCircle2, 
  AlertTriangle, 
  RefreshCw, 
  ShieldCheck, 
  Sparkles,
  User,
  ArrowRight,
  Video,
  FileCheck,
  Info,
  Lock,
  Eye,
  Sliders,
  AlertCircle
} from 'lucide-react';
import { cn } from '@/lib/utils';

type EnrollmentMode = 'WEBCAM' | 'UPLOAD';
type ProcessingState = 'IDLE' | 'PROCESSING' | 'SUCCESS' | 'ERROR';

export default function EnrollmentPage() {
  const router = useRouter();
  const { student, faceStatus, isFaceEnrolled, refreshFaceStatus, setStudentDirectly } = useStudentAuth();

  const [mode, setMode] = useState<EnrollmentMode>('WEBCAM');
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [processingState, setProcessingState] = useState<ProcessingState>('IDLE');
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [enrollmentResult, setEnrollmentResult] = useState<FaceEnrollmentResult | null>(null);
  const [isWebcamActive, setIsWebcamActive] = useState<boolean>(false);
  const [webcamError, setWebcamError] = useState<string | null>(null);

  // Quick candidate switcher for demo / testing
  const [availableCandidates, setAvailableCandidates] = useState<StudentProfile[]>([]);

  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Load exam candidates for switcher
    async function loadCandidates() {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_FASTAPI_URL || 'http://localhost:8000'}/api/v1/students/exam/exam-01`, {
          headers: { 'X-API-Key': process.env.NEXT_PUBLIC_FASTAPI_KEY || 'dev-proctor-secret-key' }
        });
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length > 0) {
            setAvailableCandidates(data);
          }
        }
      } catch (err) {
        console.warn('Could not fetch exam candidate list:', err);
      }
    }
    loadCandidates();
  }, []);

  // Manage webcam stream lifecycle
  useEffect(() => {
    if (mode === 'WEBCAM' && !imagePreview && processingState === 'IDLE') {
      startWebcam();
    } else {
      stopWebcam();
    }

    return () => {
      stopWebcam();
    };
  }, [mode, imagePreview, processingState]);

  const startWebcam = async () => {
    setWebcamError(null);
    try {
      stopWebcam();
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' }
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play().catch(e => console.warn('Video play warning:', e));
      }
      setIsWebcamActive(true);
    } catch (err: any) {
      console.warn('Webcam initialization failed:', err);
      setWebcamError('Webcam access was denied or not available. Please allow camera permissions or use Photo Upload.');
      setIsWebcamActive(false);
    }
  };

  const stopWebcam = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    setIsWebcamActive(false);
  };

  const captureWebcamSnapshot = () => {
    if (!videoRef.current) return;
    const canvas = document.createElement('canvas');
    canvas.width = videoRef.current.videoWidth || 640;
    canvas.height = videoRef.current.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.95);
    setImagePreview(dataUrl);
    setUploadedFile(null);
    stopWebcam();
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadedFile(file);

    const reader = new FileReader();
    reader.onload = () => {
      setImagePreview(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleRetake = () => {
    setImagePreview(null);
    setUploadedFile(null);
    setProcessingState('IDLE');
    setErrorMessage('');
    setStatusMessage('');
    setEnrollmentResult(null);
    if (mode === 'WEBCAM') {
      startWebcam();
    }
  };

  const handleEnroll = async () => {
    if (!student || !imagePreview) return;

    setProcessingState('PROCESSING');
    setStatusMessage('Analyzing facial landmarks with YuNet and extracting SFace 128-D biometric embedding...');
    setErrorMessage('');

    try {
      let result: FaceEnrollmentResult;

      if (uploadedFile && mode === 'UPLOAD') {
        // Option A: Multipart photo upload
        result = await studentApiService.enrollFaceUpload(
          student.id,
          uploadedFile,
          'Enrolled via AI-Proctor Photo Upload Portal'
        );
      } else {
        // Option B: Webcam Base64 snapshot
        result = await studentApiService.enrollFaceBase64(
          student.id,
          imagePreview
        );
      }

      setEnrollmentResult(result);
      setProcessingState('SUCCESS');
      setStatusMessage('Biometric enrollment verified and activated in live surveillance cache.');
      await refreshFaceStatus();
    } catch (err: any) {
      setProcessingState('ERROR');
      setErrorMessage(err.message || 'Face biometric enrollment failed validation.');
    }
  };

  return (
    <AppLayout breadcrumbs={[{ label: 'Dashboard', href: '/dashboard' }, { label: 'Face Enrollment' }]}>
      <div className="space-y-6 max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
                Biometric Face Enrollment
              </h1>
              <span className="flex items-center gap-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 px-2.5 py-0.5 text-xs font-mono font-semibold text-cyan-400">
                <ShieldCheck className="h-3.5 w-3.5" />
                SFace ONNX
              </span>
            </div>
            <p className="mt-1 text-xs sm:text-sm text-slate-400">
              Register high-fidelity 128-D facial embeddings for autonomous live webcam, CCTV, and exam surveillance verification.
            </p>
          </div>

          <Link
            href="/login"
            className="self-start sm:self-auto inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-slate-900/80 px-3.5 py-2 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <User className="h-3.5 w-3.5 text-cyan-400" />
            <span>Switch / Login Candidate</span>
          </Link>
        </div>

        {/* Candidate Identity Card */}
        {student ? (
          <div className="rounded-2xl border border-white/10 bg-gradient-to-r from-slate-900/90 via-slate-900/60 to-slate-950/90 p-5 backdrop-blur-xl shadow-xl">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="h-14 w-14 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center font-extrabold text-xl text-cyan-400 shadow-inner shadow-cyan-500/20">
                  {student.name.charAt(0)}
                </div>
                <div>
                  <div className="flex items-center gap-2.5">
                    <h2 className="text-lg font-bold text-white tracking-tight">{student.name}</h2>
                    {isFaceEnrolled ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/20 border border-emerald-500/40 px-2.5 py-0.5 text-[11px] font-mono font-bold text-emerald-400">
                        <CheckCircle2 className="h-3 w-3" />
                        ENROLLED & ACTIVE
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/20 border border-amber-500/40 px-2.5 py-0.5 text-[11px] font-mono font-bold text-amber-400 animate-pulse">
                        <AlertTriangle className="h-3 w-3" />
                        ENROLLMENT REQUIRED
                      </span>
                    )}
                  </div>
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1 text-xs text-slate-400 font-mono">
                    <span>Roll: <strong className="text-cyan-300">{student.roll_number}</strong></span>
                    <span>•</span>
                    <span>Email: <strong className="text-slate-300">{student.email}</strong></span>
                    <span>•</span>
                    <span>Dept: <strong className="text-slate-300">{student.department || 'Computer Science'}</strong></span>
                  </div>
                </div>
              </div>

              {/* Quick Candidate Switcher dropdown if available */}
              {availableCandidates.length > 1 && (
                <div className="flex items-center gap-2 pt-2 md:pt-0 border-t md:border-t-0 border-white/5">
                  <span className="text-xs text-slate-400">Candidate:</span>
                  <select
                    value={student.id}
                    onChange={(e) => {
                      const found = availableCandidates.find(c => c.id === e.target.value);
                      if (found) {
                        setStudentDirectly(found);
                        handleRetake();
                      }
                    }}
                    className="rounded-xl border border-white/10 bg-slate-950/80 px-3 py-1.5 text-xs text-white focus:border-cyan-500 focus:outline-none"
                  >
                    {availableCandidates.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name} ({c.roll_number})
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-sm flex items-center justify-between">
            <span>No candidate identity currently active. Please log in or select a candidate first.</span>
            <Link href="/login" className="px-3 py-1 bg-amber-500 text-slate-950 font-bold rounded-lg text-xs">
              Go to Login
            </Link>
          </div>
        )}

        {/* Enrollment Interface Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Main Visual Capture & Upload (7 Cols) */}
          <div className="lg:col-span-7 rounded-2xl border border-white/10 bg-slate-900/60 p-5 sm:p-6 backdrop-blur-xl shadow-xl space-y-5">
            {/* Mode Tabs */}
            <div className="flex items-center gap-2 p-1 rounded-xl bg-slate-950/80 border border-white/5">
              <button
                type="button"
                onClick={() => {
                  setMode('WEBCAM');
                  setImagePreview(null);
                  setUploadedFile(null);
                  setProcessingState('IDLE');
                }}
                className={cn(
                  'flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-semibold transition-all',
                  mode === 'WEBCAM'
                    ? 'bg-cyan-500 text-slate-950 shadow-md font-bold'
                    : 'text-slate-400 hover:text-white hover:bg-slate-900'
                )}
              >
                <Camera className="h-4 w-4" />
                <span>Option B: Live Webcam Capture</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setMode('UPLOAD');
                  setImagePreview(null);
                  setUploadedFile(null);
                  setProcessingState('IDLE');
                  stopWebcam();
                }}
                className={cn(
                  'flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-semibold transition-all',
                  mode === 'UPLOAD'
                    ? 'bg-cyan-500 text-slate-950 shadow-md font-bold'
                    : 'text-slate-400 hover:text-white hover:bg-slate-900'
                )}
              >
                <Upload className="h-4 w-4" />
                <span>Option A: Upload Photo (ID/Passport)</span>
              </button>
            </div>

            {/* Viewport Area */}
            <div className="relative aspect-video w-full rounded-2xl overflow-hidden border border-white/10 bg-black flex items-center justify-center shadow-2xl">
              {/* State 1: Image Captured/Uploaded Preview */}
              {imagePreview ? (
                <div className="relative h-full w-full">
                  <img
                    src={imagePreview}
                    alt="Candidate Face Snapshot"
                    className="h-full w-full object-cover"
                  />
                  <div className="absolute top-3 left-3 flex items-center gap-1.5 rounded-full bg-slate-950/80 border border-white/10 px-3 py-1 text-[11px] font-mono text-cyan-300">
                    <FileCheck className="h-3.5 w-3.5" />
                    <span>Captured Frame Ready</span>
                  </div>

                  {processingState === 'IDLE' && (
                    <button
                      onClick={handleRetake}
                      className="absolute top-3 right-3 rounded-xl bg-slate-950/80 border border-white/10 px-3 py-1.5 text-xs text-slate-300 hover:text-white hover:bg-slate-800 transition-colors flex items-center gap-1"
                    >
                      <RefreshCw className="h-3 w-3" />
                      <span>Retake</span>
                    </button>
                  )}
                </div>
              ) : mode === 'WEBCAM' ? (
                /* State 2: Live Webcam with Face Target Overlay */
                <div className="relative h-full w-full flex items-center justify-center bg-slate-950">
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    className="h-full w-full object-cover scale-x-[-1]"
                  />

                  {/* Face Target Oval Overlay */}
                  <div className="absolute inset-0 pointer-events-none flex flex-col items-center justify-center">
                    <div className="w-52 h-64 border-2 border-dashed border-cyan-400/80 rounded-[50%] shadow-[0_0_20px_rgba(6,182,212,0.3)] animate-pulse flex items-center justify-center">
                      <div className="w-48 h-60 border border-cyan-300/40 rounded-[50%]" />
                    </div>
                    <span className="mt-3 text-xs font-mono font-medium text-cyan-300 bg-slate-950/80 px-3 py-1 rounded-full border border-cyan-500/30">
                      Center face within oval
                    </span>
                  </div>

                  {webcamError && (
                    <div className="absolute inset-0 bg-slate-950/90 p-6 flex flex-col items-center justify-center text-center">
                      <AlertTriangle className="h-10 w-10 text-amber-400 mb-2" />
                      <p className="text-sm text-slate-300 max-w-sm mb-4">{webcamError}</p>
                      <button
                        onClick={() => setMode('UPLOAD')}
                        className="px-4 py-2 rounded-xl bg-cyan-500 text-slate-950 font-bold text-xs"
                      >
                        Switch to Photo Upload
                      </button>
                    </div>
                  )}

                  <div className="absolute bottom-3 left-3 text-[10px] font-mono text-slate-400 bg-black/60 px-2.5 py-1 rounded-md">
                    Webcam Feed: 640x480 • 30FPS
                  </div>
                </div>
              ) : (
                /* State 3: Drag & Drop File Upload Area */
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="h-full w-full p-8 flex flex-col items-center justify-center text-center cursor-pointer border-2 border-dashed border-white/10 hover:border-cyan-500/50 hover:bg-cyan-500/[0.02] transition-all group"
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                  <div className="h-16 w-16 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 group-hover:scale-110 transition-transform mb-3">
                    <Upload className="h-8 w-8" />
                  </div>
                  <h3 className="text-sm font-bold text-white group-hover:text-cyan-300 transition-colors">
                    Click to browse or drag & drop photo
                  </h3>
                  <p className="text-xs text-slate-400 mt-1 max-w-xs">
                    Supports high-resolution PNG, JPG, or WEBP portrait photos (up to 10MB).
                  </p>
                </div>
              )}

              {/* Processing Overlay */}
              {processingState === 'PROCESSING' && (
                <div className="absolute inset-0 bg-slate-950/90 backdrop-blur-md flex flex-col items-center justify-center p-6 text-center z-20">
                  <div className="relative flex items-center justify-center mb-4">
                    <div className="h-16 w-16 rounded-full border-4 border-cyan-500/20 border-t-cyan-400 animate-spin" />
                    <Sparkles className="h-6 w-6 text-cyan-400 absolute" />
                  </div>
                  <h4 className="text-base font-bold text-white">Extracting Biometrics</h4>
                  <p className="text-xs text-slate-400 max-w-sm mt-1">{statusMessage}</p>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row items-center gap-3">
              {mode === 'WEBCAM' && !imagePreview && (
                <button
                  type="button"
                  onClick={captureWebcamSnapshot}
                  disabled={!isWebcamActive || processingState === 'PROCESSING'}
                  className="w-full sm:flex-1 py-3 px-4 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 text-white font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-cyan-950/60 transition-all hover:scale-[1.01]"
                >
                  <Camera className="h-4 w-4" />
                  <span>Capture Biometric Snapshot</span>
                </button>
              )}

              {imagePreview && processingState !== 'SUCCESS' && (
                <>
                  <button
                    type="button"
                    onClick={handleRetake}
                    disabled={processingState === 'PROCESSING'}
                    className="w-full sm:w-auto py-3 px-5 rounded-xl border border-white/10 bg-slate-800/80 hover:bg-slate-700 text-slate-200 font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors"
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                    <span>Retake</span>
                  </button>

                  <button
                    type="button"
                    onClick={handleEnroll}
                    disabled={processingState === 'PROCESSING'}
                    className="w-full sm:flex-1 py-3 px-4 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-emerald-950/60 transition-all hover:scale-[1.01]"
                  >
                    <ShieldCheck className="h-4 w-4" />
                    <span>Confirm & Enroll Biometrics</span>
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Right Column: Feedback, Quality Criteria & Privacy Guarantees (5 Cols) */}
          <div className="lg:col-span-5 space-y-6">
            {/* Feedback Result Card */}
            {processingState === 'SUCCESS' && enrollmentResult ? (
              <div className="rounded-2xl border border-emerald-500/40 bg-gradient-to-br from-emerald-950/40 via-slate-900/90 to-slate-950/90 p-5 backdrop-blur-xl shadow-2xl space-y-4 animate-in fade-in">
                <div className="flex items-center gap-3 pb-3 border-b border-white/10">
                  <div className="h-10 w-10 rounded-xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                    <CheckCircle2 className="h-6 w-6" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-white">Enrollment Successful</h3>
                    <p className="text-xs text-emerald-400 font-medium">Biometric profile activated in live memory</p>
                  </div>
                </div>

                <div className="space-y-2.5 text-xs font-mono">
                  <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-950/80 border border-white/5">
                    <span className="text-slate-400">Quality Score</span>
                    <span className="text-emerald-400 font-bold">
                      {Math.round((enrollmentResult.quality_score || 0.95) * 100)}% Verified
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-950/80 border border-white/5">
                    <span className="text-slate-400">Biometric Engine</span>
                    <span className="text-cyan-400 font-bold">
                      {enrollmentResult.model_version || 'sface-onnx-v1'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-950/80 border border-white/5">
                    <span className="text-slate-400">Vector Space</span>
                    <span className="text-slate-200">128-D L2-Normalized</span>
                  </div>
                  <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-950/80 border border-white/5">
                    <span className="text-slate-400">Exam Scope</span>
                    <span className="text-indigo-400 font-bold">exam-01 Biometric Cache</span>
                  </div>
                </div>

                <div className="pt-2 flex flex-col gap-2">
                  <Link
                    href="/monitoring"
                    className="w-full py-2.5 px-4 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs flex items-center justify-center gap-1.5 transition-all shadow-md shadow-cyan-500/20"
                  >
                    <Video className="h-3.5 w-3.5" />
                    <span>Test in Live Camera Surveillance</span>
                  </Link>
                  <Link
                    href="/dashboard"
                    className="w-full py-2.5 px-4 rounded-xl border border-white/10 bg-slate-800/80 hover:bg-slate-700 text-slate-200 font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors"
                  >
                    <span>Return to Dashboard</span>
                    <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
              </div>
            ) : processingState === 'ERROR' ? (
              <div className="rounded-2xl border border-rose-500/40 bg-gradient-to-br from-rose-950/40 via-slate-900/90 to-slate-950/90 p-5 backdrop-blur-xl shadow-2xl space-y-4 animate-in fade-in">
                <div className="flex items-center gap-3 pb-3 border-b border-white/10">
                  <div className="h-10 w-10 rounded-xl bg-rose-500/20 border border-rose-500/30 flex items-center justify-center text-rose-400">
                    <AlertCircle className="h-6 w-6" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-white">Enrollment Rejected</h3>
                    <p className="text-xs text-rose-400 font-medium">Quality or Validation Failure</p>
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-200">
                  <p className="font-semibold text-rose-300 mb-1">Reason:</p>
                  <p>{errorMessage}</p>
                </div>

                <div className="space-y-1 text-xs text-slate-400">
                  <p className="font-semibold text-slate-300">Remediation steps:</p>
                  <ul className="list-disc list-inside space-y-0.5 text-[11px]">
                    <li>Ensure only ONE face is visible in the frame.</li>
                    <li>Look directly at the lens with eyes open and visible.</li>
                    <li>Move closer if the face appears too small.</li>
                    <li>Ensure clear frontal lighting without deep shadows.</li>
                  </ul>
                </div>

                <button
                  type="button"
                  onClick={handleRetake}
                  className="w-full py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs flex items-center justify-center gap-1.5 transition-colors"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  <span>Try Again / Re-capture</span>
                </button>
              </div>
            ) : null}

            {/* Quality & Guidance Checklist */}
            <div className="rounded-2xl border border-white/5 bg-slate-900/60 p-5 backdrop-blur-xl shadow-xl space-y-3.5">
              <div className="flex items-center gap-2 pb-2 border-b border-white/5">
                <Sliders className="h-4 w-4 text-cyan-400" />
                <h3 className="text-sm font-bold text-white">Biometric Quality Requirements</h3>
              </div>

              <div className="space-y-2.5 text-xs">
                <div className="flex items-start gap-2.5 text-slate-300">
                  <CheckCircle2 className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
                  <div>
                    <strong className="text-white">Strict Frontal Angle:</strong>
                    <span className="text-slate-400 block text-[11px]">Face directly towards the camera; yaw/pitch within ±15 degrees.</span>
                  </div>
                </div>

                <div className="flex items-start gap-2.5 text-slate-300">
                  <CheckCircle2 className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
                  <div>
                    <strong className="text-white">Isolated Single Subject:</strong>
                    <span className="text-slate-400 block text-[11px]">No background individuals or multiple faces in the frame.</span>
                  </div>
                </div>

                <div className="flex items-start gap-2.5 text-slate-300">
                  <CheckCircle2 className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
                  <div>
                    <strong className="text-white">Neutral Expression & Open Eyes:</strong>
                    <span className="text-slate-400 block text-[11px]">No tinted sunglasses, hats, masks, or heavy obstruction.</span>
                  </div>
                </div>

                <div className="flex items-start gap-2.5 text-slate-300">
                  <CheckCircle2 className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
                  <div>
                    <strong className="text-white">Adequate Lighting:</strong>
                    <span className="text-slate-400 block text-[11px]">Avoid strong backlighting or dark, underexposed environments.</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Zero Biometric Leakage Guarantee */}
            <div className="rounded-2xl border border-white/5 bg-slate-900/60 p-5 backdrop-blur-xl shadow-xl space-y-2.5">
              <div className="flex items-center gap-2 text-emerald-400">
                <Lock className="h-4 w-4" />
                <h3 className="text-xs font-bold uppercase tracking-wider">Zero Biometric Leakage</h3>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Raw 128-dimensional biometric embeddings are stored strictly server-side within encrypted vector tables or secure in-memory caches. Embeddings are never exposed in browser storage, network responses, or client logs.
              </p>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
