'use client';

import React, { useState, useRef } from 'react';
import {
  PhoneCall,
  Clock,
  CheckCircle,
  User,
  X,
  Question,
  ArrowSquareOut,
} from '@phosphor-icons/react';
import { Button } from '@/components/ui/button';

interface ScheduleCallModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ScheduleCallModal({ isOpen, onClose }: ScheduleCallModalProps) {
  const [participantName, setParticipantName] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [scheduleOption, setScheduleOption] = useState<'10s' | '1m' | '5m' | 'custom'>('10s');
  const [customDateTime, setCustomDateTime] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successResult, setSuccessResult] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [showSipInfo, setShowSipInfo] = useState(false);
  const [isExitingSipInfo, setIsExitingSipInfo] = useState(false);
  const [isModalClosing, setIsModalClosing] = useState(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  if (!isOpen) return null;

  const handleCloseModal = () => {
    setIsModalClosing(true);
    setTimeout(() => {
      setIsModalClosing(false);
      onClose();
    }, 200);
  };

  const startAutoCloseTimer = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setIsExitingSipInfo(true);
      setTimeout(() => {
        setShowSipInfo(false);
        setIsExitingSipInfo(false);
      }, 200);
    }, 500);
  };

  const handleSipInfoClick = () => {
    setIsExitingSipInfo(false);
    setShowSipInfo(true);
    startAutoCloseTimer();
  };

  const handleMouseEnter = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setIsExitingSipInfo(false);
    setShowSipInfo(true);
  };

  const handleMouseLeave = () => {
    startAutoCloseTimer();
  };

  const handleSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMsg(null);

    let targetDate = new Date();
    if (scheduleOption === '10s') {
      targetDate = new Date(Date.now() + 10 * 1000);
    } else if (scheduleOption === '1m') {
      targetDate = new Date(Date.now() + 60 * 1000);
    } else if (scheduleOption === '5m') {
      targetDate = new Date(Date.now() + 5 * 60 * 1000);
    } else if (scheduleOption === 'custom' && customDateTime) {
      targetDate = new Date(customDateTime);
    }

    const scheduledAtISO = targetDate.toISOString();

    try {
      const res = await fetch('/api/schedule-call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          participantName: participantName.trim(),
          phoneNumber: phoneNumber.trim(),
          scheduledAtISO,
        }),
      });

      const data = await res.json();
      if (data.success) {
        setSuccessResult({
          name: participantName.trim(),
          phone: phoneNumber.trim(),
          scheduledAt: targetDate.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
          }),
        });
      } else {
        setErrorMsg(data.error || 'Failed to schedule call');
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Network error occurred');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-md transition-all duration-200 ${
        isModalClosing ? 'animate-out fade-out duration-200' : 'animate-in fade-in duration-200'
      }`}
    >
      <div
        className={`relative w-full max-w-md rounded-3xl border border-border/80 bg-card/95 p-6 text-card-foreground shadow-2xl backdrop-blur-2xl transition-all duration-200 sm:p-8 ${
          isModalClosing
            ? 'animate-out fade-out zoom-out-95 duration-200'
            : 'animate-in fade-in zoom-in-95 duration-250 ease-out'
        }`}
      >
        <button
          onClick={handleCloseModal}
          className="absolute right-5 top-5 rounded-full bg-secondary/80 p-2 text-muted-foreground transition-all hover:bg-secondary hover:text-foreground active:scale-95"
        >
          <X className="size-5" />
        </button>

        {successResult ? (
          <div className="flex flex-col items-center justify-center py-4 text-center animate-in fade-in zoom-in-95 duration-200">
            <div className="mb-4 flex size-16 items-center justify-center rounded-full bg-emerald-500/20 ring-1 ring-emerald-500/40">
              <CheckCircle className="size-10 text-emerald-400" />
            </div>
            <h3 className="text-xl font-bold text-foreground">Call Scheduled!</h3>
            <p className="mt-2 max-w-xs text-sm text-muted-foreground">
              Outbound SIP call scheduled for{' '}
              <span className="font-semibold text-emerald-400">{successResult.name}</span> at{' '}
              <span className="font-semibold text-indigo-400">{successResult.scheduledAt}</span>.
            </p>
            <div className="mt-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-2.5 text-xs text-emerald-300">
              📞 Shiksha AI background scheduler will dial{' '}
              <span className="font-mono">{successResult.phone}</span> right on schedule!
            </div>
            <Button
              onClick={() => {
                setSuccessResult(null);
                setParticipantName('');
                setPhoneNumber('');
                handleCloseModal();
              }}
              className="mt-6 w-full rounded-xl bg-indigo-600 font-semibold text-white hover:bg-indigo-500"
            >
              Done
            </Button>
          </div>
        ) : (
          <form onSubmit={handleSchedule} className="flex flex-col gap-4">
            <div className="flex items-center gap-3 border-b border-border/60 pb-4">
              <div className="flex size-10 items-center justify-center rounded-2xl bg-purple-500/20 ring-1 ring-purple-500/30">
                <PhoneCall className="size-5 text-purple-400" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-foreground">Schedule Outbound Call</h3>
                <p className="text-xs text-muted-foreground">
                  Shiksha AI will dial your SIP address on schedule
                </p>
              </div>
            </div>

            {errorMsg && (
              <div className="rounded-xl border border-red-500/40 bg-red-500/10 p-3 text-xs text-red-300">
                {errorMsg}
              </div>
            )}

            {/* Learner Name */}
            <div className="flex flex-col gap-1.5">
              <label className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
                <User className="size-3.5" /> Learner Name
              </label>
              <input
                type="text"
                value={participantName}
                onChange={(e) => setParticipantName(e.target.value)}
                required
                className="w-full rounded-xl border border-border bg-secondary/60 px-3.5 py-2.5 text-sm text-foreground transition-all focus:border-indigo-500 focus:bg-secondary/90 focus:outline-none"
                placeholder="e.g. Rahul"
              />
            </div>

            {/* SIP Address with Persisting Info Tooltip */}
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
                  <PhoneCall className="size-3.5" /> SIP Address
                </label>

                {/* Info Tooltip Button & Popover */}
                <div
                  className="relative inline-flex items-center"
                  onMouseEnter={handleMouseEnter}
                  onMouseLeave={handleMouseLeave}
                >
                  <button
                    type="button"
                    onClick={handleSipInfoClick}
                    className="flex items-center gap-1 rounded-md bg-indigo-500/10 px-1.5 py-0.5 text-[11px] font-medium text-indigo-400 transition-colors hover:bg-indigo-500/20 hover:text-indigo-300"
                  >
                    <Question className="size-3.5" />
                    <span>How to get SIP?</span>
                  </button>

                  {showSipInfo && (
                    <div
                      onMouseEnter={handleMouseEnter}
                      onMouseLeave={handleMouseLeave}
                      className={`absolute right-0 bottom-full z-50 mb-2 w-72 rounded-2xl border border-indigo-500/40 bg-popover/95 p-3.5 text-xs text-popover-foreground shadow-2xl backdrop-blur-xl transition-all duration-200 ${
                        isExitingSipInfo
                          ? 'animate-out fade-out zoom-out-95 duration-200'
                          : 'animate-in fade-in zoom-in-95 duration-150'
                      }`}
                    >
                      <p className="mb-1.5 flex items-center gap-1 font-bold text-indigo-300">
                        <span>💡 How to get a free SIP Address</span>
                      </p>
                      <ol className="list-inside list-decimal space-y-1.5 text-[11px] leading-relaxed text-muted-foreground">
                        <li>
                          Download & open the free{' '}
                          <strong className="text-foreground">Linphone</strong> app on PC or Mobile.
                        </li>
                        <li>
                          Register a free SIP account at{' '}
                          <a
                            href="https://www.linphone.org"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-0.5 font-semibold text-indigo-400 underline decoration-indigo-400/40 underline-offset-2 transition-colors hover:text-indigo-300 hover:decoration-indigo-300"
                          >
                            linphone.org
                            <ArrowSquareOut className="size-3" />
                          </a>
                        </li>
                        <li>
                          Your SIP address format:
                          <br />
                          <code className="mt-0.5 inline-block rounded-md bg-secondary/90 px-1.5 py-0.5 font-mono text-[10px] text-purple-300">
                            sip:username@sip.linphone.org
                          </code>
                        </li>
                      </ol>
                    </div>
                  )}
                </div>
              </div>

              <input
                type="text"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                required
                className="w-full rounded-xl border border-border bg-secondary/60 px-3.5 py-2.5 font-mono text-sm text-foreground transition-all focus:border-indigo-500 focus:bg-secondary/90 focus:outline-none"
                placeholder="sip:username@sip.linphone.org"
              />
            </div>

            {/* Schedule Option */}
            <div className="flex flex-col gap-1.5">
              <label className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
                <Clock className="size-3.5" /> When should Shiksha AI call?
              </label>

              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setScheduleOption('10s')}
                  className={`rounded-xl border p-2.5 text-xs font-semibold transition-all ${
                    scheduleOption === '10s'
                      ? 'border-indigo-500 bg-indigo-500/20 text-indigo-300 shadow-sm'
                      : 'border-border bg-secondary/40 text-muted-foreground hover:bg-secondary/70'
                  }`}
                >
                  ⚡ In 10 Seconds
                </button>
                <button
                  type="button"
                  onClick={() => setScheduleOption('1m')}
                  className={`rounded-xl border p-2.5 text-xs font-semibold transition-all ${
                    scheduleOption === '1m'
                      ? 'border-indigo-500 bg-indigo-500/20 text-indigo-300 shadow-sm'
                      : 'border-border bg-secondary/40 text-muted-foreground hover:bg-secondary/70'
                  }`}
                >
                  ⏱️ In 1 Minute
                </button>
                <button
                  type="button"
                  onClick={() => setScheduleOption('5m')}
                  className={`rounded-xl border p-2.5 text-xs font-semibold transition-all ${
                    scheduleOption === '5m'
                      ? 'border-indigo-500 bg-indigo-500/20 text-indigo-300 shadow-sm'
                      : 'border-border bg-secondary/40 text-muted-foreground hover:bg-secondary/70'
                  }`}
                >
                  ⏰ In 5 Minutes
                </button>
                <button
                  type="button"
                  onClick={() => setScheduleOption('custom')}
                  className={`rounded-xl border p-2.5 text-xs font-semibold transition-all ${
                    scheduleOption === 'custom'
                      ? 'border-indigo-500 bg-indigo-500/20 text-indigo-300 shadow-sm'
                      : 'border-border bg-secondary/40 text-muted-foreground hover:bg-secondary/70'
                  }`}
                >
                  📅 Custom Time
                </button>
              </div>

              {scheduleOption === 'custom' && (
                <input
                  type="datetime-local"
                  value={customDateTime}
                  onChange={(e) => setCustomDateTime(e.target.value)}
                  required
                  className="mt-2 w-full rounded-xl border border-border bg-secondary/60 px-3.5 py-2.5 text-sm text-foreground focus:border-indigo-500 focus:outline-none"
                />
              )}
            </div>

            <Button
              type="submit"
              disabled={isSubmitting}
              className="mt-4 h-12 w-full rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 font-mono text-sm font-bold uppercase text-white shadow-lg transition-all hover:from-purple-500 hover:to-indigo-500 hover:shadow-indigo-500/25 active:scale-[0.99]"
            >
              {isSubmitting ? 'Scheduling...' : 'Schedule Call'}
            </Button>
          </form>
        )}
      </div>
    </div>
  );
}
