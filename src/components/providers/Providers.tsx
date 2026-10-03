'use client';

import React from 'react';
import { StudentProvider } from '@/context/StudentContext';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <StudentProvider>
      {children}
    </StudentProvider>
  );
}
