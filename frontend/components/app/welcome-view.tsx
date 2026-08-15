'use client';

import { useState } from 'react';
import {
  ChatCircleText,
  GraduationCap,
  MaskHappy,
  MicrophoneSlash,
  Sparkle,
  ChartBar,
  UserCheck,
  PhoneCall,
} from '@phosphor-icons/react';
import { motion, AnimatePresence } from 'motion/react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';

import { ScheduleCallModal } from '@/components/app/schedule-call-modal';

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
}

const FEATURE_PILLARS = [
  {
    id: 'mitra',
    icon: MaskHappy,
    title: 'Mitra AI',
    badgeText: 'Roleplay Specialist',
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/10 border-purple-500/20 hover:border-purple-500/50 hover:bg-purple-500/20',
  },
  {
    id: 'shiksha',
    icon: GraduationCap,
    title: 'Shiksha AI',
    badgeText: 'Main Tutor',
    color: 'text-indigo-400',
    bgColor: 'bg-indigo-500/10 border-indigo-500/20 hover:border-indigo-500/50 hover:bg-indigo-500/20',
  },
  {
    id: 'tools',
    icon: Sparkle,
    title: 'Smart Tools',
    badgeText: 'Memory & Analytics',
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-500/10 border-emerald-500/20 hover:border-emerald-500/50 hover:bg-emerald-500/20',
  },
];

const CARD_DETAILS: Record<string, { title: string; desc: string; colorClass: string }> = {
  shiksha: {
    title: 'Shiksha AI',
    desc: 'Your dedicated Spoken English tutor designed for vernacular learners. Practice natural everyday conversations, learn new vocabulary words in real-time, get gentle grammar corrections, and build confidence speaking English effortlessly.',
    colorClass: 'text-indigo-400',
  },
  mitra: {
    title: 'Mitra AI',
    desc: 'Specialist real-life roleplay agent designed for interactive scenario practice. Build confidence with immersive, turn-by-turn conversations for real-world situations like ordering fast food, navigating city directions, or talking to a doctor.',
    colorClass: 'text-purple-400',
  },
  tools: {
    title: 'Smart Tools & Memory',
    desc: 'Comprehensive learning ecosystem equipped with persistent SQLite memory profiles, real-time dictionary & pronunciation lookup tools, human teacher escalation routing, and detailed call analytics dashboards.',
    colorClass: 'text-emerald-400',
  },
};

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  const [micError, setMicError] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [activeCardId, setActiveCardId] = useState<string>('shiksha');
  const [isScheduleModalOpen, setIsScheduleModalOpen] = useState(false);

  const currentDetails = CARD_DETAILS[activeCardId] || CARD_DETAILS.shiksha;

  const handleStartCall = async () => {
    setMicError(null);
    setIsConnecting(true);

    try {
      // Check microphone permission before connecting
      await navigator.mediaDevices.getUserMedia({ audio: true });
      onStartCall();
    } catch (err: unknown) {
      setIsConnecting(false);
      const error = err as { name?: string; message?: string };
      if (error?.name === 'NotAllowedError' || error?.name === 'PermissionDeniedError') {
        setMicError(
          'Microphone access blocked! Please click the lock (🔒) or camera icon in your browser address bar to allow microphone access, then click "Start Learning" again.'
        );
      } else {
        setMicError(
          'Unable to access your microphone. Please make sure your microphone is plugged in and allowed by your browser.'
        );
      }
    }
  };

  return (
    <div
      ref={ref}
      className="relative flex min-h-svh w-full flex-col items-center justify-center p-4 md:p-8"
    >
      <ScheduleCallModal
        isOpen={isScheduleModalOpen}
        onClose={() => setIsScheduleModalOpen(false)}
      />

      {/* Background Ambient Glow */}
      <div className="pointer-events-none absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 size-[600px] rounded-full bg-gradient-to-tr from-indigo-600/15 via-purple-600/10 to-pink-600/5 blur-3xl" />

      <section className="relative z-10 bg-card/60 border-border/80 flex w-full max-w-3xl flex-col items-center justify-center rounded-3xl border p-8 text-center shadow-2xl backdrop-blur-xl md:p-12">
        {/* Track Badge */}
        <div className="mb-6 flex flex-wrap items-center justify-center gap-2.5">
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/15 px-4 py-1.5 text-xs font-semibold tracking-wide text-indigo-300 shadow-sm">
            <GraduationCap className="size-4 text-indigo-400" />
            <span>Learning &amp; Literacy Track | #VoiceForBharat</span>
          </div>

          <a
            href="/teacher-dashboard"
            className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1.5 text-xs font-semibold text-emerald-300 transition-all hover:border-emerald-500/50 hover:bg-emerald-500/20 hover:scale-105"
          >
            <UserCheck className="size-3.5 text-emerald-400" />
            <span>Teacher Dashboard</span>
          </a>

          <a
            href="/analytics-dashboard"
            className="inline-flex items-center gap-1.5 rounded-full border border-purple-500/30 bg-purple-500/10 px-3.5 py-1.5 text-xs font-semibold text-purple-300 transition-all hover:border-purple-500/50 hover:bg-purple-500/20 hover:scale-105"
          >
            <ChartBar className="size-3.5 text-purple-400" />
            <span>Call Analytics</span>
          </a>
        </div>

        {/* Dynamic Hero Title & Description */}
        <div className="min-h-[150px] md:min-h-[130px] flex flex-col items-center justify-center">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentDetails.title}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.2 }}
              className="flex flex-col items-center"
            >
              <h1 className="text-foreground text-3xl font-extrabold tracking-tight md:text-5xl">
                <span className={currentDetails.colorClass}>{currentDetails.title}</span>
              </h1>

              <p className="text-muted-foreground mt-3 max-w-xl text-base leading-relaxed md:text-lg">
                {currentDetails.desc}
              </p>
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Feature Cards Grid (Compact labels, no duplicate descriptions) */}
        <div className="mt-8 grid w-full grid-cols-1 gap-4 sm:grid-cols-3">
          {FEATURE_PILLARS.map(({ id, icon: Icon, title, badgeText, color, bgColor }) => (
            <div
              key={title}
              onMouseEnter={() => setActiveCardId(id)}
              onMouseLeave={() => setActiveCardId('shiksha')}
              className={`cursor-pointer flex flex-col items-start rounded-2xl border p-4 text-left transition-all hover:scale-[1.03] ${bgColor} ${
                activeCardId === id ? 'ring-2 ring-indigo-500/50 scale-[1.02]' : ''
              }`}
            >
              <div className="mb-2.5 flex w-full items-center justify-between">
                <div className="rounded-xl bg-background/80 p-2 shadow-sm">
                  <Icon className={`size-5 ${color}`} />
                </div>
                <span className="rounded-full bg-background/60 px-2 py-0.5 text-[10px] font-semibold text-muted-foreground">
                  {badgeText}
                </span>
              </div>
              <h3 className="text-foreground text-sm font-bold">{title}</h3>
            </div>
          ))}
        </div>

        {/* Microphone Error Alert */}
        {micError && (
          <Alert variant="destructive" className="mt-6 border-red-500/50 bg-red-500/10 text-left">
            <MicrophoneSlash className="size-5 text-red-400" />
            <AlertTitle className="font-semibold text-red-400">Microphone Access Denied</AlertTitle>
            <AlertDescription className="text-xs leading-relaxed text-red-300">
              {micError}
            </AlertDescription>
          </Alert>
        )}

        {/* Start Call & Schedule Call CTA Buttons */}
        <div className="mt-8 flex w-full max-w-lg flex-col gap-3 sm:flex-row sm:items-center sm:justify-center">
          <Button
            size="lg"
            onClick={handleStartCall}
            disabled={isConnecting}
            className="h-14 flex-1 rounded-2xl bg-gradient-to-r from-indigo-600 to-purple-600 font-mono text-sm font-bold tracking-wider text-white uppercase shadow-xl shadow-indigo-600/25 transition-all hover:from-indigo-500 hover:to-purple-500 hover:shadow-indigo-500/40 active:scale-95 disabled:opacity-75"
          >
            {isConnecting ? (
              <span className="flex items-center justify-center gap-2">
                <span className="size-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Connecting...
              </span>
            ) : (
              <span className="flex items-center justify-center gap-2">
                <ChatCircleText className="size-5" />
                {startButtonText}
              </span>
            )}
          </Button>

          <Button
            size="lg"
            type="button"
            onClick={() => setIsScheduleModalOpen(true)}
            className="h-14 flex-1 rounded-2xl border border-purple-500/40 bg-purple-500/15 font-mono text-sm font-bold tracking-wider text-purple-200 uppercase shadow-lg backdrop-blur-md transition-all hover:bg-purple-500/25 hover:border-purple-500/60 active:scale-95"
          >
            <span className="flex items-center justify-center gap-2">
              <PhoneCall className="size-5 text-purple-400" />
              Schedule Call
            </span>
          </Button>
        </div>

        {/* System Status Indicator */}
        <div className="mt-4 flex items-center justify-center gap-2 text-xs font-medium text-muted-foreground">
          <span className="inline-block size-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>Pipeline Ready:</span>
          <span className="font-semibold text-indigo-400">
            {isConnecting ? 'Establishing Connection...' : 'Murf Falcon + LiveKit Online'}
          </span>
        </div>
      </section>

      {/* Footer Info */}
      <footer className="text-muted-foreground mt-8 text-center text-xs tracking-wide">
        Powered by <span className="text-foreground font-semibold">Murf Falcon TTS</span>, Deepgram
        Nova-3, Gemini 3.5 &amp; LiveKit Agents
      </footer>
    </div>
  );
};
