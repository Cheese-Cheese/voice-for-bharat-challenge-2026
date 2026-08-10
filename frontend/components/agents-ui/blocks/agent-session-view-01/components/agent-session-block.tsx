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
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const { state: agentState } = useAgent();

  const controls: AgentControlBarControls = {
    leave: true,
    microphone: true,
    chat: supportsChatInput,
    camera: supportsVideoInput,
    screenShare: supportsScreenShare,
  };

  useEffect(() => {
    if (!room) return;
    const handleDataReceived = (
      payload: Uint8Array,
      participant: any,
      kind: any,
      topic?: string
    ) => {
      if (topic === 'tool_results' || !topic) {
        try {
          const str = new TextDecoder().decode(payload);
          const data = JSON.parse(str);
          if (data.type === 'tool_result') {
            setActiveToolCard(data);
          }
        } catch (err) {
          console.error('Failed to parse tool result data payload:', err);
        }
      }
    };

    room.on(RoomEvent.DataReceived, handleDataReceived);
    return () => {
      room.off(RoomEvent.DataReceived, handleDataReceived);
    };
  }, [room]);

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

      {/* Prominent State & Speaker Banner for Day 3 */}
      <div className="bg-background/90 text-foreground absolute top-12 left-1/2 z-50 flex -translate-x-1/2 items-center gap-2 rounded-full border border-indigo-500/30 px-4 py-1.5 text-xs font-semibold shadow-xl backdrop-blur-md">
        <span
          className={cn(
            'size-2.5 animate-pulse rounded-full',
            agentState === 'speaking' && 'bg-green-500',
            agentState === 'listening' && 'bg-indigo-500',
            agentState === 'thinking' && 'bg-amber-500',
            (agentState === 'connecting' || agentState === 'initializing') && 'bg-blue-500'
          )}
        />
        <span>
          {agentState === 'speaking' && '🔊 Shiksha AI is speaking...'}
          {agentState === 'listening' && '🎙️ Listening to you...'}
          {agentState === 'thinking' && '🧠 Thinking...'}
          {(agentState === 'connecting' || agentState === 'initializing') &&
            '⏳ Connecting to agent...'}
          {agentState === 'disconnected' && 'Disconnected'}
        </span>
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
                      <div className="flex items-center gap-2">
                        <span className="rounded-md bg-emerald-500/20 px-2.5 py-0.5 text-xs font-semibold tracking-wider text-emerald-400 uppercase">
                          ✍️ Grammar Analysis
                        </span>
                      </div>
                      <p className="text-muted-foreground text-xs italic">
                        "{activeToolCard.sentence}"
                      </p>
                      {activeToolCard.is_correct ? (
                        <p className="text-sm font-semibold text-emerald-400">
                          ✓ Grammatically Correct!
                        </p>
                      ) : (
                        <div className="space-y-1.5 text-xs">
                          <p className="font-semibold text-amber-400">
                            Found {activeToolCard.error_count} potential issue(s):
                          </p>
                          {activeToolCard.rules?.map((rule: any, idx: number) => (
                            <div key={idx} className="bg-muted/40 rounded-lg p-2.5">
                              <span className="font-semibold text-amber-300">
                                {rule.issue_type}:{' '}
                              </span>
                              <span>{rule.message}</span>
                            </div>
                          ))}
                        </div>
                      )}
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
        audioVisualizerColor={audioVisualizerColor}
        audioVisualizerColorShift={audioVisualizerColorShift}
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
