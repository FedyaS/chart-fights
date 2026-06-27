'use client';

import { useEffect, useRef, useState } from 'react';

export interface Ability {
  ability: string;
  label: string;
  desc: string;
  cost: number;
  cooldown: number; // real seconds
}

// Costs + cooldowns per task-003 / game-mechanics-spec §7.
export const ABILITIES: Ability[] = [
  { ability: 'delete_sl', label: 'Delete Opp SLs', desc: 'Remove their stop losses', cost: 30, cooldown: 60 },
  { ability: 'widen_spread', label: 'Widen Spreads', desc: '0.4–0.8% adverse fills 15s', cost: 25, cooldown: 45 },
  { ability: 'fake_news', label: 'Inject Fake News', desc: 'Misleading headline (victim only)', cost: 40, cooldown: 90 },
  { ability: 'peek', label: 'Peek Headline', desc: 'Reveal real news at current T', cost: 60, cooldown: 120 },
];

interface SaboPanelProps {
  ip: number;
  onCast: (ability: Ability) => void;
}

export function SaboPanel({ ip, onCast }: SaboPanelProps) {
  // local cooldown timers (real wall time) for UI gating; server is authoritative.
  const [now, setNow] = useState(() => Date.now());
  const readyAtRef = useRef<Record<string, number>>({});

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, []);

  const cast = (a: Ability) => {
    readyAtRef.current[a.ability] = Date.now() + a.cooldown * 1000;
    onCast(a);
  };

  return (
    <div className="panel p-3">
      <div className="text-xs font-medium mb-2 flex items-center gap-2">SABOTAGE <span className="text-[#a855f7]">(IP spend)</span></div>
      <div className="grid grid-cols-2 gap-1.5">
        {ABILITIES.map((a) => {
          const remaining = Math.max(0, (readyAtRef.current[a.ability] ?? 0) - now);
          const onCd = remaining > 0;
          const canAfford = ip >= a.cost;
          const disabled = onCd || !canAfford;
          return (
            <button
              key={a.ability}
              disabled={disabled}
              onClick={() => cast(a)}
              className={`sabo-btn text-left px-2 py-1.5 rounded text-xs ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
              title={`${a.desc} • ${a.cost} IP • ${a.cooldown}s cd`}
            >
              <div className="font-medium flex items-center justify-between">
                <span>{a.label}</span>
                {onCd && <span className="text-[10px] text-[#a855f7] font-mono">{Math.ceil(remaining / 1000)}s</span>}
              </div>
              <div className="text-[10px] text-[#9ca3af]">{a.desc}</div>
              <div className={`text-[10px] ${canAfford ? 'text-[#3b82f6]' : 'text-[#ef4444]'}`}>{a.cost} IP</div>
            </button>
          );
        })}
      </div>
      <div className="text-[10px] text-[#9ca3af] mt-2">Server-authoritative. Victim is always notified with a timestamp.</div>
    </div>
  );
}
