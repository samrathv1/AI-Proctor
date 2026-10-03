'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Student } from '@/types';
import { 
  Camera, 
  Upload, 
  CheckCircle2, 
  AlertTriangle, 
  RefreshCw, 
  ShieldCheck, 
  Sparkles,
  User,
  Sliders
} from 'lucide-react';

interface FaceEnrollmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  student: Student | null;
  onSuccess?: (studentId: string, qualityScore: number) => void;
}

type Mode = 'UPLOAD' | 'WEBCAM';
type StatusState = 'IDLE' | 'PROCESSING' | 'VERIFIED' | 'FAILED';

export function FaceEnrollmentModal({
  isOpen,
  onClose,
  student,
  onSuccess
}: FaceEnrollmentModalProps) {
  const [mode, setMode] = useState<Mode>('WEBCAM');
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [status, setStatus] = useState<StatusState>('IDLE');
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [qualityScore, setQualityScore] = useState<number | null>(null);
  const [modelVersion, setModelVersion] = useState<string>('');
  const [isWebcamActive, setIsWebcamActive] = useState<boolean>(false);

  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Initialize/Stop webcam when modal opens or mode switches
  useEffect(() => {
    if (isOpen && mode === 'WEBCAM' && !imagePreview) {
      startWebcam();
    } else {
      stopWebcam();
    }
    return () => {
      stopWebcam();
    };
  }, [isOpen, mode, imagePreview]);

  // Reset state on open/close
  useEffect(() => {
    if (!isOpen) {
      setImagePreview(null);
      setStatus('IDLE');
      setStatusMessage('');
      setQualityScore(null);
      stopWebcam();
    }
  }, [isOpen]);

  const startWebcam = async () => {
    try {
      stopWebcam();
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' }
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
      setIsWebcamActive(true);
    } catch (err) {
      console.warn('Webcam initialization failed:', err);
      setIsWebcamActive(false);
      setMode('UPLOAD');
    }
  };

  const stopWebcam = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    setIsWebcamActive(false);
  };

  const captureWebcamFrame = () => {
    if (!videoRef.current) return;
    const canvas = document.createElement('canvas');
    canvas.width = videoRef.current.videoWidth || 640;
    canvas.height = videoRef.current.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
    setImagePreview(dataUrl);
    stopWebcam();
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      setImagePreview(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleEnroll = async () => {
    if (!student || !imagePreview) return;

    setStatus('PROCESSING');
    setStatusMessage('Running YuNet face detection & SFace biometric embedding extraction...');

    try {
      const backendUrl = process.env.NEXT_PUBLIC_FASTAPI_URL || 'http://localhost:8000';
      const apiKey = process.env.NEXT_PUBLIC_FASTAPI_KEY || 'dev-proctor-secret-key';

      const response = await fetch(`${backendUrl}/api/v1/enrollment/face`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey
        },
        body: JSON.stringify({
          student_id: student.id,
          image_base64: imagePreview,
          notes: 'Enrolled via Examination Hall Terminal'
        })
      });

      const data = await response.json();

      if (response.ok && data.status === 'VERIFIED') {
        setStatus('VERIFIED');
        setStatusMessage(data.message || 'Face biometric profile enrolled and verified.');
        setQualityScore(data.quality_score);
        setModelVersion(data.model_version || 'sface-onnx-v1');
        if (onSuccess) {
          onSuccess(student.id, data.quality_score);
        }
      } else {
        setStatus('FAILED');
        setStatusMessage(data.detail || 'Biometric enrollment failed quality or validation checks.');
      }
    } catch (err: any) {
      setStatus('FAILED');
      setStatusMessage(`Connection Error: Ensure AI-Proctor FastAPI backend is running on port 8000. (${err.message})`);
    }
  };

  const handleRetake = () => {
    setImagePreview(null);
    setStatus('IDLE');
    setStatusMessage('');
    setQualityScore(null);
    if (mode === 'WEBCAM') {
      startWebcam();
    }
  };

  if (!student) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Biometric Face Enrollment"
      subtitle={`Enrolling candidate identity for ${student.name} (${student.rollNumber})`}
      maxWidth="lg"
    >
      <div className="space-y-4">
        {/* Candidate Summary Banner */}
        <div className="flex items-center justify-between p-3 rounded-xl bg-slate-800/60 border border-white/5">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center font-bold text-cyan-400">
              {student.avatar || <User className="h-5 w-5" />}
            </div>
            <div>
              <div className="text-sm font-bold text-white">{student.name}</div>
              <div className="text-xs font-mono text-cyan-400">{student.rollNumber} • Desk {student.seatNumber || 'N/A'}</div>
            </div>
          </div>
          <div className="text-right text-xs">
            <span className="text-slate-400">Status: </span>
            <span className="font-semibold text-slate-200">{student.status}</span>
          </div>
        </div>

        {/* Mode Selector Tabs */}
        {status !== 'VERIFIED' && (
          <div className="flex gap-2 p-1 rounded-xl bg-slate-900 border border-white/5">
            <button
              onClick={() => { setMode('WEBCAM'); setImagePreview(null); }}
              className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-semibold transition-all ${
                mode === 'WEBCAM'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Camera className="h-4 w-4" />
              <span>Live Webcam Capture</span>
            </button>
            <button
              onClick={() => { setMode('UPLOAD'); setImagePreview(null); stopWebcam(); }}
              className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-semibold transition-all ${
                mode === 'UPLOAD'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Upload className="h-4 w-4" />
              <span>Upload Photograph</span>
            </button>
          </div>
        )}

        {/* Viewport & Capture Area */}
        <div className="relative aspect-video rounded-2xl overflow-hidden bg-slate-950 border border-white/10 flex items-center justify-center">
          {imagePreview ? (
            <div className="relative w-full h-full">
              <img
                src={imagePreview}
                alt="Face Capture"
                className="w-full h-full object-cover"
              />
              {/* Face Guide Target Overlay */}
              <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                <div className="w-44 h-56 rounded-full border-2 border-dashed border-cyan-400/60 shadow-[0_0_20px_rgba(6,182,212,0.2)]" />
              </div>
            </div>
          ) : mode === 'WEBCAM' ? (
            <div className="relative w-full h-full">
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover -scale-x-100"
              />
              <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                <div className="w-44 h-56 rounded-full border-2 border-dashed border-cyan-400/60 shadow-[0_0_20px_rgba(6,182,212,0.3)] animate-pulse" />
              </div>
            </div>
          ) : (
            <div
              onClick={() => fileInputRef.current?.click()}
              className="flex flex-col items-center justify-center p-6 text-center cursor-pointer hover:bg-white/5 transition-colors w-full h-full"
            >
              <Upload className="h-10 w-10 text-cyan-400 mb-2 opacity-80" />
              <div className="text-sm font-semibold text-white">Click or drag photo here</div>
              <div className="text-xs text-slate-400 mt-1">JPEG, PNG or WebP (min. 200x200px)</div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={handleFileUpload}
              />
            </div>
          )}
        </div>

        {/* Status / Results Feedback */}
        {status !== 'IDLE' && (
          <div
            className={`p-3.5 rounded-xl border text-xs flex items-start gap-3 ${
              status === 'VERIFIED'
                ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-300'
                : status === 'FAILED'
                ? 'bg-rose-950/40 border-rose-500/30 text-rose-300'
                : 'bg-cyan-950/40 border-cyan-500/30 text-cyan-300'
            }`}
          >
            {status === 'VERIFIED' && <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />}
            {status === 'FAILED' && <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />}
            {status === 'PROCESSING' && <RefreshCw className="h-5 w-5 text-cyan-400 animate-spin shrink-0 mt-0.5" />}

            <div className="space-y-1 flex-1">
              <div className="font-bold flex items-center justify-between">
                <span>
                  {status === 'VERIFIED' && 'BIOMETRIC PROFILE VERIFIED'}
                  {status === 'FAILED' && 'ENROLLMENT REJECTED'}
                  {status === 'PROCESSING' && 'EXTRACTING BIOMETRICS'}
                </span>
                {qualityScore !== null && (
                  <span className="font-mono text-[11px] bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded-md border border-emerald-500/30">
                    Quality: {qualityScore}/100
                  </span>
                )}
              </div>
              <div className="text-slate-300 text-[11px] leading-relaxed">{statusMessage}</div>
              {modelVersion && (
                <div className="text-[10px] text-slate-400 font-mono">
                  Engine: {modelVersion} • Vector: 128-d L2-Normalized (Server Secured)
                </div>
              )}
            </div>
          </div>
        )}

        {/* Action Controls */}
        <div className="flex items-center justify-end gap-3 pt-2">
          {imagePreview ? (
            <>
              <button
                type="button"
                onClick={handleRetake}
                disabled={status === 'PROCESSING'}
                className="px-4 py-2 text-xs font-semibold text-slate-300 hover:text-white rounded-xl bg-slate-800 hover:bg-slate-700 transition-colors"
              >
                Retake Photo
              </button>
              {status !== 'VERIFIED' && (
                <button
                  type="button"
                  onClick={handleEnroll}
                  disabled={status === 'PROCESSING'}
                  className="px-5 py-2 text-xs font-bold text-slate-950 rounded-xl bg-gradient-to-r from-cyan-400 to-emerald-400 hover:from-cyan-300 hover:to-emerald-300 transition-all shadow-lg shadow-cyan-500/20 flex items-center gap-2"
                >
                  {status === 'PROCESSING' ? (
                    <>
                      <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                      <span>Processing...</span>
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="h-3.5 w-3.5" />
                      <span>Verify & Enroll Biometrics</span>
                    </>
                  )}
                </button>
              )}
            </>
          ) : mode === 'WEBCAM' ? (
            <button
              type="button"
              onClick={captureWebcamFrame}
              disabled={!isWebcamActive}
              className="px-5 py-2 text-xs font-bold text-slate-950 rounded-xl bg-cyan-400 hover:bg-cyan-300 transition-colors flex items-center gap-2 shadow-lg shadow-cyan-500/20"
            >
              <Camera className="h-3.5 w-3.5" />
              <span>Capture Snapshot</span>
            </button>
          ) : null}

          {status === 'VERIFIED' && (
            <button
              type="button"
              onClick={onClose}
              className="px-5 py-2 text-xs font-bold text-white rounded-xl bg-slate-800 hover:bg-slate-700 transition-colors"
            >
              Done
            </button>
          )}
        </div>
      </div>
    </Modal>
  );
}
