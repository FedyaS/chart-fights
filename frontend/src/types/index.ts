export interface Bar { time: number; open: number; high: number; low: number; close: number; }
export interface Arena { id: string; name: string; ticker: string; description: string; bars: Bar[]; }
export interface LogEvent { t: number; type: 'order' | 'sabo' | 'tb' | 'voice' | 'info'; message: string; }
