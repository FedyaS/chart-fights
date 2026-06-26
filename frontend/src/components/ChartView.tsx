'use client';

import React, { useRef } from 'react';
import { useReplayController } from '../hooks/useReplayController';
import type { Bar } from '../types';

interface ChartViewProps {
  bars: Bar[];
  onControllerReady?: (ctrl: ReturnType<typeof useReplayController>) => void;
  externalMarkers?: { barIdx: number; isBuy: boolean; player?: 'p1' | 'p2' }[];
  externalSabo?: { barIdx: number; effect: string }[];
  onIndexChange?: (idx: number) => void;
  // WS support: pass serverT from deltas to ReplayController for series.update + range set
  serverT?: number;
}

export function ChartView({ bars, onControllerReady, externalMarkers, externalSabo, onIndexChange, serverT }: ChartViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  const ctrl = useReplayController({ containerRef, initialBars: bars, externalT: serverT });

  React.useEffect(() => {
    onControllerReady?.(ctrl);
  }, [ctrl, onControllerReady]);

  React.useEffect(() => {
    if (externalMarkers && externalMarkers.length > 0) {
      externalMarkers.forEach((m) => ctrl.addPlayerMarker(m.barIdx, m.isBuy, m.player));
    }
  }, [externalMarkers]);

  React.useEffect(() => {
    if (externalSabo && externalSabo.length > 0) {
      externalSabo.forEach((s) => ctrl.addSaboMarker(s.barIdx, s.effect));
    }
  }, [externalSabo]);

  React.useEffect(() => {
    onIndexChange?.(ctrl.currentIndex);
  }, [ctrl.currentIndex, onIndexChange]);

  return (
    <div className="chart-container rounded relative">
      <div ref={containerRef} className="w-full" style={{ minHeight: 420 }} />
      <div className="absolute top-2 right-2 bg-[#0a0c10]/80 px-2 py-1 rounded text-[10px] font-mono border border-[#2a313a] text-[#9ca3af]">
        T={ctrl.currentIndex} / {bars.length} • R={ctrl.speed}x {ctrl.isPlaying ? '▶' : '⏸'}
      </div>
      <div className="px-2 pb-1 text-[10px] text-[#6b7280] flex justify-between">
        <span>Normalized • % returns only (P[0]=100). Logical replay head.</span>
        <button onClick={ctrl.reset} className="underline hover:text-[#9ca3af]">RESET VIEW</button>
      </div>
    </div>
  );
}
