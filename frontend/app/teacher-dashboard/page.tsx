'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';

interface EscalationTicket {
  reference_id: string;
  learner_name: string;
  reason: string;
  summary: string;
  urgency: 'low' | 'medium' | 'high' | 'emergency';
  status: 'OPEN' | 'RESOLVED';
  created_at: string;
}

export default function TeacherDashboardPage() {
  const [tickets, setTickets] = useState<EscalationTicket[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'ALL' | 'OPEN' | 'RESOLVED' | 'HIGH'>('ALL');
  const [updatingRef, setUpdatingRef] = useState<string | null>(null);

  const fetchTickets = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/escalations');
      const data = await res.json();
      if (data.success) {
        setTickets(data.escalations || []);
      }
    } catch (err) {
      console.error('Failed to fetch escalation tickets:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
  }, []);

  const markResolved = async (refId: string) => {
    try {
      setUpdatingRef(refId);
      const res = await fetch('/api/escalations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reference_id: refId, status: 'RESOLVED' }),
      });
      const data = await res.json();
      if (data.success) {
        setTickets((prev) =>
          prev.map((t) => (t.reference_id === refId ? { ...t, status: 'RESOLVED' } : t))
        );
      }
    } catch (err) {
      console.error('Failed to resolve ticket:', err);
    } finally {
      setUpdatingRef(null);
    }
  };

  const filteredTickets = tickets.filter((t) => {
    if (filter === 'OPEN') return t.status === 'OPEN';
    if (filter === 'RESOLVED') return t.status === 'RESOLVED';
    if (filter === 'HIGH') return t.urgency === 'high' || t.urgency === 'emergency';
    return true;
  });

  const openCount = tickets.filter((t) => t.status === 'OPEN').length;
  const resolvedCount = tickets.filter((t) => t.status === 'RESOLVED').length;
  const highCount = tickets.filter((t) => t.urgency === 'high' || t.urgency === 'emergency').length;

  return (
    <main className="min-h-screen bg-slate-950 p-6 font-sans text-slate-100 md:p-12">
      <div className="mx-auto max-w-6xl space-y-8">
        {/* Header Bar */}
        <div className="flex flex-col items-start justify-between gap-4 border-b border-slate-800 pb-6 md:flex-row md:items-center">
          <div>
            <a
              href="/"
              className="mb-2 inline-flex items-center gap-2 text-xs font-semibold text-indigo-400 transition-colors hover:text-indigo-300"
            >
              ← Back to Shiksha AI Session
            </a>
            <h1 className="flex items-center gap-3 text-3xl font-extrabold tracking-tight text-white">
              <span>👩‍🏫 Human Teacher Escalation Dashboard</span>
            </h1>
            <p className="mt-1 text-sm text-slate-400">
              Day 7: Review learner escalation tickets, practice notes, and human support requests.
            </p>
          </div>
          <button
            onClick={fetchTickets}
            disabled={loading}
            className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-indigo-600/30 transition-all hover:bg-indigo-500 disabled:opacity-50"
          >
            <span>🔄 Refresh Requests</span>
          </button>
        </div>

        {/* Metrics Overview Cards */}
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <div className="flex flex-col rounded-xl border border-slate-800 bg-slate-900/80 p-4">
            <span className="text-xs font-medium text-slate-400">Total Tickets</span>
            <span className="mt-1 text-2xl font-bold text-slate-100">{tickets.length}</span>
          </div>
          <div className="flex flex-col rounded-xl border border-amber-500/30 bg-amber-950/40 p-4">
            <span className="text-xs font-medium text-amber-400">Open Requests</span>
            <span className="mt-1 text-2xl font-bold text-amber-300">{openCount}</span>
          </div>
          <div className="flex flex-col rounded-xl border border-rose-500/30 bg-rose-950/40 p-4">
            <span className="text-xs font-medium text-rose-400">High Urgency</span>
            <span className="mt-1 text-2xl font-bold text-rose-300">{highCount}</span>
          </div>
          <div className="flex flex-col rounded-xl border border-emerald-500/30 bg-emerald-950/40 p-4">
            <span className="text-xs font-medium text-emerald-400">Resolved</span>
            <span className="mt-1 text-2xl font-bold text-emerald-300">{resolvedCount}</span>
          </div>
        </div>

        {/* Filter Bar */}
        <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
          <button
            onClick={() => setFilter('ALL')}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
              filter === 'ALL'
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200'
            }`}
          >
            All ({tickets.length})
          </button>
          <button
            onClick={() => setFilter('OPEN')}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
              filter === 'OPEN'
                ? 'bg-amber-600 text-white'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200'
            }`}
          >
            Open ({openCount})
          </button>
          <button
            onClick={() => setFilter('HIGH')}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
              filter === 'HIGH'
                ? 'bg-rose-600 text-white'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200'
            }`}
          >
            High Urgency ({highCount})
          </button>
          <button
            onClick={() => setFilter('RESOLVED')}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
              filter === 'RESOLVED'
                ? 'bg-emerald-600 text-white'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200'
            }`}
          >
            Resolved ({resolvedCount})
          </button>
        </div>

        {/* Ticket List */}
        {loading ? (
          <div className="animate-pulse py-16 text-center text-sm text-slate-400">
            Loading escalation tickets from SQLite database...
          </div>
        ) : filteredTickets.length === 0 ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-8 py-16 text-center">
            <span className="text-4xl">🎉</span>
            <h3 className="mt-3 text-lg font-bold text-slate-200">No tickets found</h3>
            <p className="mx-auto mt-1 max-w-sm text-xs text-slate-400">
              No human teacher escalation requests match the selected filter. Test human help in a
              Shiksha AI voice session!
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {filteredTickets.map((ticket) => (
              <div
                key={ticket.reference_id}
                className="flex flex-col justify-between space-y-4 rounded-2xl border border-slate-800 bg-slate-900/90 p-6 shadow-xl transition-all hover:border-slate-700"
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="rounded-md border border-indigo-500/30 bg-indigo-950/80 px-2.5 py-1 font-mono text-xs font-bold text-indigo-400">
                      {ticket.reference_id}
                    </span>
                    <div className="flex items-center gap-2">
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase ${
                          ticket.urgency === 'high' || ticket.urgency === 'emergency'
                            ? 'border border-rose-500/40 bg-rose-500/20 text-rose-300'
                            : 'border border-amber-500/40 bg-amber-500/20 text-amber-300'
                        }`}
                      >
                        {ticket.urgency} Urgency
                      </span>
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase ${
                          ticket.status === 'OPEN'
                            ? 'bg-amber-500/20 text-amber-300'
                            : 'bg-emerald-500/20 text-emerald-300'
                        }`}
                      >
                        {ticket.status}
                      </span>
                    </div>
                  </div>

                  <div>
                    <h3 className="flex items-center gap-2 text-base font-bold text-slate-100">
                      <span>👤 {ticket.learner_name}</span>
                    </h3>
                    <p className="mt-0.5 text-xs font-semibold text-indigo-300">
                      Reason: {ticket.reason}
                    </p>
                  </div>

                  <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-3 text-xs leading-relaxed text-slate-300">
                    {ticket.summary}
                  </div>
                </div>

                <div className="flex items-center justify-between border-t border-slate-800 pt-3 text-[11px] text-slate-500">
                  <span>
                    Created:{' '}
                    {new Date(ticket.created_at).toLocaleString('en-IN', {
                      timeZone: 'Asia/Kolkata',
                    })}
                  </span>
                  {ticket.status === 'OPEN' && (
                    <button
                      onClick={() => markResolved(ticket.reference_id)}
                      disabled={updatingRef === ticket.reference_id}
                      className="rounded-lg bg-emerald-600 px-3 py-1.5 font-semibold text-white shadow transition-colors hover:bg-emerald-500 disabled:opacity-50"
                    >
                      {updatingRef === ticket.reference_id ? 'Resolving...' : '✓ Mark Resolved'}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
