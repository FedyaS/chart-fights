'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type { ReplayController } from '../hooks/useReplayController';

// Custom drawing tools over lightweight-charts (which has none built in).
// Anchors are stored in DATA space ({logical bar index, price}) and converted to
// pixels on every redraw, so they track pan / zoom / live bar appends.

type Tool = 'cursor' | 'trend' | 'hline' | 'box' | 'fib' | 'ruler';
interface Anchor { logical: number; price: number }
interface Drawing { id: number; tool: Tool; a: Anchor; b?: Anchor }

const CHART_HEIGHT = 420;
const FIB_LEVELS = [0, 0.236, 0.382, 0.5, 0.618, 1];
const TOOL_COLOR: Record<Tool, string> = {
  cursor: '#9ca3af', trend: '#3b82f6', hline: '#eab308', box: '#a855f7', fib: '#06b6d4', ruler: '#f97316',
};

interface DrawingLayerProps {
  ctrl: ReplayController;
  containerRef: React.RefObject<HTMLDivElement | null>;
}

export function DrawingLayer({ ctrl, containerRef }: DrawingLayerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [tool, setTool] = useState<Tool>('cursor');
  const drawingsRef = useRef<Drawing[]>([]);
  const pendingRef = useRef<Anchor | null>(null);
  const hoverRef = useRef<Anchor | null>(null);
  const idRef = useRef(1);
  const toolRef = useRef<Tool>('cursor');
  const [, force] = useState(0); // re-render for toolbar active state
  toolRef.current = tool;

  const toPx = useCallback((anchor: Anchor): { x: number; y: number } | null => {
    const chart = ctrl.chartRef.current;
    const series = ctrl.seriesRef.current;
    if (!chart || !series) return null;
    const x = chart.timeScale().logicalToCoordinate(anchor.logical as any);
    const y = series.priceToCoordinate(anchor.price);
    if (x == null || y == null) return null;
    return { x, y };
  }, [ctrl]);

  const fromPx = useCallback((px: number, py: number): Anchor | null => {
    const chart = ctrl.chartRef.current;
    const series = ctrl.seriesRef.current;
    if (!chart || !series) return null;
    const logical = chart.timeScale().coordinateToLogical(px);
    const price = series.coordinateToPrice(py);
    if (logical == null || price == null) return null;
    return { logical: Number(logical), price };
  }, [ctrl]);

  const redraw = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    const w = container.clientWidth;
    const h = CHART_HEIGHT;
    const dpr = window.devicePixelRatio || 1;
    if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
      canvas.width = w * dpr; canvas.height = h * dpr;
      canvas.style.width = `${w}px`; canvas.style.height = `${h}px`;
    }
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    ctx.font = '10px ui-monospace, monospace';
    ctx.lineWidth = 1.5;

    const all = [...drawingsRef.current];
    if (pendingRef.current && hoverRef.current) {
      all.push({ id: -1, tool: toolRef.current, a: pendingRef.current, b: hoverRef.current });
    }

    for (const d of all) {
      const color = TOOL_COLOR[d.tool];
      ctx.strokeStyle = color; ctx.fillStyle = color;
      const a = toPx(d.a);
      if (!a) continue;
      const b = d.b ? toPx(d.b) : null;

      if (d.tool === 'hline') {
        ctx.beginPath(); ctx.moveTo(0, a.y); ctx.lineTo(w, a.y); ctx.stroke();
        ctx.fillText(d.a.price.toFixed(2), 4, a.y - 3);
      } else if (d.tool === 'trend' && b) {
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      } else if (d.tool === 'box' && b) {
        ctx.globalAlpha = 0.12; ctx.fillRect(a.x, a.y, b.x - a.x, b.y - a.y); ctx.globalAlpha = 1;
        ctx.strokeRect(a.x, a.y, b.x - a.x, b.y - a.y);
      } else if (d.tool === 'fib' && b) {
        const x0 = Math.min(a.x, b.x), x1 = Math.max(a.x, b.x);
        for (const lvl of FIB_LEVELS) {
          const price = d.a.price + (d.b!.price - d.a.price) * lvl;
          const yp = ctrl.seriesRef.current?.priceToCoordinate(price);
          if (yp == null) continue;
          ctx.globalAlpha = 0.7;
          ctx.beginPath(); ctx.moveTo(x0, yp); ctx.lineTo(x1, yp); ctx.stroke();
          ctx.globalAlpha = 1;
          ctx.fillText(`${(lvl * 100).toFixed(1)}%  ${price.toFixed(2)}`, x1 + 4, yp + 3);
        }
      } else if (d.tool === 'ruler' && b) {
        ctx.setLineDash([4, 3]);
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
        ctx.setLineDash([]);
        const dPct = d.a.price ? (d.b!.price - d.a.price) / d.a.price * 100 : 0;
        const dDays = Math.round(d.b!.logical - d.a.logical);
        const label = `${dPct >= 0 ? '+' : ''}${dPct.toFixed(2)}%  ${dDays >= 0 ? '+' : ''}${dDays}d`;
        ctx.fillStyle = '#0a0c10'; ctx.fillRect(b.x + 2, b.y - 12, ctx.measureText(label).width + 6, 14);
        ctx.fillStyle = color; ctx.fillText(label, b.x + 5, b.y - 1);
      }
    }
  }, [containerRef, toPx, ctrl]);

  // Subscribe to chart pan/zoom/stream + resize so drawings stay anchored.
  useEffect(() => {
    const chart = ctrl.chartRef.current;
    let raf = 0;
    const schedule = () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(redraw); };
    const ts = chart?.timeScale();
    ts?.subscribeVisibleLogicalRangeChange(schedule);
    window.addEventListener('resize', schedule);
    schedule();
    // light poll covers the brief window before chartRef is populated and any
    // animation frames the subscription misses
    const id = window.setInterval(schedule, 250);
    return () => {
      cancelAnimationFrame(raf);
      window.clearInterval(id);
      window.removeEventListener('resize', schedule);
      try { ts?.unsubscribeVisibleLogicalRangeChange(schedule); } catch {}
    };
  }, [ctrl, redraw]);

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    if (toolRef.current === 'cursor') return;
    const rect = canvasRef.current!.getBoundingClientRect();
    const anchor = fromPx(e.clientX - rect.left, e.clientY - rect.top);
    if (!anchor) return;
    if (toolRef.current === 'hline') {
      drawingsRef.current.push({ id: idRef.current++, tool: 'hline', a: anchor });
      redraw();
      return;
    }
    if (!pendingRef.current) {
      pendingRef.current = anchor;
      hoverRef.current = anchor;
    } else {
      drawingsRef.current.push({ id: idRef.current++, tool: toolRef.current, a: pendingRef.current, b: anchor });
      pendingRef.current = null; hoverRef.current = null;
      redraw();
    }
  }, [fromPx, redraw]);

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!pendingRef.current) return;
    const rect = canvasRef.current!.getBoundingClientRect();
    hoverRef.current = fromPx(e.clientX - rect.left, e.clientY - rect.top);
    redraw();
  }, [fromPx, redraw]);

  const undo = () => { drawingsRef.current.pop(); pendingRef.current = null; redraw(); };
  const clear = () => { drawingsRef.current = []; pendingRef.current = null; redraw(); };

  const tools: { id: Tool; label: string }[] = [
    { id: 'cursor', label: '🖱' }, { id: 'trend', label: '╱' }, { id: 'hline', label: '─' },
    { id: 'box', label: '▭' }, { id: 'fib', label: 'fib' }, { id: 'ruler', label: '📏' },
  ];

  return (
    <>
      <canvas
        ref={canvasRef}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        className="absolute top-0 left-0"
        style={{ height: CHART_HEIGHT, pointerEvents: tool === 'cursor' ? 'none' : 'auto', cursor: tool === 'cursor' ? 'default' : 'crosshair', zIndex: 5 }}
      />
      <div className="absolute bottom-7 left-2 flex items-center gap-0.5 bg-[#0a0c10]/85 px-1 py-1 rounded border border-[#2a313a]" style={{ zIndex: 6 }}>
        {tools.map((t) => (
          <button key={t.id} onClick={() => { setTool(t.id); force((n) => n + 1); if (t.id === 'cursor') { pendingRef.current = null; redraw(); } }}
            title={t.id}
            className={`px-1.5 py-0.5 rounded text-[11px] ${tool === t.id ? 'bg-[#272d37] text-white' : 'bg-[#1a1f26] text-[#9ca3af]'}`}>
            {t.label}
          </button>
        ))}
        <span className="w-px h-4 bg-[#2a313a] mx-0.5" />
        <button onClick={undo} title="undo" className="px-1.5 py-0.5 rounded text-[11px] bg-[#1a1f26] text-[#9ca3af]">⎌</button>
        <button onClick={clear} title="clear" className="px-1.5 py-0.5 rounded text-[11px] bg-[#1a1f26] text-[#ef4444]">✕</button>
      </div>
    </>
  );
}
