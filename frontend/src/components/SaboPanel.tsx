'use client';

interface SaboPanelProps {
  ip: number;
  onSabo: (action: string, cost: number) => void;
}

const SABOS = [
  { key: 'del_sl', label: 'Delete Opp SL', desc: 'Remove their stop', cost: 18 },
  { key: 'fake_news', label: 'Inject Fake News', desc: 'Misleading headline to opp only', cost: 25 },
  { key: 'widen_spread', label: 'Widen Spreads', desc: '1m slip for opp trades', cost: 12 },
  { key: 'jam_feed', label: 'Jam Data Feed', desc: 'Delay opp chart 4 bars', cost: 30 },
];

export function SaboPanel({ ip, onSabo }: SaboPanelProps) {
  return (
    <div className="panel p-3">
      <div className="text-xs font-medium mb-2 flex items-center gap-2">SABOTAGE <span className="text-[#a855f7]">(IP spend)</span></div>
      <div className="grid grid-cols-2 gap-1.5">
        {SABOS.map((s) => {
          const can = ip >= s.cost;
          return (
            <button key={s.key} disabled={!can} onClick={() => onSabo(s.key, s.cost)} className={`sabo-btn text-left px-2 py-1.5 rounded text-xs ${can ? '' : 'opacity-50 cursor-not-allowed'}`} title={`${s.desc} • costs ${s.cost} IP`}>
              <div className="font-medium">{s.label}</div>
              <div className="text-[10px] text-[#9ca3af]">{s.desc} • {s.cost}IP</div>
            </button>
          );
        })}
      </div>
      <div className="text-[10px] text-[#9ca3af] mt-2">Psych warfare. Opponent sees effect (or not). Log only in MVP.</div>
    </div>
  );
}
