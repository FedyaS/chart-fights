// Core domain types for chart-fights frontend.
// These mirror the backend WS/HTTP contract (task-007). Backend may ADD fields,
// so all server-derived parsing is defensive and tolerant of missing keys.

export interface Bar {
  time: number; // synthetic day index T (used directly as the lightweight-charts time)
  open: number;
  high: number;
  low: number;
  close: number;
}

// Lobby arena summary from GET /arenas
export interface Arena {
  id: string;
  name: string;
  ticker: string;
  description: string;
  bars: Bar[]; // only populated for offline SAMPLE_ARENAS; server arenas reveal bars progressively
  numBars?: number;
}

export type Side = 'long' | 'short';
export type OrderType = 'market' | 'limit' | 'stop';

export interface Position {
  instr: string;
  side: Side;
  size: number;
  entry: number;
  // optional server-provided marks
  unrealized?: number;
}

export interface OpenOrder {
  id?: string;
  instr: string;
  side: Side;
  size: number;
  type: OrderType | string;
  price?: number;
  // Bracket-order extras (TP/SL legs). `group` links OCO siblings to their entry.
  tp?: number; // take-profit price (on the entry order, before it fills)
  sl?: number; // stop-loss price (on the entry order, before it fills)
  group?: number | string;
  reduceOnly?: boolean;
  kind?: 'tp' | 'sl' | string; // bracket leg role, when this order IS a TP/SL leg
}

export interface PlayerState {
  id: string;
  ip: number;
  equity: number;
  pnl: number; // equity - starting capital (100) unless server provides
  unrealized: number; // sum of open-position unrealized PnL (computed if not server-provided)
  tb: number; // tempo bar resource 0..100
  positions: Position[];
  orders: OpenOrder[];
  buyingPower?: number; // max gross exposure (equity * leverage)
  exposure?: number; // current gross exposure (sum |size|)
}

// A normalized news / economic-calendar item (anti-cheat: Sim Day only, sector labels).
export interface NewsItem {
  t: number; // Sim Day
  kind: 'headline' | 'calendar' | string;
  title: string;
  sentiment?: 'bullish' | 'bearish' | 'neutral' | string;
  importance?: 'low' | 'medium' | 'high' | string;
  // calendar-only
  name?: string;
  actual?: number;
  forecast?: number;
  prior?: number;
  surprise?: number;
}

// Macro indicator snapshot shown in the IndicatorPanel.
export interface Indicators {
  t?: number;
  cpi_yoy?: number;
  unemployment?: number;
  fed_funds?: number;
  ten_year?: number;
}

export interface Fill {
  player: string;
  instr: string;
  price: number;
  size: number;
  side: Side | string;
  type: string;
  t: number;
}

// A normalized server/game event (sabotage, news, fill, info, peek).
export interface GameEvent {
  type: string; // 'sabo' | 'fill' | 'news' | 'peek' | 'info' | ...
  message: string;
  t?: number;
  target?: string;
  ability?: string;
}

// Local UI log line (superset; server events are folded into this).
export interface LogEvent {
  t: number;
  type: 'order' | 'sabo' | 'tb' | 'voice' | 'info' | 'fill' | 'news' | 'peek';
  message: string;
}

// Resolved tempo state derived from snapshot/delta.
export interface TempoState {
  R: number; // resolved clock rate (days per real second)
  contested: boolean;
  myLevel: TempoLevel; // local player's current influence level
}

export type TempoLevel = 'base' | 'pause' | 'ff2' | 'ff3' | 'ff5';

// Parsed, UI-friendly snapshot of the whole match.
export interface MatchSnapshot {
  matchId: string;
  arenaId: string;
  contentHash?: string;
  label?: string;
  T: number;
  tempo: TempoState;
  currentBar: Bar | null;
  players: Record<string, PlayerState>;
  you: string;
  recentEvents: GameEvent[];
}

export interface MatchEndResult {
  winner: string | null; // player id, or null for draw
  players: Record<string, PlayerState>;
  you: string;
  contentHash?: string;
  reveal?: MatchReveal; // post-match: real ticker/dates (hidden during play)
}

// Post-match reveal of what the obfuscated arena actually was.
export interface MatchReveal {
  ticker?: string;
  start_date?: string;
  end_date?: string;
  sector?: string;
}

// Info returned by POST /matches (or constructed for a join).
export interface MatchInfo {
  matchId: string;
  arenaId: string;
  arenaLabel: string;
  arenaHash?: string;
  contentHash?: string;
  numBars?: number;
  wsUrl: string;
  you: string;
  bot?: boolean; // quick-match vs-bot fallback
  sector?: string;
}
