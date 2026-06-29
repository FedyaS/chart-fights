'use client';

import { useCallback, useEffect, useRef } from 'react';
import type { ReplayController } from '../hooks/useReplayController';

// Visualizes the open position's entry + TP/SL as transparent zones on the chart,
// with thin draggable handle strips so TP/SL can be adjusted with the mouse.

export interface BracketModel {
  entry: number;
  side: 'long' | 'short';
  tp?: { id?: string; price: number };
  sl?: { id?: string; price: number };
}

interface BracketOverlayProps {
  ctrl: ReplayController;
  containerRef: React.RefObject<HTMLDivElement | null>;
  bracket: BracketModel | null;
  onAdjust: (kind: 'tp' | 'sl', price: number) => void;
}

const HEIGHT = 420;

export function BracketOverlay({ ctrl, containerRef, bracket, onAdjust }: BracketOverlayProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const tpHandleRef = useRef<HTMLDivElement>(null);
  const slHandleRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{ kind: 'tp' | 'sl'; price: number } | null>(null);
  const bracketRef = useRef<BracketModel | null>(bracket);
  bracketRef.current = bracket;

  const yOf = useCallback((price: number): number | null => {
    const s = ctrl.seriesRef.current;
    const y = s?.priceToCoordinate(price);
    return y == null ? null : y;
  }, [ctrl]);

  const priceOf = useCallback((y: number): number | null => {
    const s = ctrl.seriesRef.current;
    const p = s?.coordinateToPrice(y);
    return p == null ? null : Number(p);
  }, [ctrl]);

  const redraw = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    const w = container.clientWidth;
    const dpr = window.devicePixelRatio || 1;
    if (canvas.width !== w * dpr || canvas.height !== HEIGHT * dpr) {
      canvas.width = w * dpr; canvas.height = HEIGHT * dpr;
      canvas.style.width = `${w}px`; canvas.style.height = `${HEIGHT}px`;
    }
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, HEIGHT);

    const b = bracketRef.current;
    const drag = dragRef.current;
    const hide = (el: HTMLDivElement | null) => { if (el) el.style.display = 'none'; };
    if (!b || b.entry == null) { hide(tpHandleRef.current); hide(slHandleRef.current); return; }

    const yE = yOf(b.entry);
    if (yE == null) return;
    ctx.font = '10px ui-monospace, monospace';

    const drawLeg = (kind: 'tp' | 'sl', price: number, handle: HTMLDivElement | null) => {
      const live = drag && drag.kind === kind ? drag.price : price;
      const y = yOf(live);
      if (y == null) { hide(handle); return; }
      const isTp = kind === 'tp';
      const stroke = isTp ? '#22c55e' : '#ef4444';
      const fill = isTp ? 'rgba(34,197,94,0.10)' : 'rgba(239,68,68,0.10)';
      // transparent zone between entry and the leg
      ctx.fillStyle = fill;
      ctx.fillRect(0, Math.min(yE, y), w, Math.abs(y - yE));
      // the leg line
      ctx.strokeStyle = stroke; ctx.lineWidth = 1.5;
      ctx.setLineDash([6, 3]);
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
      ctx.setLineDash([]);
      // label
      const pct = b.entry ? ((live - b.entry) / b.entry) * 100 : 0;
      const label = `${kind.toUpperCase()} ${live.toFixed(2)} (${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%)`;
      ctx.fillStyle = '#0a0c10'; ctx.fillRect(6, y - 13, ctx.measureText(label).width + 8, 13);
      ctx.fillStyle = stroke; ctx.fillText(label, 10, y - 3);
      // position the draggable handle strip
      if (handle) { handle.style.display = 'block'; handle.style.top = `${y - 4}px`; }
    };

    // entry line
    ctx.strokeStyle = '#6b7280'; ctx.lineWidth = 1; ctx.setLineDash([2, 3]);
    ctx.beginPath(); ctx.moveTo(0, yE); ctx.lineTo(w, yE); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = '#9ca3af'; ctx.fillText(`Entry ${b.entry.toFixed(2)}`, 10, yE + 11);

    if (b.tp) drawLeg('tp', b.tp.price, tpHandleRef.current); else hide(tpHandleRef.current);
    if (b.sl) drawLeg('sl', b.sl.price, slHandleRef.current); else hide(slHandleRef.current);
  }, [containerRef, yOf]);

  useEffect(() => {
    const ts = ctrl.chartRef.current?.timeScale();
    let raf = 0;
    const schedule = () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(redraw); };
    ts?.subscribeVisibleLogicalRangeChange(schedule);
    window.addEventListener('resize', schedule);
    const id = window.setInterval(schedule, 200);
    schedule();
    return () => {
      cancelAnimationFrame(raf); window.clearInterval(id);
      window.removeEventListener('resize', schedule);
      try { ts?.unsubscribeVisibleLogicalRangeChange(schedule); } catch {}
    };
  }, [ctrl, redraw]);

  const makeHandlers = (kind: 'tp' | 'sl') => ({
    onPointerDown: (e: React.PointerEvent) => {
      const b = bracketRef.current;
      const leg = kind === 'tp' ? b?.tp : b?.sl;
      if (!leg) return;
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
      dragRef.current = { kind, price: leg.price };
      e.preventDefault();
    },
    onPointerMove: (e: React.PointerEvent) => {
      if (!dragRef.current || dragRef.current.kind !== kind) return;
      const rect = canvasRef.current!.getBoundingClientRect();
      const p = priceOf(e.clientY - rect.top);
      if (p != null && p > 0) { dragRef.current.price = p; redraw(); }
    },
    onPointerUp: (e: React.PointerEvent) => {
      const d = dragRef.current;
      dragRef.current = null;
      try { (e.target as HTMLElement).releasePointerCapture(e.pointerId); } catch {}
      if (d && d.kind === kind) onAdjust(kind, +d.price.toFixed(2));
    },
  });

  return (
    <>
      <canvas ref={canvasRef} className="absolute top-0 left-0" style={{ height: HEIGHT, pointerEvents: 'none', zIndex: 4 }} />
      <div ref={tpHandleRef} {...makeHandlers('tp')} title="drag to adjust take-profit"
        className="absolute left-0 right-0" style={{ height: 9, display: 'none', cursor: 'ns-resize', zIndex: 7 }} />
      <div ref={slHandleRef} {...makeHandlers('sl')} title="drag to adjust stop-loss"
        className="absolute left-0 right-0" style={{ height: 9, display: 'none', cursor: 'ns-resize', zIndex: 7 }} />
    </>
  );
}
