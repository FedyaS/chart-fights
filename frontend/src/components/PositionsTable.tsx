'use client';

import { useState } from 'react';
import type { PlayerState, OpenOrder } from '../types';

interface PositionsTableProps {
  me: PlayerState | null;
  markPrice: number;
  sector?: string;
  disabled?: boolean;
  onClose: (instr: string, fraction: number) => void;
  onSetBracketLeg: (instr: string, kind: 'tp' | 'sl', price: number) => void;
  onCancelOrder: (id: string) => void;
}

function unrealized(size: number, entry: number, mark: number, isLong: boolean): number {
  if (!entry) return 0;
  return size * (isLong ? 1 : -1) * (mark - entry) / entry;
}

function fmt(v: number, sign = false) {
  const s = sign && v > 0 ? '+' : '';
  return `${s}${v.toFixed(2)}`;
}

export function PositionsTable({ me, markPrice, sector, disabled, onClose, onSetBracketLeg, onCancelOrder }: PositionsTableProps) {
  const [editing, setEditing] = useState<{ instr: string; kind: 'tp' | 'sl' } | null>(null);
  const [editVal, setEditVal] = useState('');

  const positions = me?.positions ?? [];
  const orders = me?.orders ?? [];
  // bracket legs grouped by instrument so we can show current TP/SL next to each position
  const legFor = (instr: string, kind: 'tp' | 'sl'): OpenOrder | undefined =>
    orders.find((o) => o.instr === instr && (o.kind === kind || (kind === 'tp' && o.type === 'limit' && o.reduceOnly) || (kind === 'sl' && o.type === 'stop' && o.reduceOnly)));
  const standalone = orders.filter((o) => !o.reduceOnly && o.kind == null);
  const label = sector ?? 'Asset';

  const startEdit = (instr: string, kind: 'tp' | 'sl', current?: number) => {
    setEditing({ instr, kind });
    setEditVal((current ?? markPrice).toFixed(2));
  };
  const commitEdit = () => {
    if (!editing) return;
    const v = Number(editVal);
    if (Number.isFinite(v) && v > 0) onSetBracketLeg(editing.instr, editing.kind, v);
    setEditing(null);
  };

  const equity = me?.equity ?? 100;
  const unreal = me?.unrealized ?? 0;
  const cash = equity - unreal;                 // settled value (100 + realized)
  const bpLeft = Math.max(0, (me?.buyingPower ?? equity * 3) - (me?.exposure ?? 0));

  const stat = (label: string, value: string, color = '#e5e7eb') => (
    <div>
      <div className="text-[9px] uppercase tracking-widest text-[#6b7280]">{label}</div>
      <div className="font-mono text-sm tabular-nums" style={{ color }}>{value}</div>
    </div>
  );

  return (
    <div className="panel p-3 flex flex-col gap-2">
      <div className="text-xs font-medium">ACCOUNT</div>
      <div className="grid grid-cols-2 gap-2 rounded border border-[#2a313a] bg-[#0b0e14] p-2">
        {stat('Cash', cash.toFixed(2))}
        {stat('Equity', equity.toFixed(2))}
        {stat('Open P/L', `${unreal >= 0 ? '+' : ''}${unreal.toFixed(2)}`, unreal > 0.0001 ? '#22c55e' : unreal < -0.0001 ? '#ef4444' : '#9ca3af')}
        {stat('Buying Power', bpLeft.toFixed(0))}
      </div>
      <div className="text-xs font-medium mt-1">POSITIONS</div>
      {positions.length === 0 ? (
        <div className="text-[11px] text-[#6b7280]">Flat — no open positions.</div>
      ) : (
        <div className="space-y-2">
          {positions.map((pos, i) => {
            const isLong = pos.size > 0 || pos.side === 'long';
            const absSize = Math.abs(pos.size);
            const up = pos.unrealized != null ? pos.unrealized : unrealized(absSize, pos.entry, markPrice, isLong);
            const upPct = pos.entry ? (up / absSize) * 100 / (markPrice / pos.entry) : 0;
            const tp = legFor(pos.instr, 'tp');
            const sl = legFor(pos.instr, 'sl');
            return (
              <div key={i} className="rounded border border-[#2a313a] bg-[#0b0e14] p-2 text-[11px]">
                <div className="flex items-center justify-between">
                  <span className={isLong ? 'text-[#22c55e] font-medium' : 'text-[#ef4444] font-medium'}>
                    {isLong ? 'LONG' : 'SHORT'} {label} ×{absSize}
                  </span>
                  <span className="font-mono" style={{ color: up >= 0 ? '#22c55e' : '#ef4444' }}>{fmt(up, true)}</span>
                </div>
                <div className="flex items-center justify-between text-[#9ca3af] mt-0.5 font-mono">
                  <span>entry {pos.entry.toFixed(2)} · mark {markPrice.toFixed(2)}</span>
                </div>
                <div className="flex items-center gap-2 mt-1.5">
                  {(['tp', 'sl'] as const).map((kind) => {
                    const leg = kind === 'tp' ? tp : sl;
                    const isEditing = editing?.instr === pos.instr && editing?.kind === kind;
                    return (
                      <div key={kind} className="flex items-center gap-1">
                        <span className={kind === 'tp' ? 'text-[#22c55e]' : 'text-[#ef4444]'}>{kind.toUpperCase()}</span>
                        {isEditing ? (
                          <>
                            <input autoFocus value={editVal} onChange={(e) => setEditVal(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && commitEdit()} className="bg-[#0b0e14] border border-[#2a313a] px-1 py-0.5 rounded w-16 text-right" />
                            <button onClick={commitEdit} className="px-1 rounded bg-[#1a1f26]">✓</button>
                          </>
                        ) : (
                          <button disabled={disabled} onClick={() => startEdit(pos.instr, kind, leg?.price)} className="font-mono text-[#9ca3af] underline decoration-dotted">
                            {leg?.price != null ? leg.price.toFixed(2) : 'set'}
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
                <div className="flex gap-1 mt-1.5">
                  <button disabled={disabled} onClick={() => onClose(pos.instr, 0.5)} className="flex-1 py-0.5 rounded bg-[#1a1f26] hover:bg-[#272d37]">Close ½</button>
                  <button disabled={disabled} onClick={() => onClose(pos.instr, 1)} className="flex-1 py-0.5 rounded bg-[#3f1c1c] text-[#ef4444] hover:bg-[#4f2424]">Close</button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {standalone.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-widest text-[#6b7280] mb-1 mt-1">Working Orders</div>
          <div className="space-y-0.5">
            {standalone.map((o, i) => (
              <div key={i} className="flex items-center justify-between text-[11px] font-mono">
                <span className="text-[#9ca3af]">{String(o.type).toUpperCase()} {o.side === 'long' ? 'BUY' : 'SELL'} ×{o.size} @ {o.price?.toFixed(2) ?? '—'}</span>
                <button disabled={disabled || o.id == null} onClick={() => o.id && onCancelOrder(String(o.id))} className="text-[#ef4444] underline">cancel</button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
