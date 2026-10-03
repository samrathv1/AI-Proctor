'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  GraduationCap, 
  Camera, 
  Video, 
  BellRing, 
  FileText, 
  BarChart3, 
  Cpu, 
  Settings, 
  ChevronLeft, 
  ChevronRight,
  Shield,
  ShieldCheck,
  Radio,
  Wifi,
  LogOut
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { mockCurrentUser } from '@/services/auth';

interface SidebarProps {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  isMobileOpen: boolean;
  onCloseMobile: () => void;
}

const menuItems = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, badge: 'Live' },
  { label: 'Exams', href: '/exams', icon: GraduationCap },
  { label: 'Cameras', href: '/cameras', icon: Camera, badge: '3' },
  { label: 'Live Monitoring', href: '/monitoring', icon: Video, alertPulse: true },
  { label: 'Face Enrollment', href: '/enrollment', icon: ShieldCheck, badge: 'Biometric' },
  { label: 'Alerts', href: '/alerts', icon: BellRing, badge: '8', alertBadge: true },
  { label: 'Reports', href: '/reports', icon: FileText },
  { label: 'Analytics', href: '/analytics', icon: BarChart3 },
  { label: 'IoT Device', href: '/iot', icon: Cpu, badge: 'ESP32' },
  { label: 'Settings', href: '/settings', icon: Settings },
];

export function Sidebar({
  isCollapsed,
  onToggleCollapse,
  isMobileOpen,
  onCloseMobile,
}: SidebarProps) {
  const pathname = usePathname();

  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 z-40 bg-black/80 backdrop-blur-sm lg:hidden"
        />
      )}

      {/* Main Sidebar Shell */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex flex-col border-r border-white/5 bg-[#0a0e18]/95 backdrop-blur-2xl transition-all duration-300 lg:static',
          isCollapsed ? 'w-20' : 'w-64',
          isMobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
      >
        {/* Brand Header */}
        <div className="flex h-16 items-center justify-between px-4 border-b border-white/5">
          <Link
            href="/dashboard"
            className="flex items-center gap-3 overflow-hidden group"
          >
            <div className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-600 via-cyan-500 to-emerald-400 p-0.5 shadow-lg shadow-cyan-500/25">
              <div className="flex h-full w-full items-center justify-center rounded-[10px] bg-slate-950">
                <Shield className="h-5 w-5 text-cyan-400 group-hover:scale-110 transition-transform" />
              </div>
            </div>

            {!isCollapsed && (
              <div className="flex flex-col min-w-0">
                <span className="font-extrabold text-base tracking-tight bg-gradient-to-r from-white via-slate-100 to-cyan-300 bg-clip-text text-transparent">
                  AI-PROCTOR
                </span>
                <span className="text-[10px] font-mono tracking-widest uppercase text-cyan-400 font-semibold">
                  SURVEILLANCE AI
                </span>
              </div>
            )}
          </Link>

          {/* Desktop Collapse Toggle */}
          <button
            onClick={onToggleCollapse}
            className="hidden lg:flex h-7 w-7 items-center justify-center rounded-lg border border-white/5 bg-slate-900/60 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
          >
            {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </button>
        </div>

        {/* System Status Indicator Pill */}
        <div className={cn('px-3 pt-3 pb-1', isCollapsed && 'flex justify-center')}>
          {!isCollapsed ? (
            <div className="flex items-center justify-between rounded-xl bg-slate-950/60 p-2.5 border border-white/5 text-xs">
              <div className="flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
                </span>
                <span className="font-mono text-[11px] text-slate-300 font-medium">
                  ENGINE ONLINE
                </span>
              </div>
              <span className="font-mono text-[10px] text-cyan-400 bg-cyan-950/50 px-1.5 py-0.5 rounded border border-cyan-800/40">
                92% ACC
              </span>
            </div>
          ) : (
            <div
              title="System Online (92% Accuracy)"
              className="flex h-8 w-8 items-center justify-center rounded-xl bg-slate-950/80 border border-emerald-500/30 text-emerald-400 cursor-pointer"
            >
              <Radio className="h-4 w-4 animate-pulse" />
            </div>
          )}
        </div>

        {/* Navigation Menu Links */}
        <nav className="flex-1 space-y-1 px-3 py-3 overflow-y-auto">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname?.startsWith(item.href));

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onCloseMobile}
                className={cn(
                  'group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-xs font-semibold transition-all duration-200',
                  isActive
                    ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 shadow-md shadow-cyan-950/40'
                    : 'text-slate-400 hover:bg-slate-900/60 hover:text-slate-200 border border-transparent'
                )}
                title={isCollapsed ? item.label : undefined}
              >
                {/* Active Indicator Bar */}
                {isActive && (
                  <span className="absolute left-0 top-2 bottom-2 w-1 rounded-r-full bg-cyan-400 shadow-[0_0_8px_#22d3ee]" />
                )}

                <Icon
                  className={cn(
                    'h-4 w-4 shrink-0 transition-colors',
                    isActive ? 'text-cyan-400' : 'text-slate-400 group-hover:text-slate-200',
                    item.alertPulse && 'text-rose-400 animate-pulse'
                  )}
                />

                {!isCollapsed && (
                  <span className="truncate flex-1 tracking-wide">
                    {item.label}
                  </span>
                )}

                {!isCollapsed && item.badge && (
                  <span
                    className={cn(
                      'ml-auto rounded-full px-2 py-0.5 text-[10px] font-mono font-bold uppercase',
                      item.alertBadge
                        ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
                        : 'bg-slate-800 text-slate-300 border border-slate-700'
                    )}
                  >
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* User Profile Section */}
        <div className="border-t border-white/5 p-3">
          <div
            className={cn(
              'flex items-center gap-3 rounded-xl bg-slate-950/40 p-2.5 border border-white/5',
              isCollapsed && 'justify-center p-2'
            )}
          >
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-tr from-cyan-600 to-indigo-600 font-bold text-xs text-white shadow-sm">
              {mockCurrentUser.avatar}
            </div>

            {!isCollapsed && (
              <div className="flex flex-col min-w-0 flex-1">
                <span className="text-xs font-semibold text-white truncate">
                  {mockCurrentUser.name}
                </span>
                <span className="text-[10px] text-slate-400 truncate">
                  Chief Invigilator
                </span>
              </div>
            )}
          </div>
        </div>
      </aside>
    </>
  );
}
