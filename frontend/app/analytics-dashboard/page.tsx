'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';

interface AnalyticsData {
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
  success_rate: number;
  average_duration_seconds: number;
  failure_reasons: Record<string, number>;
}

interface CallLog {
  call_id: string;
  participant_name: string;
  channel: string;
  duration_seconds: number;
  exercises_completed: number;
  outcome: 'SUCCESS' | 'FAILED';
  failure_reason: string;
  created_at: string;
}

export default function AnalyticsDashboardPage() {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [recentLogs, setRecentLogs] = useState<CallLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<string>('');

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/analytics');
      const data = await res.json();
      if (data.success) {
        setAnalytics(data.analytics);
        setRecentLogs(data.recent_logs || []);
        setLastUpdated(new Date().toLocaleTimeString('en-IN'));
      }
    } catch (err) {
      console.error('Failed to fetch call analytics:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
    // Auto-refresh every 5 seconds for live demo responsiveness
    const interval = setInterval(fetchAnalytics, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <main className="min-h-screen bg-slate-950 p-6 font-sans text-slate-100 md:p-12">
      <div className="mx-auto max-w-6xl space-y-8">
        {/* Top Header & Navigation */}
        <div className="flex flex-col items-start justify-between gap-4 border-b border-slate-800 pb-6 md:flex-row md:items-center">
          <div>
            <div className="mb-2 flex items-center gap-4">
              <a
                href="/"
                className="text-xs font-semibold text-indigo-400 transition-colors hover:text-indigo-300"
              >
                ← Back to Shiksha AI Session
              </a>
              <span className="text-slate-700">•</span>
              <a
                href="/teacher-dashboard"
                className="text-xs font-semibold text-emerald-400 transition-colors hover:text-emerald-300"
              >
                👩‍🏫 Teacher Dashboard
              </a>
            </div>
            <h1 className="flex items-center gap-3 text-3xl font-extrabold tracking-tight text-white">
              <span>📊 Call Analytics Dashboard</span>
            </h1>
            <p className="mt-1 text-sm text-slate-400">
              Day 8: Real-time call performance, success rates, and session history from SQLite.
            </p>
          </div>

          <div className="flex items-center gap-3">
            {lastUpdated && (
              <span className="font-mono text-xs text-slate-500">
                Live Polling (Updated {lastUpdated})
              </span>
            )}
            <button
              onClick={fetchAnalytics}
              disabled={loading}
              className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-indigo-600/30 transition-all hover:bg-indigo-500 disabled:opacity-50"
            >
              <span>🔄 Refresh Data</span>
            </button>
          </div>
        </div>

        {/* Success Criteria Banner */}
        <div className="flex items-start gap-3 rounded-2xl border border-indigo-500/30 bg-indigo-950/40 p-4 text-xs leading-relaxed text-indigo-200">
          <span className="text-xl">🎯</span>
          <div>
            <strong className="font-bold text-indigo-300">Shiksha AI Success Metric: </strong>A call
            is counted as <span className="font-bold text-emerald-400">SUCCESSFUL</span> when the
            learner completes at least 1 practice activity (word lookup, grammar check, or teacher
            escalation). Calls where the learner disconnects without completing any activity are
            logged as <span className="font-bold text-rose-400">FAILED / INCOMPLETE</span>.
          </div>
        </div>

        {/* 3 Core Required Numbers + Advanced Cards */}
        <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
          <div className="flex flex-col justify-between rounded-xl border border-slate-800 bg-slate-900/80 p-4">
            <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase">
              Total Calls
            </span>
            <span className="mt-2 text-3xl font-extrabold text-white">
              {analytics?.total_calls ?? 0}
            </span>
            <span className="mt-1 text-[10px] text-slate-500">All Web & SIP Sessions</span>
          </div>

          <div className="flex flex-col justify-between rounded-xl border border-emerald-500/30 bg-emerald-950/40 p-4">
            <span className="text-xs font-semibold tracking-wider text-emerald-400 uppercase">
              Successful Calls
            </span>
            <span className="mt-2 text-3xl font-extrabold text-emerald-300">
              {analytics?.successful_calls ?? 0}
            </span>
            <span className="mt-1 text-[10px] text-emerald-400/70">≥1 Exercise Completed</span>
          </div>

          <div className="flex flex-col justify-between rounded-xl border border-rose-500/30 bg-rose-950/40 p-4">
            <span className="text-xs font-semibold tracking-wider text-rose-400 uppercase">
              Failed Calls
            </span>
            <span className="mt-2 text-3xl font-extrabold text-rose-300">
              {analytics?.failed_calls ?? 0}
            </span>
            <span className="mt-1 text-[10px] text-rose-400/70">0 Exercises / Hangup</span>
          </div>

          <div className="flex flex-col justify-between rounded-xl border border-indigo-500/30 bg-indigo-950/40 p-4">
            <span className="text-xs font-semibold tracking-wider text-indigo-300 uppercase">
              Success Rate
            </span>
            <span className="mt-2 text-3xl font-extrabold text-indigo-200">
              {analytics?.success_rate ?? 0}%
            </span>
            <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
              <div
                className="h-full rounded-full bg-indigo-500 transition-all duration-500"
                style={{ width: `${analytics?.success_rate ?? 0}%` }}
              />
            </div>
          </div>

          <div className="col-span-2 flex flex-col justify-between rounded-xl border border-slate-800 bg-slate-900/80 p-4 md:col-span-1">
            <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase">
              Avg Call Duration
            </span>
            <span className="mt-2 text-3xl font-extrabold text-slate-200">
              {analytics?.average_duration_seconds ?? 0}s
            </span>
            <span className="mt-1 text-[10px] text-slate-500">Average Session Length</span>
          </div>
        </div>

        {/* Failure Reason Breakdown */}
        {analytics?.failure_reasons && Object.keys(analytics.failure_reasons).length > 0 && (
          <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
            <h3 className="flex items-center gap-2 text-sm font-bold tracking-wider text-slate-200 uppercase">
              <span>❌ Failure Categories Breakdown</span>
            </h3>
            <div className="space-y-2">
              {Object.entries(analytics.failure_reasons).map(([reason, count]) => {
                const pct = analytics.failed_calls
                  ? Math.round((count / analytics.failed_calls) * 100)
                  : 0;
                return (
                  <div key={reason} className="space-y-1">
                    <div className="flex justify-between text-xs font-medium text-slate-300">
                      <span>{reason}</span>
                      <span className="font-mono text-slate-400">
                        {count} call(s) ({pct}%)
                      </span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
                      <div
                        className="h-full rounded-full bg-rose-500 transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Recent Call Logs Table */}
        <div className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/90 p-6 shadow-xl">
          <div className="flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-lg font-bold text-white">
              <span>📋 Recent Call Sessions</span>
            </h2>
            <span className="font-mono text-xs text-slate-400">
              Showing last {recentLogs.length} sessions
            </span>
          </div>

          {loading && recentLogs.length === 0 ? (
            <div className="animate-pulse py-12 text-center text-sm text-slate-400">
              Fetching call analytics from SQLite database...
            </div>
          ) : recentLogs.length === 0 ? (
            <div className="rounded-xl bg-slate-950/50 py-12 text-center text-sm text-slate-400">
              No call sessions logged yet. Start a Shiksha AI voice session to see live analytics!
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="border-b border-slate-800 bg-slate-950/80 font-semibold tracking-wider text-slate-400 uppercase">
                  <tr>
                    <th className="p-3">Call ID</th>
                    <th className="p-3">Learner Name</th>
                    <th className="p-3">Channel</th>
                    <th className="p-3">Exercises</th>
                    <th className="p-3">Duration</th>
                    <th className="p-3">Outcome</th>
                    <th className="p-3">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-sans">
                  {recentLogs.map((log) => (
                    <tr key={log.call_id} className="transition-colors hover:bg-slate-800/40">
                      <td className="p-3 font-mono font-semibold text-indigo-400">{log.call_id}</td>
                      <td className="p-3 font-medium text-slate-200">{log.participant_name}</td>
                      <td className="p-3">
                        <span className="rounded border border-slate-700 bg-slate-800 px-2 py-0.5 text-[11px] font-medium text-slate-300">
                          {log.channel}
                        </span>
                      </td>
                      <td className="p-3 font-mono text-indigo-300">
                        {log.exercises_completed} activity(ies)
                      </td>
                      <td className="p-3 font-mono">{log.duration_seconds}s</td>
                      <td className="p-3">
                        <span
                          className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase ${
                            log.outcome === 'SUCCESS'
                              ? 'border border-emerald-500/40 bg-emerald-500/20 text-emerald-300'
                              : 'border border-rose-500/40 bg-rose-500/20 text-rose-300'
                          }`}
                        >
                          {log.outcome === 'SUCCESS' ? '✓ SUCCESS' : '✕ FAILED'}
                        </span>
                      </td>
                      <td className="p-3 text-[11px] text-slate-400">
                        {new Date(log.created_at).toLocaleString('en-IN', {
                          timeZone: 'Asia/Kolkata',
                        })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
