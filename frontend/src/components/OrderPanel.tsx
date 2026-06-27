'use client';

import { useState } from 'react';
import type { OrderType, Side } from '../types';

interface OrderPanelProps {
  onPlaceOrder: (order: { type: OrderType; side: Side; size: number; price?: number }) => void;
  currentPrice?: number;
  disabled?: boolean;
}

export function OrderPanel({ onPlaceOrder, currentPrice = 100, disabled }: OrderPanelProps) {
  const [otype, setOtype] = useState<OrderType>('market');
  const [side, setSide] = useState<Side>('long');
  const [size, setSize] = useState(40);
  const [limitPrice, setLimitPrice] = useState(currentPrice);

  const submit = () => {
    if (disabled) return;
    onPlaceOrder({
      type: otype,
      side,
      size: Math.max(1, Math.floor(size)),
      ...(otype !== 'market' ? { price: limitPrice } : {}),
    });
    if (otype !== 'market') setLimitPrice(currentPrice);
  };

  return (
    <div className="panel p-3 flex flex-col gap-2">
      <div className="text-xs font-medium">ORDERS</div>

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

      <button onClick={submit} disabled={disabled} className={`mt-1 py-1.5 text-sm rounded font-medium ${disabled ? 'bg-[#272d37] text-[#6b7280] cursor-not-allowed' : 'bg-white text-black active:bg-[#e5e7eb]'}`}>
        PLACE {side.toUpperCase()} {otype.toUpperCase()} @ ~{currentPrice.toFixed(2)}
      </button>

      <div className="text-[10px] text-[#9ca3af]">Sends submit_order via WS. Fills appear as chart markers + in the log.</div>
    </div>
  );
}
