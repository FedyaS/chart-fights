'use client';

import { useRef, useEffect, useCallback, useState } from 'react';
import {
  createChart,
  CandlestickSeries,
  createSeriesMarkers,
  LineStyle,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type SeriesMarker,
  type LogicalRange,
  type Time,
} from 'lightweight-charts';
import type { Bar } from '../types';

interface UseReplayControllerProps {
  containerRef: React.RefObject<HTMLDivElement | null>;
  initialBars?: Bar[];
  // WS integration support (GDD task-007): drive from server deltas
  externalT?: number; // authoritative current T from backend delta/snapshot
  externalBars?: Bar[]; // optional override bars
}

interface UseReplayControllerReturn {
  isPlaying: boolean;
  speed: number;
  currentIndex: number;
  play: () => void;
  pause: () => void;
  setSpeed: (s: number) => void;
  seekTo: (idx: number) => void;
  addPlayerMarker: (barIdx: number, isBuy: boolean, player?: 'p1' | 'p2') => void;
  addSaboMarker: (barIdx: number, effect: string) => void;
  addPriceLine: (price: number, title: string, color: string) => void;
  clearPriceLines: () => void;
  reset: () => void;
  currentBar: Bar | null;
  chartRef: React.MutableRefObject<IChartApi | null>;
  seriesRef: React.MutableRefObject<ISeriesApi<'Candlestick'> | null>;
  // WS-driven update for real deltas: series.update + set range from server T/current bar (GDD flow)
  updateFromServer: (barOrT: Bar | number, maybeBar?: Bar) => void;
}

const BASE_INTERVAL_MS = 800;

export function useReplayController({ containerRef, initialBars = [], externalT, externalBars }: UseReplayControllerProps): UseReplayControllerReturn {
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const priceLinesRef = useRef<any[]>([]);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeedState] = useState(1);
  const [currentIndex, setCurrentIndex] = useState(0);
  const effectiveBars = externalBars && externalBars.length > 0 ? externalBars : initialBars;
  const [bars, setBars] = useState<Bar[]>(effectiveBars);

  const currentBar = bars[currentIndex] ?? null;

  // WS driven: use series.update(bar) + setVisibleLogicalRange for server T (per task-007, LW realtime + replay patterns)
  const updateFromServer = useCallback((barOrT: Bar | number, maybeBar?: Bar) => {
    const series = seriesRef.current;
    const chart = chartRef.current;
    if (!series || !chart || bars.length === 0) return;

    let idx = typeof barOrT === 'number' ? Math.floor(barOrT) : barOrT.time;
    let bar = typeof barOrT === 'number' ? (maybeBar || bars[Math.min(idx, bars.length-1)]) : barOrT;
    if (!bar) return;

    idx = Math.min(Math.max(0, idx), bars.length - 1);

    // use UPDATE not setData for streaming deltas
    series.update({
      time: bar.time as Time,
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
    } as CandlestickData);

    // follow server T with logical range
    const windowSize = 22;
    const from = Math.max(0, idx - windowSize);
    chart.timeScale().setVisibleLogicalRange({ from, to: idx + 5 } as LogicalRange);

    setCurrentIndex(idx);
  }, [bars]);

  const clearTimer = useCallback(() => {
    if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }
  }, []);

  const initChart = useCallback((data: Bar[]) => {
    const container = containerRef.current;
    if (!container) return;

    if (chartRef.current) { try { chartRef.current.remove(); } catch {} chartRef.current = null; seriesRef.current = null; priceLinesRef.current = []; }

    const chart = createChart(container, {
      width: container.clientWidth, height: 420,
      layout: { background: { color: '#0b0e14' }, textColor: '#9ca3af' },
      grid: { vertLines: { color: '#1f252e' }, horzLines: { color: '#1f252e' } },
      timeScale: { borderColor: '#2a313a', rightOffset: 5, barSpacing: 6 },
      rightPriceScale: { borderColor: '#2a313a', scaleMargins: { top: 0.1, bottom: 0.1 } },
    });

    const series = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e', downColor: '#ef4444',
      borderUpColor: '#22c55e', borderDownColor: '#ef4444',
      wickUpColor: '#22c55e', wickDownColor: '#ef4444',
    }) as ISeriesApi<'Candlestick'>;

    chartRef.current = chart; seriesRef.current = series;

    if (data.length > 0) {
      series.setData(data.map(b => ({ time: b.time as Time, open: b.open, high: b.high, low: b.low, close: b.close })));
      chart.timeScale().setVisibleLogicalRange({ from: -1, to: Math.min(22, data.length) } as LogicalRange);
    }

    const handleResize = () => { if (chartRef.current) chartRef.current.resize(container.clientWidth, 420); };
    window.addEventListener('resize', handleResize);
    (chart as any)._resizeCleanup = () => window.removeEventListener('resize', handleResize);
  }, [containerRef]);

  useEffect(() => {
    if (initialBars.length > 0) {
      setBars(initialBars); setCurrentIndex(0); setIsPlaying(false); clearTimer(); initChart(initialBars);
    }
  }, [initialBars, initChart, clearTimer]);

  const advanceOne = useCallback(() => {
    const series = seriesRef.current; if (!series || bars.length === 0) return;
    const nextIdx = Math.min(currentIndex + 1, bars.length - 1);
    if (nextIdx === currentIndex) { setIsPlaying(false); clearTimer(); return; }
    const bar = bars[nextIdx];
    series.update({ time: bar.time as Time, open: bar.open, high: bar.high, low: bar.low, close: bar.close } as CandlestickData);
    const chart = chartRef.current;
    if (chart) {
      const from = Math.max(0, nextIdx - 18); chart.timeScale().setVisibleLogicalRange({ from, to: nextIdx + 4 } as LogicalRange);
    }
    setCurrentIndex(nextIdx);
  }, [bars, currentIndex, clearTimer]);

  useEffect(() => {
    clearTimer();
    if (!isPlaying || speed <= 0 || bars.length === 0) return;
    const ms = Math.max(120, Math.floor(BASE_INTERVAL_MS / speed));
    intervalRef.current = setInterval(advanceOne, ms);
    return clearTimer;
  }, [isPlaying, speed, bars.length, advanceOne, clearTimer]);

  const play = useCallback(() => { if (currentIndex >= bars.length - 1) setCurrentIndex(0); setIsPlaying(true); }, [currentIndex, bars.length]);
  const pause = useCallback(() => { setIsPlaying(false); clearTimer(); }, [clearTimer]);
  const setSpeed = useCallback((s: number) => setSpeedState(Math.max(1, Math.min(5, Math.floor(s)))), []);
  const seekTo = useCallback((idx: number) => {
    const c = Math.max(0, Math.min(idx, bars.length - 1)); setCurrentIndex(c); setIsPlaying(false); clearTimer();
    const s = seriesRef.current; const ch = chartRef.current;
    if (s && ch && bars.length) {
      s.setData(bars.slice(0, c + 1).map(b => ({ time: b.time as Time, open: b.open, high: b.high, low: b.low, close: b.close })));
      ch.timeScale().setVisibleLogicalRange({ from: Math.max(0, c - 18), to: c + 4 } as LogicalRange);
    }
  }, [bars, clearTimer]);

  const addPlayerMarker = useCallback((barIdx: number, isBuy: boolean, player: 'p1' | 'p2' = 'p1') => {
    const series = seriesRef.current; if (!series || !bars[barIdx]) return;
    const color = player === 'p1' ? (isBuy ? '#22c55e' : '#ef4444') : (isBuy ? '#3b82f6' : '#f97316');
    const m: SeriesMarker<Time> = { time: bars[barIdx].time as Time, position: isBuy ? 'belowBar' : 'aboveBar', color, shape: isBuy ? 'arrowUp' : 'arrowDown', text: `${player.toUpperCase()}:${isBuy ? 'BUY' : 'SELL'}`, size: 2 };
    try { createSeriesMarkers(series, [m] as any); } catch { (series as any).setMarkers?.([m]); }
  }, [bars]);

  const addSaboMarker = useCallback((barIdx: number, effect: string) => {
    const series = seriesRef.current; if (!series || !bars[barIdx]) return;
    const m: SeriesMarker<Time> = { time: bars[barIdx].time as Time, position: 'inBar', color: '#a855f7', shape: 'square', text: `SABO:${effect}`, size: 1.5 };
    try { createSeriesMarkers(series, [m] as any); } catch { (series as any).setMarkers?.([m]); }
  }, [bars]);

  const addPriceLine = useCallback((price: number, title: string, color: string) => {
    const series = seriesRef.current; if (!series) return;
    priceLinesRef.current.push(series.createPriceLine({ price, color, lineWidth: 2, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title }));
  }, []);
  const clearPriceLines = useCallback(() => {
    const series = seriesRef.current;
    priceLinesRef.current.forEach(pl => { try { series?.removePriceLine(pl); } catch {} });
    priceLinesRef.current = [];
  }, []);

  const reset = useCallback(() => {
    setIsPlaying(false); clearTimer(); setCurrentIndex(0);
    if (seriesRef.current && bars.length) {
      seriesRef.current.setData(bars.map(b => ({ time: b.time as Time, open: b.open, high: b.high, low: b.low, close: b.close })));
      chartRef.current?.timeScale().setVisibleLogicalRange({ from: -1, to: 22 } as LogicalRange);
    }
    clearPriceLines();
  }, [bars, clearTimer, clearPriceLines]);

  useEffect(() => () => { clearTimer(); if (chartRef.current) { try { (chartRef.current as any).remove(); } catch {} } }, [clearTimer]);

  // WS deltas: follow external authoritative T (from snapshot/delta) - set range + update current bar using series.update
  useEffect(() => {
    if (typeof externalT === 'number' && bars.length > 0) {
      const idx = Math.min(Math.max(0, Math.floor(externalT)), bars.length - 1);
      const bar = bars[idx];
      const series = seriesRef.current;
      const chart = chartRef.current;
      if (bar && series && chart) {
        series.update({ time: bar.time as Time, open: bar.open, high: bar.high, low: bar.low, close: bar.close } as CandlestickData);
        const from = Math.max(0, idx - 20);
        chart.timeScale().setVisibleLogicalRange({ from, to: idx + 5 } as LogicalRange);
        setCurrentIndex(idx);
      }
    }
  }, [externalT, bars]);

  return { isPlaying, speed, currentIndex, play, pause, setSpeed, seekTo, addPlayerMarker, addSaboMarker, addPriceLine, clearPriceLines, reset, currentBar, chartRef, seriesRef, updateFromServer };
}
