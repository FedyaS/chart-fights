'use client';

import type { MatchEndResult, PlayerState } from '../types';
import { otherPlayer } from '../lib/matchState';

interface EndScreenProps {
  result: MatchEndResult;
  onRematch: () => void;
  onLobby: () => void;
}

export function EndScreen({ result, onRematch, onLobby }: EndScreenProps) {
  const you = result.players[result.you] ?? null;
  const opp = otherPlayer(result.players, result.you);

  let outcome: 'win' | 'lose' | 'draw';
  if (result.winner == null) outcome = 'draw';
  else if (result.winner === result.you) outcome = 'win';
  else outcome = 'lose';

  const banner = {
    win: { text: 'VICTORY', color: '#22c55e', sub: 'You out-traded your opponent.' },
    lose: { text: 'DEFEAT', color: '#ef4444', sub: 'They had the better book this time.' },
    draw: { text: 'DRAW', color: '#eab308', sub: 'Dead heat. Run it back.' },
  }[outcome];

  const row = (label: string, p: PlayerState | null, accent: string) => (
    <div className="flex items-center justify-between rounded border border-[#2a313a] bg-[#0b0e14] px-4 py-3">
      <div>
        <div className="text-[10px] uppercase tracking-widest" style={{ color: accent }}>{label}</div>
        <div className="text-[11px] text-[#6b7280] font-mono">{p?.id ?? '—'}</div>
      </div>
      <div className="text-right">
        <div className="text-2xl font-semibold font-mono tabular-nums">{(p?.equity ?? 100).toFixed(2)}</div>
        <div className="text-xs font-mono" style={{ color: (p?.pnl ?? 0) >= 0 ? '#22c55e' : '#ef4444' }}>
          {(p?.pnl ?? 0) >= 0 ? '+' : ''}{(p?.pnl ?? 0).toFixed(2)} PnL
        </div>
      </div>
    </div>
  );

  return (
    <div className="max-w-md mx-auto mt-10 space-y-6 text-center">
      <div>
        <div className="text-5xl font-bold tracking-tighter" style={{ color: banner.color }}>{banner.text}</div>
        <div className="mt-2 text-sm text-[#9ca3af]">{banner.sub}</div>
      </div>
      <div className="space-y-2 text-left">
        {row('You', you, '#22c55e')}
        {row('Opponent', opp, '#f97316')}
      </div>
      {result.reveal?.ticker && (
        <div className="rounded border border-[#2a313a] bg-[#0b0e14] px-4 py-3 text-left text-sm">
          <div className="text-[10px] uppercase tracking-widest text-[#6b7280] mb-1">Reveal</div>
          <div>You were trading <span className="font-semibold text-white">{result.reveal.ticker}</span>
            {result.reveal.sector ? <span className="text-[#9ca3af]"> ({result.reveal.sector})</span> : null}</div>
          {result.reveal.start_date && (
            <div className="text-xs text-[#6b7280] font-mono mt-0.5">{result.reveal.start_date} → {result.reveal.end_date}</div>
          )}
        </div>
      )}
      <div className="flex gap-2">
        <button onClick={onRematch} className="flex-1 py-2 rounded bg-white text-black font-medium hover:bg-[#e5e7eb]">REMATCH</button>
        <button onClick={onLobby} className="flex-1 py-2 rounded border border-[#2a313a] hover:bg-[#1a1f26]">BACK TO LOBBY</button>
      </div>
    </div>
  );
}
