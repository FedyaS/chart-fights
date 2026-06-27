'use client';

import type { Arena } from '../types';

interface ArenaLobbyProps {
  arenas: Arena[];
  onSelect: (arena: Arena) => void;
  selectedId?: string;
  connecting?: boolean;
}

export function ArenaLobby({ arenas, onSelect, selectedId, connecting }: ArenaLobbyProps) {
  return (
    <div className="space-y-3">
      <div>
        <h2 className="text-xl font-semibold tracking-tight">Select Arena</h2>
        <p className="text-sm text-[#9ca3af]">Choose a normalized historical slice. Same data, same hidden future for both duelists.</p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {arenas.map((a) => {
          const active = a.id === selectedId;
          const barCount = a.numBars ?? a.bars.length;
          return (
            <button
              key={a.id}
              onClick={() => !connecting && onSelect(a)}
              disabled={connecting}
              className={`lobby-card text-left p-4 rounded-lg border ${active ? 'border-[#ef4444] bg-[#1a1f26]' : 'border-[#2a313a] bg-[#111418] hover:border-[#ef4444]/60'} ${connecting ? 'opacity-60 cursor-wait' : ''}`}
            >
              <div className="font-semibold">{a.name}</div>
              <div className="text-xs text-[#f97316] mt-0.5">{a.ticker} • {barCount} bars</div>
              <div className="text-xs text-[#9ca3af] mt-2 leading-snug">{a.description}</div>
              <div className="mt-3 text-[10px] uppercase tracking-widest text-[#9ca3af]">
                {active && connecting ? 'Connecting…' : 'Enter Duel →'}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
