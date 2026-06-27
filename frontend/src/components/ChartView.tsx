'use client';

import { useRef, useEffect } from 'react';
import { useReplayController, type ReplayController } from '../hooks/useReplayController';
import { DrawingLayer } from './DrawingLayer';

interface ChartViewProps {
  onControllerReady?: (ctrl: ReplayController) => void;
  R?: number;
  contested?: boolean;
  T?: number;
  paused?: boolean;
}

export function ChartView({ onControllerReady, R = 1, contested = false, T = 0, paused = false }: ChartViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const ctrl = useReplayController({ containerRef });
  const readyRef = useRef(false);

  useEffect(() => {
    // Controller methods are stable (useCallback); only hand it up once after mount.
    if (readyRef.current) return;
    readyRef.current = true;
    onControllerReady?.(ctrl);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const speedLabel = paused ? 'PAUSED' : `${R.toFixed(1)}×`;
  const speedColor = paused ? '#eab308' : R > 1 ? '#22c55e' : '#9ca3af';

  return (
    <div className="chart-container rounded relative">
      <div ref={containerRef} className="w-full" style={{ minHeight: 420 }} />
      <DrawingLayer ctrl={ctrl} containerRef={containerRef} />
      <div className="absolute top-2 left-2 flex items-center gap-2 bg-[#0a0c10]/85 px-2.5 py-1 rounded border border-[#2a313a]">
        <span className="text-[10px] uppercase tracking-widest text-[#6b7280]">Market Speed</span>
        <span className="text-sm font-semibold font-mono" style={{ color: speedColor }}>{speedLabel}</span>
        {contested && <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#ef4444]/15 text-[#ef4444] animate-pulse">CONTESTED</span>}
      </div>
      <div className="absolute top-2 right-2 bg-[#0a0c10]/85 px-2 py-1 rounded text-[10px] font-mono border border-[#2a313a] text-[#9ca3af]">
        Sim Day {Math.round(T)} • bars {ctrl.revealedCount}
      </div>
      <div className="px-2 pb-1 pt-1 text-[10px] text-[#6b7280] flex justify-between">
        <span>Normalized • P[0]=100 • bars revealed live by server (no future preload)</span>
        <span>streaming via series.update()</span>
      </div>
    </div>
  );
}
