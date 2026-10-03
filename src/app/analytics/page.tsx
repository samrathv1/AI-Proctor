'use client';

import React from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { StatCard } from '@/components/ui/StatCard';
import { ChartCard } from '@/components/ui/ChartCard';
import { 
  BarChart3, 
  Cpu, 
  Gauge, 
  Smartphone, 
  Eye, 
  Volume2, 
  Zap, 
  Activity, 
  Layers,
  Sparkles,
  TrendingUp
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  LineChart, 
  Line, 
  RadarChart, 
  PolarGrid, 
  PolarAngleAxis, 
  PolarRadiusAxis, 
  Radar 
} from 'recharts';

export default function AnalyticsPage() {
  // Detection Statistics from user prompt:
  // Phone Detection: 45%
  // Head Movement: 35%
  // Noise: 20%
  const detectionStatsData = [
    { category: 'Phone Detection', percentage: 45, fill: '#ef4444' },
    { category: 'Head Movement', percentage: 35, fill: '#f59e0b' },
    { category: 'Noise / Audio', percentage: 20, fill: '#06b6d4' },
  ];

  // AI Performance metrics from prompt:
  // Frames Analysed: 25000
  // Detection Accuracy: 92%

  const hourlyInferenceData = [
    { time: '10:00', framesProcessed: 4100, latency: 17, accuracy: 93 },
    { time: '10:15', framesProcessed: 4250, latency: 18, accuracy: 92 },
    { time: '10:30', framesProcessed: 4320, latency: 19, accuracy: 91 },
    { time: '10:45', framesProcessed: 4200, latency: 18, accuracy: 94 },
    { time: '11:00', framesProcessed: 4150, latency: 16, accuracy: 92 },
    { time: '11:15', framesProcessed: 3980, latency: 17, accuracy: 93 },
  ];

  const modelBenchmarkData = [
    { subject: 'Recall', score: 94, fullMark: 100 },
    { subject: 'Precision', score: 92, fullMark: 100 },
    { subject: 'Speed (FPS)', score: 90, fullMark: 100 },
    { subject: 'Low Light', score: 86, fullMark: 100 },
    { subject: 'Multi-Face', score: 95, fullMark: 100 },
    { subject: 'Audio Filter', score: 88, fullMark: 100 },
  ];

  return (
    <AppLayout breadcrumbs={[{ label: 'Dashboard', href: '/dashboard' }, { label: 'Analytics' }]}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-extrabold text-white tracking-tight sm:text-3xl">
                Advanced AI Vision Analytics
              </h1>
              <span className="rounded-full bg-cyan-500/10 border border-cyan-500/30 px-2.5 py-0.5 text-xs font-mono font-semibold text-cyan-400">
                MODEL TELEMETRY
              </span>
            </div>
            <p className="mt-1 text-xs sm:text-sm text-slate-400">
              In-depth performance evaluation across YOLOv8 inference latency, MediaPipe pose mesh, and anomaly distributions.
            </p>
          </div>
        </div>

        {/* AI PERFORMANCE METRICS (Requested: Frames Analysed: 25000, Detection Accuracy: 92%) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Frames Analysed"
            value="25,000"
            subtitle="Processed Across All Streams"
            icon={Layers}
            accentColor="cyan"
            badge="Real-time Stream"
            trend={{ value: '30 FPS/node', isPositive: true }}
          />

          <StatCard
            title="Detection Accuracy"
            value="92%"
            subtitle="Verified Precision Rate"
            icon={Gauge}
            accentColor="emerald"
            badge="YOLOv8 + Ensemble"
            trend={{ value: '+1.4% vs v1', isPositive: true }}
          />

          <StatCard
            title="Avg Model Latency"
            value="18ms"
            subtitle="Per Frame Inference Speed"
            icon={Zap}
            accentColor="violet"
            badge="GPU Accelerated"
            trend={{ value: 'Under 33ms target', isPositive: true }}
          />

          <StatCard
            title="False Positive Rate"
            value="3.2%"
            subtitle="Invigilator Dismissed"
            icon={Activity}
            accentColor="amber"
            badge="Threshold Filtered"
            trend={{ value: '-0.8% decrease', isPositive: true }}
          />
        </div>

        {/* DETECTION STATISTICS (Requested: Phone 45%, Head Movement 35%, Noise 20%) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left: Detection Statistics Breakdown Bar Chart - 6 Cols */}
          <div className="lg:col-span-6">
            <ChartCard
              title="Detection Statistics Distribution"
              subtitle="Relative frequency of anomalous violation triggers"
            >
              <div className="space-y-4 pt-2">
                {/* Visual Progress Cards */}
                <div className="space-y-3">
                  {/* Phone Detection: 45% */}
                  <div className="rounded-xl bg-slate-950/60 p-3.5 border border-white/5 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2 font-semibold text-white">
                        <Smartphone className="h-4 w-4 text-rose-400" />
                        <span>Phone Detection</span>
                      </div>
                      <span className="font-mono text-base font-extrabold text-rose-400">45%</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                      <div className="h-full rounded-full bg-rose-500" style={{ width: '45%' }} />
                    </div>
                  </div>

                  {/* Head Movement: 35% */}
                  <div className="rounded-xl bg-slate-950/60 p-3.5 border border-white/5 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2 font-semibold text-white">
                        <Eye className="h-4 w-4 text-amber-400" />
                        <span>Head Movement & Yaw Angle</span>
                      </div>
                      <span className="font-mono text-base font-extrabold text-amber-400">35%</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                      <div className="h-full rounded-full bg-amber-500" style={{ width: '35%' }} />
                    </div>
                  </div>

                  {/* Noise: 20% */}
                  <div className="rounded-xl bg-slate-950/60 p-3.5 border border-white/5 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2 font-semibold text-white">
                        <Volume2 className="h-4 w-4 text-cyan-400" />
                        <span>Auditory Noise / Whispering</span>
                      </div>
                      <span className="font-mono text-base font-extrabold text-cyan-400">20%</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                      <div className="h-full rounded-full bg-cyan-500" style={{ width: '20%' }} />
                    </div>
                  </div>
                </div>

                {/* Recharts Bar representation */}
                <div className="h-48 w-full pt-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={detectionStatsData} layout="vertical" margin={{ left: 20, right: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                      <XAxis type="number" stroke="#64748b" fontSize={11} domain={[0, 50]} unit="%" />
                      <YAxis type="category" dataKey="category" stroke="#94a3b8" fontSize={11} width={110} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#090d16',
                          borderColor: 'rgba(255,255,255,0.1)',
                          borderRadius: '0.75rem',
                          color: '#fff',
                        }}
                      />
                      <Bar dataKey="percentage" name="Trigger Percentage" radius={[0, 6, 6, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </ChartCard>
          </div>

          {/* Right: Model Robustness Radar & Accuracy Timeline - 6 Cols */}
          <div className="lg:col-span-6 space-y-6">
            <ChartCard
              title="AI Vision Model Benchmarks"
              subtitle="Ensemble verification radar across multiple surveillance criteria"
            >
              <div className="h-72 w-full flex items-center justify-center">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={modelBenchmarkData} cx="50%" cy="50%" outerRadius={90}>
                    <PolarGrid stroke="rgba(255,255,255,0.1)" />
                    <PolarAngleAxis dataKey="subject" stroke="#94a3b8" fontSize={11} />
                    <PolarRadiusAxis angle={30} domain={[0, 100]} stroke="#475569" fontSize={10} />
                    <Radar
                      name="Model Score"
                      dataKey="score"
                      stroke="#06b6d4"
                      fill="#06b6d4"
                      fillOpacity={0.4}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#090d16',
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderRadius: '0.75rem',
                        color: '#fff',
                      }}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>
          </div>
        </div>

        {/* Frames Processed & Inference Speed Timeline */}
        <ChartCard
          title="Session Inference Telemetry Over Time"
          subtitle="Processed frames and pipeline latency per 15-minute checkpoint"
        >
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={hourlyInferenceData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={11} />
                <YAxis stroke="#64748b" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#090d16',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderRadius: '0.75rem',
                    color: '#fff',
                  }}
                />
                <Legend
                  verticalAlign="top"
                  align="right"
                  height={36}
                  formatter={(val) => <span className="text-xs text-slate-300 ml-1">{val}</span>}
                />
                <Line
                  type="monotone"
                  dataKey="framesProcessed"
                  name="Frames Processed"
                  stroke="#10b981"
                  strokeWidth={2.5}
                  dot={{ r: 4, fill: '#10b981' }}
                />
                <Line
                  type="monotone"
                  dataKey="latency"
                  name="Inference Latency (ms)"
                  stroke="#f43f5e"
                  strokeWidth={2}
                  dot={{ r: 4, fill: '#f43f5e' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
      </div>
    </AppLayout>
  );
}
