'use client';

import type { PlayerState } from '../types';

interface ScoreboardProps {
  you: PlayerState | null;
  opp: PlayerState | null;
}

function pnlColor(v: number) {
  if (v > 0.0001) return '#22c55e';
  if (v < -0.0001) return '#ef4444';
  return '#9ca3af';
}

function fmt(v: number, sign = false) {
  const s = sign && v > 0 ? '+' : '';
  return `${s}${v.toFixed(2)}`;
}

function PlayerCard({ p, label, accent }: { p: PlayerState | null; label: string; accent: string }) {
  const equity = p?.equity ?? 100;
  const pnl = p?.pnl ?? 0;
  const unreal = p?.unrealized ?? 0;
  return (
    <div className="flex-1 rounded border border-[#2a313a] bg-[#0b0e14] p-2.5">
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-widest" style={{ color: accent }}>{label}</span>
        <span className="text-[10px] text-[#6b7280] font-mono">{p?.id ?? '—'}</span>
      </div>
      <div className="mt-1 flex items-baseline gap-1.5">
        <span className="text-lg font-semibold font-mono tabular-nums">{equity.toFixed(2)}</span>
        <span className="text-[10px] text-[#6b7280]">equity</span>
      </div>
      <div className="text-xs font-mono tabular-nums" style={{ color: pnlColor(pnl) }}>
        {fmt(pnl, true)} PnL
        <span className="text-[10px] text-[#9ca3af]"> · {fmt(unreal, true)} unreal</span>
      </div>
    </div>
  );
}

export function Scoreboard({ you, opp }: ScoreboardProps) {
  const positions = you?.positions ?? [];
  return (
    <div className="panel p-3 flex flex-col gap-2.5">
      <div className="text-xs font-medium">SCOREBOARD</div>
      <div className="flex gap-2">
        <PlayerCard p={you} label="You" accent="#22c55e" />
        <PlayerCard p={opp} label="Opponent" accent="#f97316" />
      </div>
      <div>
        <div className="text-[10px] uppercase tracking-widest text-[#6b7280] mb-1">Your Positions</div>
        {positions.length === 0 ? (
          <div className="text-[11px] text-[#6b7280]">Flat — no open positions.</div>
        ) : (
          <div className="space-y-0.5">
            {positions.map((pos, i) => (
              <div key={i} className="flex items-center justify-between text-[11px] font-mono">
                <span className={pos.side === 'long' ? 'text-[#22c55e]' : 'text-[#ef4444]'}>
                  {pos.side.toUpperCase()} {pos.instr} ×{pos.size}
                </span>
                <span className="text-[#9ca3af]">@ {pos.entry.toFixed(2)}{pos.unrealized != null ? ` · ${fmt(pos.unrealized, true)}` : ''}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
