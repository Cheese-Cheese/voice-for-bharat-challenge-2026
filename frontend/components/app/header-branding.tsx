'use client';

import React, { useEffect, useState } from 'react';
import { RoomEvent } from 'livekit-client';
import { useRoomContext, useSessionContext } from '@livekit/components-react';
import { GraduationCap, MaskHappy } from '@phosphor-icons/react';
import { motion, AnimatePresence } from 'motion/react';
import type { AppConfig } from '@/app-config';

const SHIKSHA_FAVICON = '/icon.svg';
const MITRA_FAVICON =
  'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">🎭</text></svg>';

interface HeaderBrandingProps {
  appConfig: AppConfig;
}

export function HeaderBranding({ appConfig }: HeaderBrandingProps) {
  const room = useRoomContext();
  const { isConnected } = useSessionContext();
  const [activeAgent, setActiveAgent] = useState<{
    name: string;
    tagline: string;
    role: string;
    isSpecialist: boolean;
    tabTitle: string;
    favicon: string;
  }>({
    name: 'Shiksha AI',
    tagline: appConfig.companyName || 'Shiksha AI | #VoiceForBharat',
    role: 'Main Voice Tutor',
    isSpecialist: false,
    tabTitle: appConfig.pageTitle || 'Shiksha AI — Spoken English Tutor',
    favicon: SHIKSHA_FAVICON,
  });

  // Reset to default Shiksha AI whenever disconnected / returning to WelcomeView
  useEffect(() => {
    if (!isConnected) {
      setActiveAgent({
        name: 'Shiksha AI',
        tagline: appConfig.companyName || 'Shiksha AI | #VoiceForBharat',
        role: 'Main Voice Tutor',
        isSpecialist: false,
        tabTitle: appConfig.pageTitle || 'Shiksha AI — Spoken English Tutor',
        favicon: SHIKSHA_FAVICON,
      });
    }
  }, [isConnected, appConfig]);

  useEffect(() => {
    if (!room) return;

    const handleDataReceived = (
      payload: Uint8Array,
      _participant: any,
      _kind: any,
      topic?: string
    ) => {
      if (topic === 'agent_tool_results' || topic === 'tool_results' || !topic) {
        try {
          const str = new TextDecoder().decode(payload);
          const data = JSON.parse(str);
          if (data.type === 'tool_result') {
            if (data.tool === 'transfer_to_scenario_specialist') {
              setActiveAgent({
                name: data.data?.agent_name || 'Mitra AI',
                tagline: `${data.data?.agent_name || 'Mitra AI'} | #VoiceForBharat`,
                role: data.data?.agent_role || 'Real-Life Scenario Roleplay Specialist',
                isSpecialist: true,
                tabTitle: 'Mitra AI — Real-Life Scenario Specialist',
                favicon: MITRA_FAVICON,
              });
            } else if (data.tool === 'return_to_main_tutor') {
              setActiveAgent({
                name: 'Shiksha AI',
                tagline: 'Shiksha AI | #VoiceForBharat',
                role: 'Main Voice Tutor',
                isSpecialist: false,
                tabTitle: 'Shiksha AI — Spoken English Tutor',
                favicon: SHIKSHA_FAVICON,
              });
            }
          }
        } catch (err) {
          console.error('Failed to parse agent tool payload in header:', err);
        }
      }
    };

    room.on(RoomEvent.DataReceived, handleDataReceived);
    return () => {
      room.off(RoomEvent.DataReceived, handleDataReceived);
    };
  }, [room]);

  // Update browser tab title and favicon dynamically
  useEffect(() => {
    if (typeof window === 'undefined') return;

    // 1. Update Title
    document.title = activeAgent.tabTitle;

    // 2. Update Favicon
    let faviconLink = document.querySelector("link[rel='icon']") as HTMLLinkElement;
    if (!faviconLink) {
      faviconLink = document.createElement('link');
      faviconLink.rel = 'icon';
      document.head.appendChild(faviconLink);
    }
    faviconLink.href = activeAgent.favicon;

    let appleIcon = document.querySelector("link[rel='apple-touch-icon']") as HTMLLinkElement;
    if (appleIcon) {
      appleIcon.href = activeAgent.favicon;
    }
  }, [activeAgent]);

  return (
    <header className="fixed top-0 left-0 z-50 flex w-full flex-row items-center justify-between p-6">
      <AnimatePresence mode="wait">
        <motion.div
          key={activeAgent.name}
          initial={{ opacity: 0, y: -10, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 10, scale: 0.95 }}
          transition={{ duration: 0.3, ease: 'easeOut' }}
          className="flex items-center gap-2.5"
        >
          {activeAgent.isSpecialist ? (
            <div className="flex size-8 items-center justify-center rounded-xl bg-purple-500/20 ring-1 ring-purple-500/40 backdrop-blur-md shadow-lg shadow-purple-950/30">
              <MaskHappy className="size-5 text-purple-300 animate-pulse" />
            </div>
          ) : (
            <div className="flex size-8 items-center justify-center rounded-xl bg-indigo-500/20 ring-1 ring-indigo-500/40 backdrop-blur-md shadow-lg shadow-indigo-950/30">
              <GraduationCap className="size-5 text-indigo-300" />
            </div>
          )}

          <div className="flex flex-col">
            <span className="text-foreground flex items-center gap-2 text-sm font-bold tracking-wide">
              {activeAgent.tagline}
              {activeAgent.isSpecialist && (
                <span className="rounded-full bg-purple-500/20 px-2 py-0.5 text-[10px] font-semibold text-purple-300 ring-1 ring-purple-500/30">
                  Specialist Active
                </span>
              )}
            </span>
            <span className="text-[11px] font-medium text-muted-foreground">
              {activeAgent.role}
            </span>
          </div>
        </motion.div>
      </AnimatePresence>

      <span className="text-foreground hidden font-mono text-xs font-bold tracking-wider uppercase sm:inline">
        Built with{' '}
        <a
          target="_blank"
          rel="noopener noreferrer"
          href="https://docs.livekit.io/agents"
          className="underline underline-offset-4 hover:text-indigo-400 transition-colors"
        >
          LiveKit Agents
        </a>
      </span>
    </header>
  );
}
