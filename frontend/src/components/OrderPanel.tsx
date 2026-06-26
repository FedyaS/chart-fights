'use client';

import { useState } from 'react';

interface OrderPanelProps {
  onPlaceOrder: (order: { type: string; side: string; size: number; price?: number }) => void;
  currentPrice?: number;
}

export function OrderPanel({ onPlaceOrder, currentPrice = 100 }: OrderPanelProps) {
  const [otype, setOtype] = useState<'market' | 'limit' | 'stop'>('market');
  const [side, setSide] = useState<'long' | 'short'>('long');
  const [size, setSize] = useState(100);
  const [limitPrice, setLimitPrice] = useState(currentPrice);

  const submit = () => {
    const ord = {
      type: otype,
      side,
      size: Math.max(10, Math.floor(size)),
      ...(otype !== 'market' ? { price: limitPrice } : {}),
    };
    onPlaceOrder(ord);
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
        <span className="text-[#9ca3af]">shr</span>
        {otype !== 'market' && (<><label className="text-[#9ca3af] ml-1">Price</label><input type="number" step="0.01" value={limitPrice} onChange={(e) => setLimitPrice(+e.target.value)} className="bg-[#0b0e14] border border-[#2a313a] px-2 py-0.5 rounded w-16 text-right" /></>)}
      </div>

      <button onClick={submit} className="mt-1 py-1.5 text-sm rounded bg-white text-black font-medium active:bg-[#e5e7eb]">
        PLACE {side.toUpperCase()} {otype.toUpperCase()} @ ~{currentPrice.toFixed(2)}
      </button>

      <div className="text-[10px] text-[#9ca3af]">Sends submit_order via WS to backend.</div>
    </div>
  );
}
