'use client';

import React from 'react';
import { Camera } from '@/types';
import { StatusBadge } from './StatusBadge';
import { Video, Activity, Wifi, Shield, RefreshCw, PowerOff } from 'lucide-react';
import { cn } from '@/lib/utils';

interface CameraCardProps {
  camera: Camera;
  onSelect?: (camera: Camera) => void;
  onDisconnect?: (cameraId: string) => void;
  isSelected?: boolean;
  className?: string;
}

export function CameraCard({
  camera,
  onSelect,
  onDisconnect,
  isSelected,
  className,
}: CameraCardProps) {
  const isOnline = camera.status === 'ONLINE';

  return (
    <div
      onClick={() => onSelect && onSelect(camera)}
      className={cn(
        'group relative overflow-hidden rounded-2xl border bg-slate-900/70 p-4 backdrop-blur-md transition-all duration-300 cursor-pointer',
        isSelected
          ? 'border-cyan-500 shadow-lg shadow-cyan-950/40 ring-1 ring-cyan-500/50'
          : 'border-white/5 hover:border-white/20 hover:bg-slate-900/90',
        className
      )}
    >
      {/* Top row: Name & Status */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className={cn(
            'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border',
            isOnline ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30' : 'bg-slate-800 text-slate-500 border-slate-700'
          )}>
            <Video className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <h4 className="font-semibold text-white text-sm truncate">
              {camera.name}
            </h4>
            <p className="text-[11px] text-slate-400 truncate">{camera.location}</p>
          </div>
        </div>

        <StatusBadge status={camera.status} size="sm" />
      </div>

      {/* Camera Live Preview Simulated Box */}
      <div className="relative mt-3 h-28 w-full overflow-hidden rounded-xl bg-slate-950 border border-slate-800/80 flex items-center justify-center">
        {isOnline ? (
          <>
            <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:12px_12px] opacity-40" />
            <div className="relative z-10 flex flex-col items-center text-center p-2">
              <div className="flex items-center gap-1.5 rounded-full bg-slate-900/80 px-2.5 py-0.5 border border-slate-700 text-[10px] text-emerald-400 font-mono">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                LIVE STREAM FEED
              </div>
              <span className="mt-2 text-[11px] font-mono text-slate-400">
                {camera.resolution} @ {camera.fps} FPS
              </span>
            </div>
            {/* Live Timestamp Overlay */}
            <div className="absolute bottom-1.5 left-2 text-[9px] font-mono text-slate-400 bg-black/60 px-1.5 py-0.5 rounded">
              CAM-ID: {camera.id.toUpperCase()}
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center gap-1 text-slate-500">
            <PowerOff className="h-6 w-6" />
            <span className="text-xs font-mono">SIGNAL OFFLINE</span>
          </div>
        )}
      </div>

      {/* Metrics Row */}
      <div className="mt-3 grid grid-cols-3 gap-2 border-t border-white/5 pt-3 text-center">
        <div className="rounded-lg bg-slate-950/40 p-1.5 border border-white/5">
          <div className="text-[10px] uppercase tracking-wider text-slate-400 font-medium">FPS</div>
          <div className="text-xs font-bold text-white font-mono mt-0.5">{camera.fps}</div>
        </div>
        <div className="rounded-lg bg-slate-950/40 p-1.5 border border-white/5">
          <div className="text-[10px] uppercase tracking-wider text-slate-400 font-medium">Resolution</div>
          <div className="text-xs font-bold text-cyan-400 font-mono mt-0.5">{camera.resolution.split(' ')[0]}</div>
        </div>
        <div className="rounded-lg bg-slate-950/40 p-1.5 border border-white/5">
          <div className="text-[10px] uppercase tracking-wider text-slate-400 font-medium">Latency</div>
          <div className="text-xs font-bold text-emerald-400 font-mono mt-0.5">{camera.latencyMs}ms</div>
        </div>
      </div>

      {/* Footer Details */}
      <div className="mt-3 flex items-center justify-between text-[11px] text-slate-400">
        <span className="font-mono">Bitrate: {camera.bitrate}</span>
        {onDisconnect && isOnline && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDisconnect(camera.id);
            }}
            className="text-slate-400 hover:text-rose-400 transition-colors"
          >
            Disconnect
          </button>
        )}
      </div>
    </div>
  );
}
