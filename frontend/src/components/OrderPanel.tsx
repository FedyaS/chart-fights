'use client';

import { useEffect, useState } from 'react';
import type { OrderType, Side } from '../types';

export interface OrderRequest {
  type: OrderType;
  side: Side;
  size: number;
  price?: number;
  tp?: number;
  sl?: number;
}

interface OrderPanelProps {
  onPlaceOrder: (order: OrderRequest) => void;
  currentPrice?: number;
  buyingPower?: number;
  exposure?: number;
  disabled?: boolean;
}

// P/L in equity points for a position of `size` units moving entry -> exit.
function pl(size: number, entry: number, exit: number, side: Side): number {
  if (!entry) return 0;
  const dir = side === 'long' ? 1 : -1;
  return size * dir * (exit - entry) / entry;
}

export function OrderPanel({ onPlaceOrder, currentPrice = 100, buyingPower, exposure, disabled }: OrderPanelProps) {
  const [otype, setOtype] = useState<OrderType>('market');
  const [side, setSide] = useState<Side>('long');
  const [size, setSize] = useState(40);
  const [limitPrice, setLimitPrice] = useState(currentPrice);
  const [useBracket, setUseBracket] = useState(true);
  const [tpPct, setTpPct] = useState(3); // % from entry
  const [slPct, setSlPct] = useState(1.5);

  // keep the limit price tracking the market until the user touches a non-market type
  useEffect(() => {
    if (otype === 'market') setLimitPrice(currentPrice);
  }, [currentPrice, otype]);

  const entry = otype === 'market' ? currentPrice : limitPrice;
  // long: TP above / SL below; short: TP below / SL above
  const tpPrice = side === 'long' ? entry * (1 + tpPct / 100) : entry * (1 - tpPct / 100);
  const slPrice = side === 'long' ? entry * (1 - slPct / 100) : entry * (1 + slPct / 100);

  const tpPL = pl(size, entry, tpPrice, side);
  const slPL = pl(size, entry, slPrice, side);
  const rr = slPL !== 0 ? Math.abs(tpPL / slPL) : 0;

  const overBuyingPower = buyingPower != null && exposure != null && exposure + size > buyingPower + 1e-6;

  const submit = () => {
    if (disabled) return;
    const s = Math.max(1, Math.floor(size));
    onPlaceOrder({
      type: otype,
      side,
      size: s,
      ...(otype !== 'market' ? { price: limitPrice } : {}),
      ...(useBracket ? { tp: +tpPrice.toFixed(2), sl: +slPrice.toFixed(2) } : {}),
    });
  };

  return (
    <div className="panel p-3 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <div className="text-xs font-medium">ORDERS</div>
        {buyingPower != null && (
          <div className="text-[10px] text-[#6b7280] font-mono">
            BP {Math.max(0, buyingPower - (exposure ?? 0)).toFixed(0)}/{buyingPower.toFixed(0)}
          </div>
        )}
      </div>

      <div className="flex gap-1 text-[11px]">
        {(['market', 'limit', 'stop'] as const).map((t) => (
          <button key={t} onClick={() => setOtype(t)} className={`px-2 py-0.5 rounded ${otype === t ? 'bg-[#272d37]' : 'bg-[#1a1f26]'}`}>{t}</button>
        ))}
      </div>

      <div className="flex gap-1 text-[11px]">
        <button onClick={() => setSide('long')} className={`flex-1 py-1 rounded ${side === 'long' ? 'bg-[#052e16] text-[#22c55e]' : 'bg-[#1a1f26]'}`}>LONG</button>
        <button onClick={() => setSide('short')} className={`flex-1 py-1 rounded ${side === 'short' ? 'bg-[#3f1c1c] text-[#ef4444]' : 'bg-[#1a1f26]'}`}>SHORT</button>
      </div>

      <div className="flex gap-2 items-center text-xs">
        <label className="text-[#9ca3af]">Size</label>
        <input type="number" value={size} onChange={(e) => setSize(+e.target.value)} className="bg-[#0b0e14] border border-[#2a313a] px-2 py-0.5 rounded w-16 text-right" />
        <span className="text-[#9ca3af]">units</span>
        {otype !== 'market' && (<><label className="text-[#9ca3af] ml-1">Price</label><input type="number" step="0.01" value={limitPrice} onChange={(e) => setLimitPrice(+e.target.value)} className="bg-[#0b0e14] border border-[#2a313a] px-2 py-0.5 rounded w-16 text-right" /></>)}
      </div>

      <label className="flex items-center gap-1.5 text-[11px] text-[#9ca3af] cursor-pointer select-none">
        <input type="checkbox" checked={useBracket} onChange={(e) => setUseBracket(e.target.checked)} />
        Bracket (TP / SL)
      </label>

      {useBracket && (
        <div className="rounded border border-[#2a313a] bg-[#0b0e14] p-2 space-y-1.5">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-[#22c55e]">Take Profit</span>
            <div className="flex items-center gap-1">
              <button onClick={() => setTpPct((v) => Math.max(0.1, +(v - 0.5).toFixed(1)))} className="px-1.5 rounded bg-[#1a1f26]">−</button>
              <span className="font-mono w-12 text-right">{tpPct.toFixed(1)}%</span>
              <button onClick={() => setTpPct((v) => +(v + 0.5).toFixed(1))} className="px-1.5 rounded bg-[#1a1f26]">+</button>
              <span className="font-mono text-[#6b7280] w-16 text-right">@{tpPrice.toFixed(2)}</span>
              <span className="font-mono text-[#22c55e] w-14 text-right">+{tpPL.toFixed(2)}</span>
            </div>
          </div>
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-[#ef4444]">Stop Loss</span>
            <div className="flex items-center gap-1">
              <button onClick={() => setSlPct((v) => Math.max(0.1, +(v - 0.5).toFixed(1)))} className="px-1.5 rounded bg-[#1a1f26]">−</button>
              <span className="font-mono w-12 text-right">{slPct.toFixed(1)}%</span>
              <button onClick={() => setSlPct((v) => +(v + 0.5).toFixed(1))} className="px-1.5 rounded bg-[#1a1f26]">+</button>
              <span className="font-mono text-[#6b7280] w-16 text-right">@{slPrice.toFixed(2)}</span>
              <span className="font-mono text-[#ef4444] w-14 text-right">{slPL.toFixed(2)}</span>
            </div>
          </div>
          <div className="text-[10px] text-[#6b7280] text-right">Risk : Reward ≈ 1 : {rr.toFixed(2)}</div>
        </div>
      )}

      {overBuyingPower && (
        <div className="text-[10px] text-[#ef4444]">Exceeds buying power — reduce size.</div>
      )}

      <button onClick={submit} disabled={disabled} className={`mt-1 py-1.5 text-sm rounded font-medium ${disabled ? 'bg-[#272d37] text-[#6b7280] cursor-not-allowed' : 'bg-white text-black active:bg-[#e5e7eb]'}`}>
        {side.toUpperCase()} {otype.toUpperCase()} {size}u @ ~{currentPrice.toFixed(2)}{useBracket ? ' + bracket' : ''}
      </button>

      <div className="text-[10px] text-[#9ca3af]">Bracket attaches reduce-only TP/SL (OCO). Lines render on the chart.</div>
    </div>
  );
}
