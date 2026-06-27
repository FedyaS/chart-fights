// Defensive parsers that turn raw backend WS payloads into typed UI state.
// The backend may ADD fields; these helpers tolerate missing/renamed keys and
// never throw on unexpected shapes.

import type {
  Bar,
  PlayerState,
  Position,
  OpenOrder,
  TempoState,
  TempoLevel,
  GameEvent,
  Fill,
  Side,
  NewsItem,
  Indicators,
} from '../types';

const STARTING_CAPITAL = 100;

export function num(v: unknown, fallback = 0): number {
  const n = typeof v === 'number' ? v : Number(v);
  return Number.isFinite(n) ? n : fallback;
}

// Server bars use `t` for the day index; the chart uses it directly as `time`.
export function toBar(raw: any): Bar | null {
  if (!raw || typeof raw !== 'object') return null;
  const time = raw.time ?? raw.t;
  if (time == null) return null;
  return {
    time: num(time),
    open: num(raw.open),
    high: num(raw.high),
    low: num(raw.low),
    close: num(raw.close),
  };
}

function parsePosition(raw: any): Position {
  return {
    instr: String(raw?.instr ?? raw?.instrument ?? 'X'),
    side: (raw?.side === 'short' ? 'short' : 'long') as Side,
    size: num(raw?.size),
    entry: num(raw?.entry ?? raw?.entry_price ?? raw?.price),
    unrealized: raw?.unrealized != null ? num(raw.unrealized) : undefined,
  };
}

function parseOrder(raw: any): OpenOrder {
  return {
    id: raw?.id != null ? String(raw.id) : undefined,
    instr: String(raw?.instr ?? raw?.instrument ?? 'X'),
    side: (raw?.side === 'short' ? 'short' : 'long') as Side,
    size: num(raw?.size),
    type: String(raw?.type ?? 'limit'),
    price: raw?.price != null ? num(raw.price) : undefined,
    tp: raw?.tp != null ? num(raw.tp) : undefined,
    sl: raw?.sl != null ? num(raw.sl) : undefined,
    group: raw?.group ?? undefined,
    reduceOnly: raw?.reduce_only ?? raw?.reduceOnly ?? undefined,
    kind: raw?.kind ?? undefined,
  };
}

function unrealizedFor(pos: Position, markPrice: number): number {
  if (!pos.entry || !markPrice) return 0;
  const dir = pos.side === 'long' ? 1 : -1;
  return pos.size * dir * (markPrice - pos.entry) / pos.entry;
}

// Build a single player's state from either a snapshot player object or a
// merge of snapshot + delta resources. `prev` lets deltas patch a known player.
export function parsePlayer(
  id: string,
  raw: any,
  markPrice: number,
  prev?: PlayerState,
): PlayerState {
  const positions: Position[] = Array.isArray(raw?.positions)
    ? raw.positions.map(parsePosition)
    : prev?.positions ?? [];
  const orders: OpenOrder[] = Array.isArray(raw?.orders)
    ? raw.orders.map(parseOrder)
    : prev?.orders ?? [];

  const equity = raw?.equity != null ? num(raw.equity) : prev?.equity ?? STARTING_CAPITAL;
  const ip = raw?.ip != null ? num(raw.ip) : prev?.ip ?? 50;
  const tb = raw?.tb != null && typeof raw.tb === 'number' ? num(raw.tb) : prev?.tb ?? 100;

  const unrealized = positions.reduce(
    (acc, p) => acc + (p.unrealized != null ? p.unrealized : unrealizedFor(p, markPrice)),
    0,
  );
  const pnl = raw?.pnl != null ? num(raw.pnl) : equity - STARTING_CAPITAL;
  const buyingPower = raw?.buying_power != null ? num(raw.buying_power)
    : raw?.buyingPower != null ? num(raw.buyingPower) : prev?.buyingPower;
  const exposure = raw?.exposure != null ? num(raw.exposure) : prev?.exposure;

  return { id, ip, equity, pnl, unrealized, tb, positions, orders, buyingPower, exposure };
}

export function parsePlayersMap(
  rawPlayers: any,
  markPrice: number,
  prev?: Record<string, PlayerState>,
): Record<string, PlayerState> {
  const out: Record<string, PlayerState> = {};
  if (rawPlayers && typeof rawPlayers === 'object') {
    for (const id of Object.keys(rawPlayers)) {
      out[id] = parsePlayer(id, rawPlayers[id], markPrice, prev?.[id]);
    }
  }
  return out;
}

// Merge delta.resources (per-player {ip,equity,tb}) onto known players.
export function applyResources(
  players: Record<string, PlayerState>,
  resources: any,
  markPrice: number,
): Record<string, PlayerState> {
  if (!resources || typeof resources !== 'object') return players;
  const out: Record<string, PlayerState> = { ...players };
  for (const id of Object.keys(resources)) {
    out[id] = parsePlayer(id, resources[id], markPrice, players[id]);
  }
  return out;
}

function countInfluences(influences: any): number {
  if (influences == null) return 0;
  if (Array.isArray(influences)) return influences.filter(Boolean).length;
  if (typeof influences === 'number') return influences;
  if (typeof influences === 'object') {
    return Object.values(influences).filter((v) => {
      if (v == null) return false;
      if (typeof v === 'string') return v !== 'base' && v !== 'none';
      if (typeof v === 'number') return v !== 0 && v !== 1;
      return Boolean(v);
    }).length;
  }
  return 0;
}

function levelFromValue(v: unknown): TempoLevel | null {
  if (typeof v === 'string') {
    if (['base', 'pause', 'ff2', 'ff3', 'ff5'].includes(v)) return v as TempoLevel;
  }
  if (typeof v === 'number') {
    if (v === 0) return 'pause';
    if (v === 2) return 'ff2';
    if (v === 3) return 'ff3';
    if (v === 5) return 'ff5';
    if (v === 1) return 'base';
  }
  return null;
}

// Resolve tempo from a `tb` object {r, tbs, influences} plus a top-level r.
export function resolveTempo(tbObj: any, topR: unknown, you: string, fallback: TempoLevel = 'base'): TempoState {
  const R = num(tbObj?.r ?? topR, 1);
  const contested = countInfluences(tbObj?.influences) >= 2;
  const myLevel = levelFromValue(tbObj?.tbs?.[you]) ?? fallback;
  return { R, contested, myLevel };
}

export function parseEvents(raw: any): GameEvent[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((e: any): GameEvent => ({
    type: String(e?.type ?? 'info'),
    message: String(e?.message ?? e?.msg ?? JSON.stringify(e)),
    t: e?.t != null ? num(e.t) : (e?.sim_T != null ? num(e.sim_T) : undefined),
    target: e?.target ?? e?.target_player,
    ability: e?.ability,
  }));
}

export function parseFills(raw: any): Fill[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((f: any): Fill => ({
    player: String(f?.player ?? f?.player_id ?? '?'),
    instr: String(f?.instr ?? f?.instrument ?? 'X'),
    price: num(f?.price),
    size: num(f?.size),
    side: String(f?.side ?? 'long'),
    type: String(f?.type ?? 'market'),
    t: num(f?.t),
  }));
}

export function parseNews(raw: any): NewsItem[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((e: any) => e && (e.title || e.headline))
    .map((e: any): NewsItem => ({
      t: num(e?.t),
      kind: String(e?.kind ?? (e?.name ? 'calendar' : 'headline')),
      title: String(e?.title ?? e?.headline ?? ''),
      sentiment: e?.sentiment,
      importance: e?.importance,
      name: e?.name,
      actual: e?.actual != null ? num(e.actual) : undefined,
      forecast: e?.forecast != null ? num(e.forecast) : undefined,
      prior: e?.prior != null ? num(e.prior) : undefined,
      surprise: e?.surprise != null ? num(e.surprise) : undefined,
    }));
}

export function parseIndicators(raw: any): Indicators | null {
  if (!raw || typeof raw !== 'object') return null;
  const pick = (k: string) => (raw[k] != null ? num(raw[k]) : undefined);
  return {
    t: raw.t != null ? num(raw.t) : undefined,
    cpi_yoy: pick('cpi_yoy'),
    unemployment: pick('unemployment'),
    fed_funds: pick('fed_funds'),
    ten_year: pick('ten_year'),
  };
}

export function otherPlayer(players: Record<string, PlayerState>, you: string): PlayerState | null {
  const ids = Object.keys(players).filter((id) => id !== you);
  return ids.length ? players[ids[0]] : null;
}
