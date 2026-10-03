import { supabase, isSupabaseConfigured } from '@/lib/supabase/client';

export interface User {
  id: string;
  name: string;
  email: string;
  role: 'ADMIN' | 'INVIGILATOR' | 'CHIEF_INVIGILATOR' | 'PROCTOR';
  avatar: string;
  department: string;
}

export const mockCurrentUser: User = {
  id: 'usr-001',
  name: 'Dr. Robert Vance',
  email: 'robert.vance@engineering.edu',
  role: 'CHIEF_INVIGILATOR',
  avatar: 'RV',
  department: 'Department of Computer Science & AI',
};

export const authService = {
  async getCurrentUser(): Promise<User> {
    if (isSupabaseConfigured()) {
      try {
        const { data: { user } } = await supabase.auth.getUser();
        if (user) {
          const { data: profile } = await supabase
            .from('profiles')
            .select('*')
            .eq('id', user.id)
            .single();

          if (profile) {
            return {
              id: user.id,
              name: profile.full_name,
              email: user.email || '',
              role: profile.role,
              avatar: profile.avatar_initials || 'IP',
              department: profile.department || 'Examination Directorate',
            };
          }
        }
      } catch (err) {
        console.warn('Supabase auth check failed, using session fallback:', err);
      }
    }
    return mockCurrentUser;
  },

  async login(email: string, password?: string): Promise<{ success: boolean; user: User; error?: string }> {
    if (isSupabaseConfigured() && password) {
      try {
        const { data, error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (error) throw error;
        if (data.user) {
          const user = await this.getCurrentUser();
          return { success: true, user };
        }
      } catch (err: any) {
        return { success: false, user: mockCurrentUser, error: err.message };
      }
    }
    // Fallback for demo session
    await new Promise((r) => setTimeout(r, 200));
    return { success: true, user: { ...mockCurrentUser, email } };
  },

  async logout(): Promise<{ success: boolean }> {
    if (isSupabaseConfigured()) {
      try {
        await supabase.auth.signOut();
      } catch (err) {
        console.warn('Supabase signout failed:', err);
      }
    }
    return { success: true };
  },
};
