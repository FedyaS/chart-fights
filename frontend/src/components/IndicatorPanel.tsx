'use client';

import type { Indicators } from '../types';

interface IndicatorPanelProps {
  indicators: Indicators | null;
}

const FIELDS: { key: keyof Indicators; label: string; suffix: string }[] = [
  { key: 'cpi_yoy', label: 'CPI YoY', suffix: '%' },
  { key: 'unemployment', label: 'Unemp', suffix: '%' },
  { key: 'fed_funds', label: 'Fed Funds', suffix: '%' },
  { key: 'ten_year', label: '10Y', suffix: '%' },
];

export function IndicatorPanel({ indicators }: IndicatorPanelProps) {
  return (
    <div className="panel p-3">
      <div className="text-xs font-medium mb-2">ECON INDICATORS</div>
      <div className="grid grid-cols-2 gap-2">
        {FIELDS.map((f) => {
          const v = indicators?.[f.key];
          return (
            <div key={String(f.key)} className="rounded border border-[#2a313a] bg-[#0b0e14] px-2 py-1.5">
              <div className="text-[10px] uppercase tracking-widest text-[#6b7280]">{f.label}</div>
              <div className="font-mono text-sm tabular-nums">
                {typeof v === 'number' ? `${v}${f.suffix}` : '—'}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
