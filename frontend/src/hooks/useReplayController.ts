'use client';

import { useRef, useEffect, useCallback, useState } from 'react';
import {
  createChart,
  CandlestickSeries,
  createSeriesMarkers,
  LineStyle,
  type IChartApi,
  type ISeriesApi,
  type IPriceLine,
  type ISeriesMarkersPluginApi,
  type CandlestickData,
  type SeriesMarker,
  type LogicalRange,
  type Time,
} from 'lightweight-charts';
import type { Bar } from '../types';

interface UseReplayControllerProps {
  containerRef: React.RefObject<HTMLDivElement | null>;
}

export interface ReplayController {
  // Streaming API (anti-cheat: bars are only revealed as the server emits them).
  pushBar: (bar: Bar) => void;
  setHistory: (bars: Bar[]) => void;
  reset: () => void;
  revealedCount: number;
  currentIndex: number; // compat: last revealed bar index
  lastBar: Bar | null;
  // Overlays
  addFillMarker: (bar: Bar, side: 'long' | 'short' | string, player: string, you: string, label?: string) => void;
  addSaboMarker: (bar: Bar, effect: string) => void;
  clearMarkers: () => void;
  addPriceLine: (price: number, title: string, color: string, id?: string) => void;
  removePriceLine: (id: string) => void;
  clearPriceLines: () => void;
  // Refs (for advanced callers)
  chartRef: React.MutableRefObject<IChartApi | null>;
  seriesRef: React.MutableRefObject<ISeriesApi<'Candlestick'> | null>;
}

const WINDOW = 40; // number of bars kept visible behind the live edge
const RIGHT_OFFSET = 4;

export function useReplayController({ containerRef }: UseReplayControllerProps): ReplayController {
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const markersApiRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null);
  const markersRef = useRef<SeriesMarker<Time>[]>([]);
  const priceLineMapRef = useRef<Map<string, IPriceLine>>(new Map());
  const lastTimeRef = useRef<number>(-Infinity);

  const [revealedCount, setRevealedCount] = useState(0);
  const [lastBar, setLastBar] = useState<Bar | null>(null);

  const followRange = useCallback((idx: number) => {
    const chart = chartRef.current;
    if (!chart) return;
    const from = Math.max(0, idx - WINDOW);
    chart.timeScale().setVisibleLogicalRange({ from, to: idx + RIGHT_OFFSET } as LogicalRange);
  }, []);

  // Append (or replace the in-progress) candle revealed by the server.
  const pushBar = useCallback((bar: Bar) => {
    const series = seriesRef.current;
    if (!series || !bar) return;
    series.update({
      time: bar.time as Time,
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
    } as CandlestickData);

    const isNew = bar.time > lastTimeRef.current;
    lastTimeRef.current = bar.time;
    setLastBar(bar);
    setRevealedCount((c) => {
      const next = isNew ? c + 1 : c;
      followRange(Math.max(0, next - 1));
      return next;
    });
  }, [followRange]);

  // Used for offline replay seeding or reconnect with revealed history.
  const setHistory = useCallback((bars: Bar[]) => {
    const series = seriesRef.current;
    const chart = chartRef.current;
    if (!series || bars.length === 0) return;
    series.setData(
      bars.map((b) => ({ time: b.time as Time, open: b.open, high: b.high, low: b.low, close: b.close })),
    );
    lastTimeRef.current = bars[bars.length - 1].time;
    setLastBar(bars[bars.length - 1]);
    setRevealedCount(bars.length);
    chart?.timeScale().setVisibleLogicalRange({ from: Math.max(0, bars.length - WINDOW), to: bars.length + RIGHT_OFFSET } as LogicalRange);
  }, []);

  const ensureMarkersApi = useCallback(() => {
    const series = seriesRef.current;
    if (!series) return null;
    if (!markersApiRef.current) {
      markersApiRef.current = createSeriesMarkers(series, []);
    }
    return markersApiRef.current;
  }, []);

  const commitMarkers = useCallback(() => {
    const api = ensureMarkersApi();
    api?.setMarkers([...markersRef.current]);
  }, [ensureMarkersApi]);

  const addFillMarker = useCallback((bar: Bar, side: string, player: string, you: string, label?: string) => {
    if (!bar) return;
    const isBuy = side === 'long' || side === 'buy';
    const isMe = player === you;
    const color = isMe ? (isBuy ? '#22c55e' : '#ef4444') : (isBuy ? '#3b82f6' : '#f97316');
    const m: SeriesMarker<Time> = {
      time: bar.time as Time,
      position: isBuy ? 'belowBar' : 'aboveBar',
      color,
      shape: isBuy ? 'arrowUp' : 'arrowDown',
      text: label ?? `${isMe ? 'YOU' : 'OPP'} ${isBuy ? 'BUY' : 'SELL'}`,
    };
    markersRef.current = [...markersRef.current, m].slice(-60);
    commitMarkers();
  }, [commitMarkers]);

  const addSaboMarker = useCallback((bar: Bar, effect: string) => {
    if (!bar) return;
    const m: SeriesMarker<Time> = {
      time: bar.time as Time,
      position: 'inBar',
      color: '#a855f7',
      shape: 'square',
      text: `SABO:${effect}`,
    };
    markersRef.current = [...markersRef.current, m].slice(-60);
    commitMarkers();
  }, [commitMarkers]);

  const clearMarkers = useCallback(() => {
    markersRef.current = [];
    markersApiRef.current?.setMarkers([]);
  }, []);

  const addPriceLine = useCallback((price: number, title: string, color: string, id?: string) => {
    const series = seriesRef.current;
    if (!series) return;
    const key = id ?? `${title}:${price.toFixed(2)}`;
    const existing = priceLineMapRef.current.get(key);
    if (existing) {
      existing.applyOptions({ price, color, title });
      return;
    }
    const pl = series.createPriceLine({ price, color, lineWidth: 2, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title });
    priceLineMapRef.current.set(key, pl);
  }, []);

  const removePriceLine = useCallback((id: string) => {
    const series = seriesRef.current;
    const pl = priceLineMapRef.current.get(id);
    if (pl && series) {
      try { series.removePriceLine(pl); } catch {}
      priceLineMapRef.current.delete(id);
    }
  }, []);

  const clearPriceLines = useCallback(() => {
    const series = seriesRef.current;
    priceLineMapRef.current.forEach((pl) => { try { series?.removePriceLine(pl); } catch {} });
    priceLineMapRef.current.clear();
  }, []);

  const reset = useCallback(() => {
    const series = seriesRef.current;
    clearMarkers();
    clearPriceLines();
    try { series?.setData([]); } catch {}
    lastTimeRef.current = -Infinity;
    setRevealedCount(0);
    setLastBar(null);
  }, [clearMarkers, clearPriceLines]);

  // Create the chart once.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    let removed = false;

    const chart = createChart(container, {
      width: container.clientWidth,
      height: 420,
      layout: { background: { color: '#0b0e14' }, textColor: '#9ca3af' },
      grid: { vertLines: { color: '#1f252e' }, horzLines: { color: '#1f252e' } },
      timeScale: {
        borderColor: '#2a313a',
        rightOffset: RIGHT_OFFSET,
        barSpacing: 8,
        tickMarkFormatter: (time: Time) => `Day ${Math.round(Number(time))}`,
      },
      localization: {
        timeFormatter: (time: Time) => `Sim Day ${Math.round(Number(time))}`,
      },
      rightPriceScale: { borderColor: '#2a313a', scaleMargins: { top: 0.1, bottom: 0.1 } },
    });

    const series = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e', downColor: '#ef4444',
      borderUpColor: '#22c55e', borderDownColor: '#ef4444',
      wickUpColor: '#22c55e', wickDownColor: '#ef4444',
    }) as ISeriesApi<'Candlestick'>;

    chartRef.current = chart;
    seriesRef.current = series;

    const handleResize = () => {
      if (!removed && chartRef.current) chartRef.current.resize(container.clientWidth, 420);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      removed = true;
      window.removeEventListener('resize', handleResize);
      try { chart.remove(); } catch {}
      chartRef.current = null;
      seriesRef.current = null;
      markersApiRef.current = null;
      markersRef.current = [];
      priceLineMapRef.current.clear();
      lastTimeRef.current = -Infinity;
    };
  }, [containerRef]);

  return {
    pushBar,
    setHistory,
    reset,
    revealedCount,
    currentIndex: Math.max(0, revealedCount - 1),
    lastBar,
    addFillMarker,
    addSaboMarker,
    clearMarkers,
    addPriceLine,
    removePriceLine,
    clearPriceLines,
    chartRef,
    seriesRef,
  };
}
