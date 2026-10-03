import { StudentProfile, StudentFaceStatus, StudentLoginResult, FaceEnrollmentResult } from '@/types';

const FASTAPI_URL = process.env.NEXT_PUBLIC_FASTAPI_URL || 'http://localhost:8000';
const API_KEY = process.env.NEXT_PUBLIC_FASTAPI_KEY || 'dev-proctor-secret-key';

export const studentApiService = {
  async registerStudent(data: {
    name: string;
    roll_number: string;
    email: string;
    class_name?: string;
    department?: string;
  }): Promise<StudentProfile> {
    const res = await fetch(`${FASTAPI_URL}/api/v1/students/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
      },
      body: JSON.stringify(data),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Registration failed' }));
      throw new Error(err.detail || 'Failed to register student');
    }

    return await res.json();
  },

  async loginStudent(identifier: string): Promise<StudentLoginResult> {
    const res = await fetch(`${FASTAPI_URL}/api/v1/students/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
      },
      body: JSON.stringify({ identifier }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Authentication failed' }));
      throw new Error(err.detail || 'Student not found');
    }

    return await res.json();
  },

  async getStudent(studentId: string): Promise<StudentProfile | null> {
    try {
      const res = await fetch(`${FASTAPI_URL}/api/v1/students/${studentId}`, {
        headers: { 'X-API-Key': API_KEY },
      });
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  },

  async getFaceStatus(studentId: string): Promise<StudentFaceStatus | null> {
    try {
      const res = await fetch(`${FASTAPI_URL}/api/v1/students/${studentId}/face/status`, {
        headers: { 'X-API-Key': API_KEY },
      });
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  },

  async enrollFaceBase64(studentId: string, imageBase64: string): Promise<FaceEnrollmentResult> {
    const res = await fetch(`${FASTAPI_URL}/api/v1/students/${studentId}/face/enroll`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
      },
      body: JSON.stringify({
        student_id: studentId,
        image_base64: imageBase64,
        notes: 'Enrolled via Web Portal',
      }),
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || 'Biometric face enrollment failed');
    }
    return data;
  },

  async enrollFaceUpload(studentId: string, file: File, notes?: string): Promise<FaceEnrollmentResult> {
    const formData = new FormData();
    formData.append('file', file);
    if (notes) formData.append('notes', notes);

    const res = await fetch(`${FASTAPI_URL}/api/v1/students/${studentId}/face/enroll/upload`, {
      method: 'POST',
      headers: {
        'X-API-Key': API_KEY,
      },
      body: formData,
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || 'Biometric photo upload enrollment failed');
    }
    return data;
  },
};
