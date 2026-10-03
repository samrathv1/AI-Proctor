'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useStudentAuth } from '@/context/StudentContext';
import { 
  Shield, 
  User, 
  LogIn, 
  UserPlus, 
  ArrowRight, 
  CheckCircle2, 
  AlertTriangle, 
  Sparkles,
  Lock,
  GraduationCap,
  Building,
  Mail,
  Hash
} from 'lucide-react';
import { cn } from '@/lib/utils';

export default function LoginPage() {
  const router = useRouter();
  const { login, register, student } = useStudentAuth();

  const [activeTab, setActiveTab] = useState<'LOGIN' | 'REGISTER'>('LOGIN');

  // Login form state
  const [loginIdentifier, setLoginIdentifier] = useState('CS-2026-042');
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  // Register form state
  const [regName, setRegName] = useState('');
  const [regRoll, setRegRoll] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regDept, setRegDept] = useState('Computer Science');
  const [regClass, setRegClass] = useState('BE-IV-A');
  const [regLoading, setRegLoading] = useState(false);
  const [regError, setRegError] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginIdentifier.trim()) return;

    setLoginLoading(true);
    setLoginError(null);

    const res = await login(loginIdentifier.trim());
    setLoginLoading(false);

    if (res.success) {
      if (res.faceEnrolled) {
        router.push('/dashboard');
      } else {
        router.push('/enrollment');
      }
    } else {
      setLoginError(res.error || 'Student candidate not found. Please verify your roll number.');
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!regName.trim() || !regRoll.trim() || !regEmail.trim()) {
      setRegError('Please complete all required fields.');
      return;
    }

    setRegLoading(true);
    setRegError(null);

    const res = await register({
      name: regName.trim(),
      roll_number: regRoll.trim(),
      email: regEmail.trim(),
      department: regDept.trim(),
      class_name: regClass.trim()
    });

    setRegLoading(false);

    if (res.success) {
      // Newly registered candidates proceed straight to face enrollment
      router.push('/enrollment');
    } else {
      setRegError(res.error || 'Registration failed. Roll number or email may already exist.');
    }
  };

  return (
    <div className="min-h-screen bg-[#080c14] text-slate-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative overflow-hidden">
      {/* Background Cyber Grid */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(6,182,212,0.03)_1px,transparent_1px),linear-gradient(to_bottom,rgba(6,182,212,0.03)_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none" />
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 bg-cyan-500/10 rounded-full blur-[120px] pointer-events-none" />

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        {/* Brand Header */}
        <div className="flex flex-col items-center text-center">
          <div className="relative flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-tr from-cyan-600 via-cyan-500 to-emerald-400 p-0.5 shadow-xl shadow-cyan-500/25">
            <div className="flex h-full w-full items-center justify-center rounded-[14px] bg-slate-950">
              <Shield className="h-7 w-7 text-cyan-400" />
            </div>
          </div>
          <h2 className="mt-4 text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
            AI-PROCTOR
          </h2>
          <p className="mt-1 text-xs font-mono tracking-widest uppercase text-cyan-400 font-semibold">
            Candidate Identity & Biometric Verification
          </p>
        </div>

        {/* Auth Box */}
        <div className="mt-8 bg-slate-900/80 border border-white/10 rounded-2xl p-6 sm:p-8 backdrop-blur-2xl shadow-2xl space-y-6">
          {/* Tabs */}
          <div className="flex items-center gap-2 p-1 rounded-xl bg-slate-950/80 border border-white/5">
            <button
              type="button"
              onClick={() => setActiveTab('LOGIN')}
              className={cn(
                'flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-xs font-semibold transition-all',
                activeTab === 'LOGIN'
                  ? 'bg-cyan-500 text-slate-950 shadow-md font-bold'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900'
              )}
            >
              <LogIn className="h-3.5 w-3.5" />
              <span>Candidate Login</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('REGISTER')}
              className={cn(
                'flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-xs font-semibold transition-all',
                activeTab === 'REGISTER'
                  ? 'bg-cyan-500 text-slate-950 shadow-md font-bold'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900'
              )}
            >
              <UserPlus className="h-3.5 w-3.5" />
              <span>Register Candidate</span>
            </button>
          </div>

          {activeTab === 'LOGIN' ? (
            /* Login Form */
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Roll Number or Institutional Email
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Hash className="h-4 w-4" />
                  </div>
                  <input
                    type="text"
                    required
                    value={loginIdentifier}
                    onChange={(e) => setLoginIdentifier(e.target.value)}
                    placeholder="e.g. CS-2026-042 or dev.sharma@exam.edu"
                    className="w-full rounded-xl border border-white/10 bg-slate-950/80 pl-10 pr-4 py-2.5 text-sm text-white placeholder-slate-500 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 focus:outline-none font-mono"
                  />
                </div>
              </div>

              {loginError && (
                <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
                  {loginError}
                </div>
              )}

              {/* Quick Preset Buttons for Evaluation */}
              <div className="pt-1">
                <span className="text-[11px] text-slate-400 block mb-1.5">Quick candidate test presets:</span>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <button
                    type="button"
                    onClick={() => setLoginIdentifier('CS-2026-042')}
                    className="p-2 rounded-lg bg-slate-950/60 border border-white/5 hover:border-cyan-500/40 text-left transition-colors"
                  >
                    <div className="font-semibold text-white">Dev Sharma</div>
                    <div className="text-[10px] text-emerald-400 font-mono">CS-2026-042 (Enrolled)</div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setLoginIdentifier('CS-2026-044')}
                    className="p-2 rounded-lg bg-slate-950/60 border border-white/5 hover:border-cyan-500/40 text-left transition-colors"
                  >
                    <div className="font-semibold text-white">Rahul Verma</div>
                    <div className="text-[10px] text-amber-400 font-mono">CS-2026-044 (Pending)</div>
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loginLoading}
                className="w-full mt-2 py-3 px-4 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 text-white font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-cyan-950/60 transition-all hover:scale-[1.01]"
              >
                {loginLoading ? (
                  <span>Authenticating...</span>
                ) : (
                  <>
                    <span>Verify Identity</span>
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </form>
          ) : (
            /* Register Form */
            <form onSubmit={handleRegister} className="space-y-3.5">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Full Name *
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <User className="h-4 w-4" />
                  </div>
                  <input
                    type="text"
                    required
                    value={regName}
                    onChange={(e) => setRegName(e.target.value)}
                    placeholder="e.g. Ananya Roy"
                    className="w-full rounded-xl border border-white/10 bg-slate-950/80 pl-10 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Roll Number *
                  </label>
                  <input
                    type="text"
                    required
                    value={regRoll}
                    onChange={(e) => setRegRoll(e.target.value)}
                    placeholder="e.g. CS-2026-088"
                    className="w-full rounded-xl border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none font-mono"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Class / Batch
                  </label>
                  <input
                    type="text"
                    value={regClass}
                    onChange={(e) => setRegClass(e.target.value)}
                    placeholder="BE-IV-A"
                    className="w-full rounded-xl border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Institutional Email *
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Mail className="h-4 w-4" />
                  </div>
                  <input
                    type="email"
                    required
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                    placeholder="ananya.roy@exam.edu"
                    className="w-full rounded-xl border border-white/10 bg-slate-950/80 pl-10 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Department
                </label>
                <input
                  type="text"
                  value={regDept}
                  onChange={(e) => setRegDept(e.target.value)}
                  placeholder="Computer Science"
                  className="w-full rounded-xl border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
                />
              </div>

              {regError && (
                <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
                  {regError}
                </div>
              )}

              <button
                type="submit"
                disabled={regLoading}
                className="w-full mt-2 py-3 px-4 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 text-white font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-cyan-950/60 transition-all hover:scale-[1.01]"
              >
                {regLoading ? (
                  <span>Registering...</span>
                ) : (
                  <>
                    <span>Register & Enroll Face</span>
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </form>
          )}

          {/* Invigilator / Staff Link */}
          <div className="pt-2 border-t border-white/5 flex items-center justify-between text-xs text-slate-400">
            <span>Staff or Invigilator?</span>
            <Link
              href="/dashboard"
              className="text-cyan-400 hover:underline font-semibold"
            >
              Surveillance Command Center →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
