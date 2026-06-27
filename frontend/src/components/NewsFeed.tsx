'use client';

import type { NewsItem } from '../types';

interface NewsFeedProps {
  items: NewsItem[];
}

const sentimentColor: Record<string, string> = {
  bullish: '#22c55e',
  bearish: '#ef4444',
  neutral: '#9ca3af',
};

export function NewsFeed({ items }: NewsFeedProps) {
  const recent = items.slice(-40).reverse();
  return (
    <div className="panel p-3 flex flex-col gap-2">
      <div className="text-xs font-medium">NEWS WIRE</div>
      {recent.length === 0 ? (
        <div className="text-[11px] text-[#6b7280]">No headlines yet — they print as days advance.</div>
      ) : (
        <div className="space-y-1 max-h-44 overflow-y-auto pr-1">
          {recent.map((n, i) => {
            const color = sentimentColor[n.sentiment ?? 'neutral'] ?? '#9ca3af';
            const isCal = n.kind === 'calendar';
            return (
              <div key={i} className="text-[11px] leading-snug">
                <span className="text-[#6b7280] font-mono mr-1">D{Math.round(n.t)}</span>
                {isCal && <span className="text-[10px] px-1 py-0.5 rounded bg-[#1a1f26] text-[#eab308] mr-1">{n.name ?? 'DATA'}</span>}
                <span style={{ color }}>{n.title}</span>
                {isCal && n.actual != null && (
                  <span className="text-[10px] text-[#9ca3af] ml-1 font-mono">
                    act {n.actual}{n.forecast != null ? ` vs fcst ${n.forecast}` : ''}
                    {n.surprise != null && (
                      <span style={{ color: n.surprise > 0 ? '#ef4444' : n.surprise < 0 ? '#22c55e' : '#9ca3af' }}>
                        {' '}{n.surprise > 0 ? '▲' : n.surprise < 0 ? '▼' : '·'}
                      </span>
                    )}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
