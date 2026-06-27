'use client';

import type { LogEvent } from '../types';

interface EventLogProps {
  events: LogEvent[];
}

const TYPE_COLOR: Record<LogEvent['type'], string> = {
  order: '#22c55e',
  fill: '#22c55e',
  sabo: '#a855f7',
  news: '#eab308',
  peek: '#3b82f6',
  tb: '#eab308',
  voice: '#06b6d4',
  info: '#6b7280',
};

export function EventLog({ events }: EventLogProps) {
  return (
    <div className="panel p-2 flex flex-col h-[170px] overflow-hidden">
      <div className="text-xs font-medium px-1 pb-1 border-b border-[#2a313a]">EVENT LOG</div>
      <div className="flex-1 overflow-y-auto text-[11px] p-1 space-y-0.5 font-mono">
        {events.length === 0 && <div className="text-[#6b7280]">No events yet. Fills, sabotage, and news appear here.</div>}
        {events.slice().reverse().map((e, i) => (
          <div key={i} className="log-line text-[#d1d5db]">
            <span className="text-[#6b7280]">D{e.t}</span>{' '}
            <span style={{ color: TYPE_COLOR[e.type] ?? '#6b7280' }}>[{e.type}]</span>{' '}
            {e.message}
          </div>
        ))}
      </div>
    </div>
  );
}
