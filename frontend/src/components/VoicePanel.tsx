'use client';

import { useState } from 'react';

interface VoicePanelProps {
  onToggleMic?: (on: boolean) => void;
  onPTT?: (down: boolean) => void;
}

export function VoicePanel({ onToggleMic, onPTT }: VoicePanelProps) {
  const [micOn, setMicOn] = useState(false);
  const [isPTT, setIsPTT] = useState(false);

  return (
    <div className="panel p-3">
      <div className="text-xs font-medium mb-2">VOICE (stub • WebRTC later)</div>
      <div className="flex gap-2">
        <button onClick={() => { const next = !micOn; setMicOn(next); onToggleMic?.(next); }} className={`voice-btn flex-1 py-1.5 text-xs rounded border ${micOn ? 'active border-[#22c55e]' : 'border-[#2a313a] bg-[#1a1f26]'}`}>{micOn ? '🎤 MIC ON' : 'MIC OFF'}</button>
        <button onMouseDown={() => { setIsPTT(true); onPTT?.(true); }} onMouseUp={() => { setIsPTT(false); onPTT?.(false); }} onMouseLeave={() => { if (isPTT) { setIsPTT(false); onPTT?.(false); } }} className="voice-btn flex-1 py-1.5 text-xs rounded border border-[#2a313a] bg-[#1a1f26] active:bg-[#272d37]">PTT HOLD</button>
      </div>
      <div className="text-[10px] text-[#9ca3af] mt-1.5">Trash talk + psych. Connected via room (future). Mute opp • vol sliders in v2.</div>
    </div>
  );
}
