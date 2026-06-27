'use client';

import type { TempoLevel } from '../types';

interface ResourceBarsProps {
  tb: number; // 0..100
  ip: number;
  R: number;
  contested: boolean;
  myLevel: TempoLevel;
  onTempo: (level: TempoLevel) => void;
}

const FF_LEVELS: { level: TempoLevel; label: string; cost: string }[] = [
  { level: 'ff2', label: 'FF×2', cost: '-2/s' },
  { level: 'ff3', label: 'FF×3', cost: '-5/s' },
  { level: 'ff5', label: 'FF×5', cost: '-12/s' },
];

export function ResourceBars({ tb, ip, R, contested, myLevel, onTempo }: ResourceBarsProps) {
  const tbPct = Math.max(0, Math.min(100, tb));
  const ipDisplay = Math.floor(ip);

  const btn = (active: boolean) =>
    `flex-1 py-1 text-xs rounded border transition ${
      active ? 'border-[#eab308] bg-[#eab308]/15 text-[#eab308]' : 'border-[#2a313a] bg-[#1a1f26] hover:bg-[#272d37]'
    }`;

  return (
    <div className="panel p-3 flex flex-col gap-3">
      <div>
        <div className="flex items-center justify-between text-xs mb-1.5">
          <div className="flex items-center gap-2">
            <span className="font-medium text-[#eab308]">TB · Tempo Bar</span>
            <span className="text-[10px] text-[#9ca3af]">R={R.toFixed(1)}×{contested ? ' · contested' : ''}</span>
          </div>
          <span className="font-mono tabular-nums">{tbPct.toFixed(0)}/100</span>
        </div>
        <div className="resource-bar">
          <div className="resource-fill" style={{ width: `${tbPct}%`, background: 'var(--tb-fill)' }} />
        </div>
        <div className="flex gap-1 mt-2">
          <button onClick={() => onTempo('pause')} className={btn(myLevel === 'pause')}>PAUSE</button>
          <button onClick={() => onTempo('base')} className={btn(myLevel === 'base')}>1×</button>
          {FF_LEVELS.map((f) => (
            <button key={f.level} onClick={() => onTempo(f.level)} className={btn(myLevel === f.level)} title={`Consumes ${f.cost} TB`}>
              {f.label}
            </button>
          ))}
        </div>
        <div className="text-[10px] text-[#9ca3af] mt-1">Contested shared clock. Pause forces R=0 + recharges +4/s. FF = max wins; all payers pay.</div>
      </div>

      <div>
        <div className="flex items-center justify-between text-xs mb-1.5">
          <span className="font-medium text-[#3b82f6]">IP · Intel Points</span>
          <span className="font-mono tabular-nums">{ipDisplay}</span>
        </div>
        <div className="resource-bar">
          <div className="resource-fill" style={{ width: `${Math.min(100, (ip / 200) * 100)}%`, background: 'var(--ip-fill)' }} />
        </div>
        <div className="text-[10px] text-[#9ca3af] mt-1">+0.5/s passive, +10% realized profit. Soft cap 200. Fund peeks + sabotage.</div>
      </div>
    </div>
  );
}
