'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { StudentProfile, StudentFaceStatus } from '@/types';
import { studentApiService } from '@/services/student';

interface StudentContextType {
  student: StudentProfile | null;
  faceStatus: StudentFaceStatus | null;
  isFaceEnrolled: boolean;
  isLoading: boolean;
  login: (identifier: string) => Promise<{ success: boolean; faceEnrolled: boolean; error?: string }>;
  register: (data: {
    name: string;
    roll_number: string;
    email: string;
    class_name?: string;
    department?: string;
  }) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
  refreshFaceStatus: () => Promise<void>;
  setStudentDirectly: (student: StudentProfile) => void;
}

const StudentContext = createContext<StudentContextType | undefined>(undefined);

export function StudentProvider({ children }: { children: ReactNode }) {
  const [student, setStudent] = useState<StudentProfile | null>(null);
  const [faceStatus, setFaceStatus] = useState<StudentFaceStatus | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Initialize from session on mount and verify with backend
  useEffect(() => {
    async function initStudent() {
      try {
        const savedId = typeof window !== 'undefined' ? sessionStorage.getItem('ai_proctor_student_id') : null;
        if (savedId) {
          const profile = await studentApiService.getStudent(savedId);
          if (profile) {
            setStudent(profile);
            const status = await studentApiService.getFaceStatus(profile.id);
            setFaceStatus(status);
          }
        } else {
          // Default to default enrolled student Dev Sharma if none stored
          const dev = await studentApiService.getStudent('s-01');
          if (dev) {
            setStudent(dev);
            const status = await studentApiService.getFaceStatus(dev.id);
            setFaceStatus(status);
          }
        }
      } catch (err) {
        console.warn('Student profile initialization advisory:', err);
      } finally {
        setIsLoading(false);
      }
    }
    initStudent();
  }, []);

  const login = async (identifier: string) => {
    setIsLoading(true);
    try {
      const result = await studentApiService.loginStudent(identifier);
      if (result.success && result.student) {
        setStudent(result.student);
        if (typeof window !== 'undefined') {
          sessionStorage.setItem('ai_proctor_student_id', result.student.id);
        }
        const status = await studentApiService.getFaceStatus(result.student.id);
        setFaceStatus(status);
        return { success: true, faceEnrolled: result.face_enrolled };
      }
      return { success: false, faceEnrolled: false, error: result.message || 'Login failed' };
    } catch (err: any) {
      return { success: false, faceEnrolled: false, error: err.message || 'Authentication error' };
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: {
    name: string;
    roll_number: string;
    email: string;
    class_name?: string;
    department?: string;
  }) => {
    setIsLoading(true);
    try {
      const created = await studentApiService.registerStudent(data);
      setStudent(created);
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('ai_proctor_student_id', created.id);
      }
      const status = await studentApiService.getFaceStatus(created.id);
      setFaceStatus(status);
      return { success: true };
    } catch (err: any) {
      return { success: false, error: err.message || 'Registration failed' };
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setStudent(null);
    setFaceStatus(null);
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('ai_proctor_student_id');
    }
  };

  const refreshFaceStatus = async () => {
    if (!student) return;
    try {
      const status = await studentApiService.getFaceStatus(student.id);
      setFaceStatus(status);
    } catch (err) {
      console.warn('Failed to refresh face status:', err);
    }
  };

  const setStudentDirectly = (s: StudentProfile) => {
    setStudent(s);
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('ai_proctor_student_id', s.id);
    }
    studentApiService.getFaceStatus(s.id).then(setFaceStatus).catch(() => {});
  };

  const isFaceEnrolled = faceStatus?.enrollment_status === 'ENROLLED' && faceStatus.has_embedding;

  return (
    <StudentContext.Provider
      value={{
        student,
        faceStatus,
        isFaceEnrolled,
        isLoading,
        login,
        register,
        logout,
        refreshFaceStatus,
        setStudentDirectly,
      }}
    >
      {children}
    </StudentContext.Provider>
  );
}

export function useStudentAuth() {
  const context = useContext(StudentContext);
  if (!context) {
    throw new Error('useStudentAuth must be used within a StudentProvider');
  }
  return context;
}
