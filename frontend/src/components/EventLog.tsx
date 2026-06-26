'use client';

import type { LogEvent } from '../types';

interface EventLogProps {
  events: LogEvent[];
}

export function EventLog({ events }: EventLogProps) {
  return (
    <div className="panel p-2 flex flex-col h-[138px] overflow-hidden">
      <div className="text-xs font-medium px-1 pb-1 border-b border-[#2a313a]">EVENT LOG (stubs)</div>
      <div className="flex-1 overflow-y-auto text-[11px] p-1 space-y-0.5 font-mono">
        {events.length === 0 && <div className="text-[#9ca3af]">No events yet. Actions will log here.</div>}
        {events.slice().reverse().map((e, i) => (
          <div key={i} className="log-line text-[#d1d5db]">
            <span className="text-[#6b7280]">T{e.t}</span> [{e.type}] {e.message}
          </div>
        ))}
      </div>
    </div>
  );
}
