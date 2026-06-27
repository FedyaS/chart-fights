'use client';

import type { VoiceStatus } from '../hooks/useVoiceChat';

interface VoicePanelProps {
  status: VoiceStatus;
  micOn: boolean;
  remoteActive: boolean;
  errorMsg: string | null;
  onStart: () => void;
  onStop: () => void;
  onToggleMic: () => void;
}

const STATUS_LABEL: Record<VoiceStatus, string> = {
  idle: 'Disconnected',
  connecting: 'Connecting…',
  connected: 'Connected',
  error: 'Error',
  unsupported: 'Unavailable',
};

const STATUS_COLOR: Record<VoiceStatus, string> = {
  idle: '#6b7280',
  connecting: '#eab308',
  connected: '#22c55e',
  error: '#ef4444',
  unsupported: '#ef4444',
};

export function VoicePanel({ status, micOn, remoteActive, errorMsg, onStart, onStop, onToggleMic }: VoicePanelProps) {
  const live = status === 'connected' || status === 'connecting';
  return (
    <div className="panel p-3">
      <div className="text-xs font-medium mb-2 flex items-center justify-between">
        <span>VOICE · WebRTC P2P</span>
        <span className="flex items-center gap-1 text-[10px]">
          <span className="w-1.5 h-1.5 rounded-full" style={{ background: STATUS_COLOR[status] }} />
          <span style={{ color: STATUS_COLOR[status] }}>{STATUS_LABEL[status]}</span>
        </span>
      </div>
      <div className="flex gap-2">
        {!live ? (
          <button onClick={onStart} className="voice-btn flex-1 py-1.5 text-xs rounded border border-[#2a313a] bg-[#1a1f26] hover:bg-[#272d37]">
            CALL OPPONENT
          </button>
        ) : (
          <>
            <button onClick={onToggleMic} className={`voice-btn flex-1 py-1.5 text-xs rounded border ${micOn ? 'active border-[#22c55e]' : 'border-[#2a313a] bg-[#1a1f26]'}`}>
              {micOn ? 'MIC ON' : 'MIC MUTED'}
            </button>
            <button onClick={onStop} className="voice-btn flex-1 py-1.5 text-xs rounded border border-[#ef4444]/40 bg-[#1a1f26] hover:bg-[#272d37] text-[#ef4444]">
              HANG UP
            </button>
          </>
        )}
      </div>
      <div className="text-[10px] text-[#9ca3af] mt-1.5">
        {status === 'unsupported'
          ? 'Mic/WebRTC unavailable here (needs HTTPS + a second connected player).'
          : status === 'error'
            ? (errorMsg ?? 'Voice error.')
            : remoteActive
              ? 'Opponent audio live. Trash talk + psych warfare engaged.'
              : 'Trash talk + psych. Both players must be in the same match.'}
      </div>
    </div>
  );
}
