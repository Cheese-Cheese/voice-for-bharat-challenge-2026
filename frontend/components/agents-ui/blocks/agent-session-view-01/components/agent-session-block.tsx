'use client';

import React, { useEffect, useRef, useState } from 'react';
import { RoomEvent } from 'livekit-client';
import { AnimatePresence, type MotionProps, motion } from 'motion/react';
import {
  useAgent,
  useRoomContext,
  useSessionContext,
  useSessionMessages,
} from '@livekit/components-react';
import { AgentChatTranscript } from '@/components/agents-ui/agent-chat-transcript';
import {
  AgentControlBar,
  type AgentControlBarControls,
} from '@/components/agents-ui/agent-control-bar';
import { Shimmer } from '@/components/ai-elements/shimmer';
import { cn } from '@/lib/shadcn/utils';
import { TileLayout } from './tile-view';

const MotionMessage = motion.create(Shimmer);

const BOTTOM_VIEW_MOTION_PROPS: MotionProps = {
  variants: {
    visible: {
      opacity: 1,
      translateY: '0%',
    },
    hidden: {
      opacity: 0,
      translateY: '100%',
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.3,
    delay: 0.5,
    ease: 'easeOut',
  },
};

const CHAT_MOTION_PROPS: MotionProps = {
  variants: {
    hidden: {
      opacity: 0,
      transition: {
        ease: 'easeOut',
        duration: 0.3,
      },
    },
    visible: {
      opacity: 1,
      transition: {
        delay: 0.2,
        ease: 'easeOut',
        duration: 0.3,
      },
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
};

const SHIMMER_MOTION_PROPS: MotionProps = {
  variants: {
    visible: {
      opacity: 1,
      transition: {
        ease: 'easeIn',
        duration: 0.5,
        delay: 0.8,
      },
    },
    hidden: {
      opacity: 0,
      transition: {
        ease: 'easeIn',
        duration: 0.5,
        delay: 0,
      },
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
};

interface FadeProps {
  top?: boolean;
  bottom?: boolean;
  className?: string;
}

export function Fade({ top = false, bottom = false, className }: FadeProps) {
  return (
    <div
      className={cn(
        'from-background pointer-events-none h-4 bg-linear-to-b to-transparent',
        top && 'bg-linear-to-b',
        bottom && 'bg-linear-to-t',
        className
      )}
    />
  );
}

export interface AgentSessionView_01Props {
  preConnectMessage?: string;
  supportsChatInput?: boolean;
  supportsVideoInput?: boolean;
  supportsScreenShare?: boolean;
  isPreConnectBufferEnabled?: boolean;

  audioVisualizerType?: 'bar' | 'wave' | 'grid' | 'radial' | 'aura';
  audioVisualizerColor?: `#${string}`;
  audioVisualizerColorShift?: number;
  audioVisualizerBarCount?: number;
  audioVisualizerGridRowCount?: number;
  audioVisualizerGridColumnCount?: number;
  audioVisualizerRadialBarCount?: number;
  audioVisualizerRadialRadius?: number;
  audioVisualizerWaveLineWidth?: number;
  className?: string;
}

export function AgentSessionView_01({
  preConnectMessage = 'Agent is listening, ask it a question',
  supportsChatInput = true,
  supportsVideoInput = true,
  supportsScreenShare = true,
  isPreConnectBufferEnabled = true,

  audioVisualizerType,
  audioVisualizerColor,
  audioVisualizerColorShift,
  audioVisualizerBarCount,
  audioVisualizerGridRowCount,
  audioVisualizerGridColumnCount,
  audioVisualizerRadialBarCount,
  audioVisualizerRadialRadius,
  audioVisualizerWaveLineWidth,
  ref,
  className,
  ...props
}: React.ComponentProps<'section'> & AgentSessionView_01Props) {
  const session = useSessionContext();
  const room = useRoomContext();
  const { messages } = useSessionMessages(session);
  const [chatOpen, setChatOpen] = useState(false);
  const [activeToolCard, setActiveToolCard] = useState<any>(null);
  const [isOfflineSimulated, setIsOfflineSimulated] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const { state: agentState } = useAgent();

  const controls: AgentControlBarControls = {
    leave: true,
    microphone: true,
    chat: supportsChatInput,
    camera: supportsVideoInput,
    screenShare: supportsScreenShare,
  };

  const toggleOfflineMode = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    e?.preventDefault();
    const nextState = !isOfflineSimulated;
    console.log('[FallbackTest] Toggling simulated offline mode to:', nextState);
    setIsOfflineSimulated(nextState);
    if (room && room.localParticipant) {
      try {
        const payload = new TextEncoder().encode(
          JSON.stringify({ type: 'toggle_offline_mode', enabled: nextState })
        );
        room.localParticipant.publishData(payload, { reliable: true, topic: 'simulated_offline' });
        console.log('[FallbackTest] Sent toggle_offline_mode payload to room:', nextState);
      } catch (err) {
        console.error('Failed to send toggle_offline_mode payload:', err);
      }
    } else {
      console.log('[FallbackTest] Local participant not ready yet, saved state:', nextState);
    }
  };

  const [activeAgentInfo, setActiveAgentInfo] = useState<{
    name: string;
    role: string;
    voice: string;
    isSpecialist: boolean;
  }>({
    name: 'Shiksha AI',
    role: 'Main Voice Tutor',
    voice: 'Anisha Voice',
    isSpecialist: false,
  });

  useEffect(() => {
    if (!room) return;
    const handleDataReceived = (
      payload: Uint8Array,
      participant: any,
      kind: any,
      topic?: string
    ) => {
      if (topic === 'agent_tool_results' || topic === 'tool_results' || !topic) {
        try {
          const str = new TextDecoder().decode(payload);
          const data = JSON.parse(str);
          if (data.type === 'tool_result') {
            console.log('[FallbackTest] Received tool_result data payload:', data);
            setActiveToolCard(data);

            if (data.tool === 'transfer_to_scenario_specialist') {
              setActiveAgentInfo({
                name: data.data?.agent_name || 'Mitra AI',
                role: data.data?.agent_role || 'Real-Life Scenario Roleplay Specialist',
                voice: 'Samar Voice (Male)',
                isSpecialist: true,
              });
            } else if (data.tool === 'return_to_main_tutor') {
              setActiveAgentInfo({
                name: 'Shiksha AI',
                role: 'Main Voice Tutor',
                voice: 'Anisha Voice (Female)',
                isSpecialist: false,
              });
            }
          }
        } catch (err) {
          console.error('Failed to parse tool result data payload:', err);
        }
      }
    };

    // Send initial offline status if user turned it on before room connected
    if (room.state === 'connected' && room.localParticipant && isOfflineSimulated) {
      try {
        const payload = new TextEncoder().encode(
          JSON.stringify({ type: 'toggle_offline_mode', enabled: true })
        );
        room.localParticipant.publishData(payload, { reliable: true, topic: 'simulated_offline' });
        console.log('[FallbackTest] Sent initial toggle_offline_mode payload to room on connect');
      } catch (err) {
        console.error('Failed to send initial toggle_offline_mode payload:', err);
      }
    }

    room.on(RoomEvent.DataReceived, handleDataReceived);
    return () => {
      room.off(RoomEvent.DataReceived, handleDataReceived);
    };
  }, [room, isOfflineSimulated]);

  useEffect(() => {
    const lastMessage = messages.at(-1);
    const lastMessageIsLocal = lastMessage?.from?.isLocal === true;

    if (scrollAreaRef.current && lastMessageIsLocal) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <section
      ref={ref}
      className={cn('bg-background relative z-10 h-full w-full overflow-hidden', className)}
      {...props}
    >
      <Fade top className="absolute inset-x-4 top-0 z-10 h-40" />

      {/* Prominent State & Speaker Banner for Day 3, Day 5 Fallback & Day 9 Switched Agent */}
      <div className="pointer-events-auto absolute top-12 left-1/2 z-50 flex -translate-x-1/2 items-center gap-3">
        <div
          className={cn(
            'bg-background/90 text-foreground flex items-center gap-2 rounded-full border px-4 py-1.5 text-xs font-semibold shadow-xl backdrop-blur-md transition-all duration-300',
            activeAgentInfo.isSpecialist
              ? 'border-purple-500/50 ring-1 ring-purple-500/30'
              : 'border-indigo-500/30'
          )}
        >
          <span
            className={cn(
              'size-2.5 animate-pulse rounded-full',
              agentState === 'speaking' && (activeAgentInfo.isSpecialist ? 'bg-purple-400' : 'bg-green-500'),
              agentState === 'listening' && 'bg-indigo-500',
              agentState === 'thinking' && 'bg-amber-500',
              (agentState === 'connecting' || agentState === 'initializing') && 'bg-blue-500'
            )}
          />
          <span>
            {agentState === 'speaking' &&
              `${activeAgentInfo.isSpecialist ? '🎭' : '🔊'} ${activeAgentInfo.name} is speaking...`}
            {agentState === 'listening' && `🎙️ Listening to you (${activeAgentInfo.name})...`}
            {agentState === 'thinking' && `🧠 ${activeAgentInfo.name} is thinking...`}
            {(agentState === 'connecting' || agentState === 'initializing') &&
              '⏳ Connecting to agent...'}
            {agentState === 'disconnected' && 'Disconnected'}
          </span>
        </div>

        {/* iOS-Style Horizontal Sliding Switch for Graceful Fallback Test */}
        <button
          type="button"
          role="switch"
          aria-checked={isOfflineSimulated}
          onClick={toggleOfflineMode}
          className={cn(
            'pointer-events-auto relative inline-flex cursor-pointer items-center gap-2.5 rounded-full border px-3.5 py-1.5 shadow-xl backdrop-blur-md transition-all duration-300 ease-in-out select-none focus:outline-none',
            isOfflineSimulated
              ? 'border-amber-500/60 bg-amber-500/20 text-amber-300 shadow-[0_0_12px_rgba(245,158,11,0.3)]'
              : 'bg-background/90 hover:bg-background text-foreground border-indigo-500/30'
          )}
        >
          <span className="text-xs font-semibold">⚡ Fallback Test</span>
          <span
            className={cn(
              'relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border-2 border-transparent transition-colors duration-300 ease-in-out',
              isOfflineSimulated
                ? 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.6)]'
                : 'bg-zinc-700'
            )}
          >
            <span
              className={cn(
                'pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow-md transition-transform duration-300 ease-in-out',
                isOfflineSimulated ? 'translate-x-5' : 'translate-x-0'
              )}
            />
          </span>
        </button>
      </div>

      {/* Transcript or Live Domain Data Card (Day 5) positioned right below the voice wave visualizer */}
      <AnimatePresence mode="wait">
        {chatOpen ? (
          <div
            key="chat-transcript"
            className="absolute top-[48vh] bottom-[135px] z-40 flex w-full flex-col md:bottom-[160px]"
          >
            <motion.div
              {...CHAT_MOTION_PROPS}
              className="flex h-full w-full flex-col gap-4 space-y-3 transition-opacity duration-300 ease-out"
            >
              <AgentChatTranscript
                agentState={agentState}
                messages={messages}
                className="mx-auto w-full max-w-2xl [&_.is-user>div]:rounded-[22px] [&>div>div]:px-4 [&>div>div]:pt-2 md:[&>div>div]:px-6"
              />
            </motion.div>
          </div>
        ) : (
          activeToolCard && (
            <div
              key="tool-data-card"
              className="absolute top-[60vh] bottom-[135px] z-40 flex w-full flex-col items-center justify-start md:bottom-[160px]"
            >
              <motion.div
                initial={{ opacity: 0, y: 15, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 15, scale: 0.96 }}
                transition={{ duration: 0.3, ease: 'easeOut' }}
                className="mx-auto w-full max-w-lg px-4"
              >
                <div className="bg-background/95 relative rounded-2xl border border-indigo-500/40 p-5 shadow-2xl backdrop-blur-xl">
                  <button
                    onClick={() => setActiveToolCard(null)}
                    className="text-muted-foreground hover:text-foreground absolute top-3 right-3 rounded-full p-1 text-xs transition-colors"
                  >
                    ✕
                  </button>

                  {activeToolCard.status === 'offline_fallback' && (
                    <div className="mb-2 rounded-md bg-amber-500/20 px-2.5 py-1 text-xs font-semibold text-amber-300">
                      ⚡ Offline Fallback Mode Active (Simulated Network Outage)
                    </div>
                  )}

                  {activeToolCard.tool === 'lookup_word_definition' && (
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <span className="rounded-md bg-indigo-500/20 px-2.5 py-0.5 text-xs font-semibold tracking-wider text-indigo-400 uppercase">
                          📖 Live Dictionary Data
                        </span>
                        {activeToolCard.phonetics && (
                          <span className="text-muted-foreground font-mono text-xs">
                            {activeToolCard.phonetics}
                          </span>
                        )}
                      </div>
                      <h3 className="text-xl font-bold text-indigo-300 capitalize">
                        {activeToolCard.word}
                        {activeToolCard.part_of_speech && (
                          <span className="text-muted-foreground ml-2 text-xs font-normal italic">
                            ({activeToolCard.part_of_speech})
                          </span>
                        )}
                      </h3>
                      <p className="text-foreground/90 text-sm leading-relaxed">
                        {activeToolCard.definition || activeToolCard.message}
                      </p>
                      {activeToolCard.example && (
                        <p className="border-l-2 border-indigo-500/40 pl-3 text-xs text-indigo-200/90 italic">
                          "{activeToolCard.example}"
                        </p>
                      )}
                    </div>
                  )}

                  {activeToolCard.tool === 'check_sentence_grammar' && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <span className="rounded-md bg-emerald-500/20 px-2.5 py-0.5 text-xs font-semibold tracking-wider text-emerald-400 uppercase">
                          ✍️ Grammar Analysis
                        </span>
                        <span className="text-muted-foreground font-mono text-[10px]">
                          LanguageTool Engine
                        </span>
                      </div>
                      <p className="text-muted-foreground text-xs italic">
                        "{activeToolCard.sentence}"
                      </p>
                      {activeToolCard.is_correct ? (
                        <div className="space-y-1">
                          <p className="text-sm font-semibold text-emerald-400">
                            ✓ No Syntax Violations Detected
                          </p>
                          <p className="text-muted-foreground text-[11px]">
                            LanguageTool found no rule issues. Shiksha AI evaluates natural spoken
                            style.
                          </p>
                        </div>
                      ) : (
                        <div className="space-y-1.5 text-xs">
                          <p className="font-semibold text-amber-400">
                            Found {activeToolCard.error_count} potential rule issue(s):
                          </p>
                          {activeToolCard.rules?.map((rule: any, idx: number) => (
                            <div key={idx} className="bg-muted/40 space-y-1 rounded-lg p-2.5">
                              <div>
                                <span className="font-semibold text-amber-300">
                                  {rule.issue_type}:{' '}
                                </span>
                                <span>{rule.message}</span>
                              </div>
                              {rule.replacements && rule.replacements.length > 0 && (
                                <p className="text-[11px] text-emerald-300">
                                  Suggested fix: {rule.replacements.join(', ')}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {activeToolCard.tool === 'escalate_to_human_teacher' && (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between gap-2">
                        <span className="rounded-md bg-rose-500/20 px-2.5 py-0.5 text-xs font-semibold tracking-wider text-rose-300 uppercase">
                          👩‍🏫 Human Teacher Ticket Created
                        </span>
                        <span className="rounded border border-indigo-500/30 bg-indigo-950 px-2 py-0.5 font-mono text-xs font-bold text-indigo-300">
                          {activeToolCard.reference_id}
                        </span>
                      </div>
                      <div>
                        <h3 className="text-base font-bold text-indigo-200">
                          Learner: {activeToolCard.learner_name}
                        </h3>
                        <p className="mt-0.5 text-xs font-semibold text-amber-300">
                          Reason: {activeToolCard.reason} ({activeToolCard.urgency} urgency)
                        </p>
                      </div>
                      <p className="bg-muted/40 text-foreground/90 border-border/40 rounded-xl border p-3 text-xs leading-relaxed">
                        {activeToolCard.summary}
                      </p>
                      <div className="text-muted-foreground flex items-center justify-between pt-1 text-[11px]">
                        <span>
                          Status: <strong className="text-amber-400">OPEN</strong>
                        </span>
                        <a
                          href="/teacher-dashboard"
                          target="_blank"
                          rel="noreferrer"
                          className="font-semibold text-indigo-400 underline hover:text-indigo-300"
                        >
                          View Teacher Dashboard →
                        </a>
                      </div>
                    </div>
                  )}

                  {activeToolCard.tool === 'transfer_to_scenario_specialist' && (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between gap-2">
                        <span className="rounded-md bg-purple-500/20 px-2.5 py-0.5 text-xs font-semibold tracking-wider text-purple-300 uppercase">
                          🎭 Specialist Agent Active
                        </span>
                        <span className="rounded border border-purple-500/30 bg-purple-950 px-2 py-0.5 font-mono text-xs font-bold text-purple-200">
                          {activeToolCard.data?.agent_name || 'Mitra AI'}
                        </span>
                      </div>
                      <div>
                        <h3 className="text-base font-bold text-purple-200">
                          Scenario: {activeToolCard.data?.scenario_type || 'Real-Life Roleplay'}
                        </h3>
                        <p className="mt-0.5 text-xs font-semibold text-purple-300">
                          {activeToolCard.data?.agent_role || 'Real-Life Scenario Roleplay Specialist'}
                        </p>
                      </div>
                      <p className="bg-purple-950/40 text-purple-100 border-purple-800/40 rounded-xl border p-3 text-xs leading-relaxed">
                        Session handed off to <strong>Mitra AI</strong>. Practice your scenario turn-by-turn!
                      </p>
                    </div>
                  )}

                  {activeToolCard.tool === 'return_to_main_tutor' && (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between gap-2">
                        <span className="rounded-md bg-indigo-500/20 px-2.5 py-0.5 text-xs font-semibold tracking-wider text-indigo-300 uppercase">
                          ↩️ Returned to Main Tutor
                        </span>
                        <span className="rounded border border-indigo-500/30 bg-indigo-950 px-2 py-0.5 font-mono text-xs font-bold text-indigo-200">
                          Shiksha AI
                        </span>
                      </div>
                      <p className="bg-indigo-950/40 text-indigo-100 border-indigo-800/40 rounded-xl border p-3 text-xs leading-relaxed">
                        Roleplay completed! Returned to <strong>Shiksha AI</strong> for general English practice.
                      </p>
                    </div>
                  )}
                </div>
              </motion.div>
            </div>
          )
        )}
      </AnimatePresence>



      {/* Tile layout */}
      <TileLayout
        chatOpen={chatOpen}
        audioVisualizerType={audioVisualizerType}
        audioVisualizerColor={
          activeAgentInfo.isSpecialist ? '#350f52' : (audioVisualizerColor || '#615fff')
        }
        audioVisualizerColorShift={0.02}
        audioVisualizerBarCount={audioVisualizerBarCount}
        audioVisualizerRadialBarCount={audioVisualizerRadialBarCount}
        audioVisualizerRadialRadius={audioVisualizerRadialRadius}
        audioVisualizerGridRowCount={audioVisualizerGridRowCount}
        audioVisualizerGridColumnCount={audioVisualizerGridColumnCount}
        audioVisualizerWaveLineWidth={audioVisualizerWaveLineWidth}
      />
      {/* Bottom */}
      <motion.div
        {...BOTTOM_VIEW_MOTION_PROPS}
        className="absolute inset-x-3 bottom-0 z-50 md:inset-x-12"
      >
        {/* Pre-connect message */}
        {isPreConnectBufferEnabled && (
          <AnimatePresence>
            {messages.length === 0 && (
              <MotionMessage
                key="pre-connect-message"
                duration={2}
                aria-hidden={messages.length > 0}
                {...SHIMMER_MOTION_PROPS}
                className="pointer-events-none mx-auto block w-full max-w-2xl pb-4 text-center text-sm font-semibold"
              >
                {preConnectMessage}
              </MotionMessage>
            )}
          </AnimatePresence>
        )}
        <div className="bg-background relative mx-auto max-w-2xl pb-3 md:pb-12">
          <Fade bottom className="absolute inset-x-0 top-0 h-4 -translate-y-full" />
          <AgentControlBar
            variant="livekit"
            controls={controls}
            isChatOpen={chatOpen}
            isConnected={session.isConnected}
            onDisconnect={session.end}
            onIsChatOpenChange={setChatOpen}
          />
        </div>
      </motion.div>
    </section>
  );
}
