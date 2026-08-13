'use client';

import { useState } from 'react';
import {
  BookOpen,
  ChatCircleText,
  GraduationCap,
  MicrophoneSlash,
  Sparkle,
} from '@phosphor-icons/react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
}

const PRACTICE_TOPICS = [
  { icon: ChatCircleText, label: 'Everyday Conversation' },
  { icon: BookOpen, label: 'Vocabulary & Grammar' },
  { icon: Sparkle, label: 'Confidence Building' },
];

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  const [micError, setMicError] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);

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
      className="flex min-h-svh w-full flex-col items-center justify-center p-4 md:p-8"
    >
      <section className="bg-card/50 border-border/60 flex w-full max-w-xl flex-col items-center justify-center rounded-3xl border p-6 text-center shadow-xl backdrop-blur-md md:p-10">
        {/* Shiksha AI Badge & Dashboard Links */}
        <div className="mb-4 flex flex-wrap items-center justify-center gap-2">
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-500/20 bg-indigo-500/10 px-4 py-1.5 text-xs font-semibold tracking-wide text-indigo-400">
            <GraduationCap className="size-4" />
            <span>Learning & Literacy Track | #VoiceForBharat</span>
          </div>
          <a
            href="/teacher-dashboard"
            className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1.5 text-xs font-semibold text-emerald-300 transition-all hover:border-emerald-500/50 hover:bg-emerald-500/20"
          >
            <span>👩‍🏫 Teacher Dashboard</span>
          </a>
          <a
            href="/analytics-dashboard"
            className="inline-flex items-center gap-1.5 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3.5 py-1.5 text-xs font-semibold text-indigo-300 transition-all hover:border-indigo-500/50 hover:bg-indigo-500/20"
          >
            <span>📊 Call Analytics</span>
          </a>
        </div>

        {/* Hero Title */}
        <h1 className="text-foreground text-2xl font-bold tracking-tight md:text-3xl">
          Shiksha AI — Spoken English Tutor
        </h1>

        <p className="text-muted-foreground mt-2 max-w-md text-sm leading-relaxed md:text-base">
          Practice speaking English naturally with your personal AI buddy. Learn daily vocabulary,
          improve fluency, and build confidence!
        </p>

        {/* Topic Badges */}
        <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
          {PRACTICE_TOPICS.map(({ icon: Icon, label }) => (
            <span
              key={label}
              className="bg-secondary/70 text-secondary-foreground border-border/40 inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium"
            >
              <Icon className="size-3.5 text-indigo-400" />
              {label}
            </span>
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

        {/* Start Button */}
        <Button
          size="lg"
          onClick={handleStartCall}
          disabled={isConnecting}
          className="mt-8 w-full max-w-xs rounded-2xl bg-indigo-600 font-mono text-sm font-bold tracking-wider text-white uppercase shadow-lg transition-all hover:bg-indigo-500 active:scale-95"
        >
          {isConnecting ? (
            <span className="flex items-center gap-2">
              <span className="size-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              Connecting...
            </span>
          ) : (
            startButtonText
          )}
        </Button>

        {/* Status Indicator */}
        <p className="text-muted-foreground mt-3 text-xs font-medium">
          State:{' '}
          <span className="font-semibold text-indigo-400">
            {isConnecting ? 'Connecting...' : 'Ready'}
          </span>
        </p>
      </section>

      {/* Footer Info */}
      <footer className="text-muted-foreground mt-8 text-center text-xs">
        Powered by <span className="text-foreground font-semibold">Murf Falcon TTS</span> & LiveKit
        Agents
      </footer>
    </div>
  );
};
