'use client';

interface ResourceBarsProps {
  tb: number;
  ip: number;
  currentR?: number;
  onPause?: () => void;
  onFF?: (mult: number) => void;
}

export function ResourceBars({ tb, ip, currentR = 1, onPause, onFF }: ResourceBarsProps) {
  const tbPct = Math.max(0, Math.min(100, tb));
  const ipDisplay = Math.floor(ip);

  return (
    <div className="panel p-3 flex flex-col gap-3">
      <div>
        <div className="flex items-center justify-between text-xs mb-1.5">
          <div className="flex items-center gap-2">
            <span className="font-medium text-[#eab308]">TB • Tempo Bar</span>
            <span className="text-[10px] text-[#9ca3af]">(R={currentR.toFixed(1)})</span>
          </div>
          <span className="font-mono tabular-nums">{tbPct.toFixed(0)}/100</span>
        </div>
        <div className="resource-bar">
          <div className="resource-fill" style={{ width: `${tbPct}%`, background: 'var(--tb-fill)' }} />
        </div>
        <div className="flex gap-1 mt-2">
          <button onClick={onPause} className="sabo-btn flex-1 py-1 text-xs rounded bg-[#1a1f26] hover:bg-[#272d37]">PAUSE (R=0)</button>
          {[2, 3, 5].map((m) => (<button key={m} onClick={() => onFF?.(m)} className="sabo-btn flex-1 py-1 text-xs rounded bg-[#1a1f26] hover:bg-[#272d37]">FF×{m}</button>))}
        </div>
        <div className="text-[10px] text-[#9ca3af] mt-1">Spend TB to control shared clock. Pause recharges faster.</div>
      </div>

      <div>
        <div className="flex items-center justify-between text-xs mb-1.5">
          <span className="font-medium text-[#3b82f6]">IP • Intel Points</span>
          <span className="font-mono tabular-nums">{ipDisplay}</span>
        </div>
        <div className="resource-bar">
          <div className="resource-fill" style={{ width: `${Math.min(100, ip / 1.2)}%`, background: 'var(--ip-fill)' }} />
        </div>
        <div className="text-[10px] text-[#9ca3af] mt-1">Spend IP on feeds, peeks, sabotage. Recharges slowly + from good PnL.</div>
      </div>
    </div>
  );
}
