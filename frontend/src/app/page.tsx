'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ArenaLobby } from '../components/ArenaLobby';
import { ChartView } from '../components/ChartView';
import { ResourceBars } from '../components/ResourceBars';
import { SaboPanel, type Ability } from '../components/SaboPanel';
import { OrderPanel, type OrderRequest } from '../components/OrderPanel';
import { PositionsTable } from '../components/PositionsTable';
import { NewsFeed } from '../components/NewsFeed';
import { IndicatorPanel } from '../components/IndicatorPanel';
import { VoicePanel } from '../components/VoicePanel';
import { EventLog } from '../components/EventLog';
import { Scoreboard } from '../components/Scoreboard';
import { EndScreen } from '../components/EndScreen';
import { SAMPLE_ARENAS } from '../lib/sampleArenas';
import { useVoiceChat, type VoiceSignalType } from '../hooks/useVoiceChat';
import type { ReplayController } from '../hooks/useReplayController';
import {
  toBar, num, parsePlayersMap, applyResources, resolveTempo,
  parseEvents, parseFills, parseNews, parseIndicators, otherPlayer,
} from '../lib/matchState';
import type {
  Arena, Bar, LogEvent, PlayerState, TempoLevel, TempoState,
  MatchInfo, MatchEndResult, GameEvent, NewsItem, Indicators, MatchReveal,
} from '../types';

const BACKEND_URL =
  (typeof window !== 'undefined' && (window as any).CHART_BACKEND) ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  'http://localhost:8001';
const WS_BASE = BACKEND_URL.replace(/^http/, 'ws');

const STARTING_CAPITAL = 100;
const OFFLINE_BASE_MS = 900; // 1 day per ~0.9s at R=1 (offline only)
const MATCH_SECONDS = 300;

const levelToR = (l: TempoLevel): number => (l === 'pause' ? 0 : l === 'ff2' ? 2 : l === 'ff3' ? 3 : l === 'ff5' ? 5 : 1);

const LOG_TYPES: LogEvent['type'][] = ['order', 'sabo', 'tb', 'voice', 'info', 'fill', 'news', 'peek'];
const toLogType = (t: string): LogEvent['type'] => (LOG_TYPES.includes(t as any) ? (t as LogEvent['type']) : 'info');

type View = 'lobby' | 'match' | 'ended';

const emptyTempo: TempoState = { R: 1, contested: false, myLevel: 'base' };

function fmtClock(secs: number): string {
  const s = Math.max(0, Math.floor(secs));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

export default function ChartFightsApp() {
  const [view, setView] = useState<View>('lobby');
  const [arenas, setArenas] = useState<Arena[]>(SAMPLE_ARENAS);
  const [loadingArenas, setLoadingArenas] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [selectedArenaId, setSelectedArenaId] = useState<string | undefined>();

  const [matchInfo, setMatchInfo] = useState<MatchInfo | null>(null);
  const [mode, setMode] = useState<'server' | 'offline'>('server');
  const [you, setYou] = useState<string>('p1');
  const [T, setT] = useState(0);
  const [timeLeft, setTimeLeft] = useState(MATCH_SECONDS);
  const [tempo, setTempo] = useState<TempoState>(emptyTempo);
  const [players, setPlayers] = useState<Record<string, PlayerState>>({});
  const [currentBar, setCurrentBar] = useState<Bar | null>(null);
  const [events, setEvents] = useState<LogEvent[]>([]);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [indicators, setIndicators] = useState<Indicators | null>(null);
  const [equityCurve, setEquityCurve] = useState<number[]>([]);
  const [endResult, setEndResult] = useState<MatchEndResult | null>(null);

  const [joinId, setJoinId] = useState('');
  const [joinAs, setJoinAs] = useState<'p1' | 'p2'>('p2');

  // refs for use inside stable WS / timer closures
  const wsRef = useRef<WebSocket | null>(null);
  const ctrlRef = useRef<ReplayController | null>(null);
  const youRef = useRef('p1');
  const playersRef = useRef<Record<string, PlayerState>>({});
  const currentBarRef = useRef<Bar | null>(null);
  const revealedBarsRef = useRef<Bar[]>([]);
  const myLevelRef = useRef<TempoLevel>('base');
  const modeRef = useRef<'server' | 'offline'>('server');
  const gotSnapshotRef = useRef(false);
  const voiceHandleRef = useRef<((t: VoiceSignalType, p: any) => void) | null>(null);
  const priceLinesRef = useRef<Set<string>>(new Set());
  const equityCurveRef = useRef<number[]>([]);
  const revealRef = useRef<MatchReveal | undefined>(undefined);

  // offline simulation refs
  const offlineBarsRef = useRef<Bar[]>([]);
  const offlineIdxRef = useRef(-1);
  const offlineRealizedRef = useRef(0);

  const addLog = useCallback((type: LogEvent['type'], message: string, t?: number) => {
    setEvents((prev) => [...prev, { t: t ?? Math.round(currentBarRef.current?.time ?? 0), type, message }].slice(-60));
  }, []);

  // ---- send helpers -----------------------------------------------------
  const sendRaw = useCallback((obj: any) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
  }, []);
  const sendWSAction = useCallback((actionType: string, payload: any) => {
    sendRaw({ type: 'action', action_type: actionType, payload });
  }, [sendRaw]);

  const sendVoiceSignal = useCallback((type: VoiceSignalType, payload: any) => {
    sendRaw({ type, payload });
  }, [sendRaw]);

  const voice = useVoiceChat(sendVoiceSignal);
  useEffect(() => { voiceHandleRef.current = voice.handleSignal; }, [voice.handleSignal]);

  // ---- arenas -----------------------------------------------------------
  useEffect(() => {
    setLoadingArenas(true);
    fetch(`${BACKEND_URL}/arenas`)
      .then((r) => r.json())
      .then((d) => {
        const list: Arena[] = (d.arenas || []).map((a: any) => ({
          id: a.id,
          name: a.label || a.sector || a.id, // sector · codename (no ticker — anti-cheat #4)
          ticker: a.sector || a.asset_class || 'Equity',
          description: `${a.asset_class ?? 'Equity'} • ${a.bars ?? '?'} bars`,
          bars: [],
          numBars: a.bars,
        }));
        setArenas(list.length ? list : SAMPLE_ARENAS);
      })
      .catch(() => setArenas(SAMPLE_ARENAS))
      .finally(() => setLoadingArenas(false));
  }, []);

  // ---- chart bar plumbing ----------------------------------------------
  const pushBarToChart = useCallback((bar: Bar) => {
    const arr = revealedBarsRef.current;
    if (arr.length && arr[arr.length - 1].time === bar.time) {
      arr[arr.length - 1] = bar; // replace in-progress candle
    } else if (!arr.length || bar.time > arr[arr.length - 1].time) {
      arr.push(bar);
    } else {
      return; // out-of-order / stale, ignore
    }
    currentBarRef.current = bar;
    setCurrentBar(bar);
    ctrlRef.current?.pushBar(bar);
  }, []);

  const handleCtrl = useCallback((c: ReplayController) => {
    ctrlRef.current = c;
    if (revealedBarsRef.current.length) c.setHistory(revealedBarsRef.current);
  }, []);

  const resetMatchState = useCallback(() => {
    revealedBarsRef.current = [];
    currentBarRef.current = null;
    playersRef.current = {};
    offlineBarsRef.current = [];
    offlineIdxRef.current = -1;
    offlineRealizedRef.current = 0;
    gotSnapshotRef.current = false;
    myLevelRef.current = 'base';
    priceLinesRef.current = new Set();
    equityCurveRef.current = [];
    revealRef.current = undefined;
    ctrlRef.current?.clearPriceLines();
    setPlayers({});
    setCurrentBar(null);
    setEvents([]);
    setNews([]);
    setIndicators(null);
    setEquityCurve([]);
    setEndResult(null);
    setT(0);
    setTimeLeft(MATCH_SECONDS);
    setTempo(emptyTempo);
  }, []);

  // split raw events into news (own panel) + everything else (log)
  const ingestEvents = useCallback((rawEvents: any) => {
    const arr = Array.isArray(rawEvents) ? rawEvents : [];
    const newsRaw = arr.filter((e: any) => e?.type === 'news');
    const otherRaw = arr.filter((e: any) => e?.type !== 'news');
    if (newsRaw.length) setNews((prev) => [...prev, ...parseNews(newsRaw)].slice(-100));
    const evs = parseEvents(otherRaw);
    for (const e of evs) {
      addLog(toLogType(e.type), e.message, e.t);
      if (e.type === 'sabo' && currentBarRef.current) ctrlRef.current?.addSaboMarker(currentBarRef.current, e.ability ?? 'hit');
    }
  }, [addLog]);

  // ---- WS message handling ---------------------------------------------
  const handleMessage = useCallback((msg: any) => {
    if (!msg || typeof msg !== 'object') return;

    if (msg.type === 'snapshot') {
      gotSnapshotRef.current = true;
      const st = msg.state ?? msg;
      const yid = msg.you ?? st.you ?? 'p1';
      youRef.current = yid; setYou(yid);

      const bar = toBar(st.current_bar);
      if (bar) pushBarToChart(bar);
      const mark = bar?.close ?? STARTING_CAPITAL;

      const parsed = parsePlayersMap(st.players, mark);
      playersRef.current = parsed; setPlayers(parsed);

      setTempo(resolveTempo(st.tb, st.r ?? msg.r, yid, myLevelRef.current));
      setT(num(st.T ?? msg.t ?? bar?.time ?? 0));
      if (st.time_left != null) setTimeLeft(num(st.time_left));
      if (st.indicators) setIndicators(parseIndicators(st.indicators));

      // initial recent_events: news to panel, rest to log
      const recent = Array.isArray(st.recent_events) ? st.recent_events : [];
      setNews(parseNews(recent.filter((e: any) => e?.type === 'news')));
      setEvents(parseEvents(recent.filter((e: any) => e?.type !== 'news')).map((e) => toLog(e)).slice(-60));
      return;
    }

    if (msg.type === 'delta') {
      const bar = toBar(msg.current_bar);
      if (bar) pushBarToChart(bar);
      const mark = bar?.close ?? currentBarRef.current?.close ?? STARTING_CAPITAL;

      let next = playersRef.current;
      next = applyResources(next, msg.resources, mark);
      playersRef.current = next; setPlayers(next);

      setTempo(resolveTempo(msg.tb, msg.r, youRef.current, myLevelRef.current));
      setT(num(msg.t ?? bar?.time ?? 0));
      if (msg.time_left != null) setTimeLeft(num(msg.time_left));
      if (msg.indicators) setIndicators(parseIndicators(msg.indicators));

      const fills = parseFills(msg.fills);
      for (const f of fills) {
        const fbar = revealedBarsRef.current.find((b) => b.time === f.t) ?? currentBarRef.current;
        if (fbar) ctrlRef.current?.addFillMarker(fbar, f.side, f.player, youRef.current);
        const who = f.player === youRef.current ? 'YOU' : 'OPP';
        addLog('fill', `${who} ${String(f.side).toUpperCase()} ${f.size} @ ${f.price.toFixed(2)} (${f.type})`, f.t);
      }

      ingestEvents(msg.events);
      return;
    }

    if (msg.type === 'match_end') {
      const fin = msg.final ?? {};
      const mark = toBar(fin.current_bar)?.close ?? currentBarRef.current?.close ?? STARTING_CAPITAL;
      let finalPlayers = parsePlayersMap(fin.players, mark);
      if (Object.keys(finalPlayers).length === 0) finalPlayers = playersRef.current;
      const yid = youRef.current;
      const winner = resolveWinner(msg.winner ?? fin.winner, finalPlayers, yid);
      setEndResult({ winner, players: finalPlayers, you: yid, contentHash: msg.content_hash, reveal: msg.reveal });
      setView('ended');
      closeWs();
      return;
    }

    if (msg.type === 'voice_offer' || msg.type === 'voice_answer' || msg.type === 'voice_ice') {
      voiceHandleRef.current?.(msg.type, msg.payload);
      return;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [addLog, pushBarToChart, ingestEvents]);

  const toLog = useCallback((e: GameEvent): LogEvent => ({
    t: Math.round(e.t ?? currentBarRef.current?.time ?? 0),
    type: toLogType(e.type),
    message: e.message,
  }), []);

  const closeWs = useCallback(() => {
    if (wsRef.current) { try { wsRef.current.close(); } catch {} wsRef.current = null; }
  }, []);

  const connectWs = useCallback((info: MatchInfo) => {
    closeWs();
    modeRef.current = 'server'; setMode('server');
    youRef.current = info.you; setYou(info.you);
    setMatchInfo(info);
    setView('match');

    try {
      const ws = new WebSocket(info.wsUrl);
      wsRef.current = ws;
      ws.onopen = () => addLog('info', `Connected to match ${info.matchId} as ${info.you}${info.bot ? ' (vs bot)' : ''}`);
      ws.onmessage = (ev) => { try { handleMessage(JSON.parse(ev.data)); } catch {} };
      ws.onerror = () => addLog('info', 'WS error');
      ws.onclose = () => {
        if (wsRef.current === ws) wsRef.current = null;
        if (!gotSnapshotRef.current && modeRef.current === 'server') {
          addLog('info', 'Backend unreachable — switching to offline practice mode');
          startOffline(arenaForOffline(info.arenaId));
        }
      };
    } catch {
      startOffline(arenaForOffline(info.arenaId));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [addLog, handleMessage, closeWs]);

  const arenaForOffline = useCallback((arenaId?: string): Arena => {
    return SAMPLE_ARENAS.find((a) => a.id === arenaId) ?? SAMPLE_ARENAS[0];
  }, []);

  const sectorOf = (info: MatchInfo | null): string =>
    info?.sector ?? (info?.arenaLabel ? info.arenaLabel.split(' · ')[0] : 'Asset');

  // ---- create / join ----------------------------------------------------
  const infoFromResp = useCallback((data: any, fallbackArenaId?: string): MatchInfo => ({
    matchId: data.match_id,
    arenaId: data.arena_id ?? fallbackArenaId ?? '',
    arenaLabel: data.arena_label ?? 'Arena',
    arenaHash: data.arena_hash,
    contentHash: data.content_hash,
    numBars: data.num_bars,
    wsUrl: `${WS_BASE}/ws/${data.match_id}?player_id=p1`,
    you: 'p1',
    bot: !!data.bot,
    sector: (data.arena_label ?? '').split(' · ')[0] || undefined,
  }), []);

  const createMatch = useCallback(async (arena: Arena) => {
    setSelectedArenaId(arena.id);
    setConnecting(true);
    resetMatchState();
    try {
      const resp = await fetch(`${BACKEND_URL}/matches`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ arena_id: arena.id, player_ids: ['p1', 'p2'] }),
      });
      if (!resp.ok) throw new Error(`POST /matches ${resp.status}`);
      connectWs(infoFromResp(await resp.json(), arena.id));
    } catch {
      addLog('info', 'Backend not reachable — starting offline practice match');
      startOffline(arena);
    } finally {
      setConnecting(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [connectWs, resetMatchState, addLog, infoFromResp]);

  const quickMatch = useCallback(async () => {
    setConnecting(true);
    resetMatchState();
    try {
      const resp = await fetch(`${BACKEND_URL}/matches/quick`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vs_bot: true }),
      });
      if (!resp.ok) throw new Error(`POST /matches/quick ${resp.status}`);
      const data = await resp.json();
      setSelectedArenaId(data.arena_id);
      connectWs(infoFromResp(data));
    } catch {
      addLog('info', 'Backend not reachable — starting offline practice match');
      startOffline(SAMPLE_ARENAS[Math.floor(Date.now() / 1000) % SAMPLE_ARENAS.length]);
    } finally {
      setConnecting(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [connectWs, resetMatchState, addLog, infoFromResp]);

  const joinExisting = useCallback(() => {
    const id = joinId.trim();
    if (!id) return;
    resetMatchState();
    connectWs({
      matchId: id, arenaId: '', arenaLabel: `Match ${id}`,
      wsUrl: `${WS_BASE}/ws/${id}?player_id=${joinAs}`, you: joinAs,
    });
  }, [joinId, joinAs, connectWs, resetMatchState]);

  // ---- offline practice simulation -------------------------------------
  const startOffline = useCallback((arena: Arena) => {
    resetMatchState();
    modeRef.current = 'offline'; setMode('offline');
    youRef.current = 'p1'; setYou('p1');
    const bars = (arena.bars && arena.bars.length ? arena.bars : SAMPLE_ARENAS[0].bars);
    offlineBarsRef.current = bars;
    offlineIdxRef.current = 0;
    const first = bars[0];
    const initPlayers: Record<string, PlayerState> = {
      p1: { id: 'p1', ip: 50, equity: STARTING_CAPITAL, pnl: 0, unrealized: 0, tb: 100, positions: [], orders: [], buyingPower: 300, exposure: 0 },
      p2: { id: 'p2', ip: 50, equity: STARTING_CAPITAL, pnl: 0, unrealized: 0, tb: 100, positions: [], orders: [] },
    };
    playersRef.current = initPlayers; setPlayers(initPlayers);
    setMatchInfo({ matchId: 'offline', arenaId: arena.id, arenaLabel: arena.name, wsUrl: '', you: 'p1', numBars: bars.length, sector: arena.ticker });
    setTempo({ R: 1, contested: false, myLevel: 'base' });
    setView('match');
    if (first) pushBarToChart(first);
    setT(first?.time ?? 0);
    addLog('info', `Offline practice: ${arena.name} (${bars.length} bars). Tempo controls drive a local timer.`);
  }, [resetMatchState, pushBarToChart, addLog]);

  const recomputeOfflinePlayers = useCallback((bar: Bar) => {
    setPlayers((prev) => {
      const base = prev.p1 ?? playersRef.current.p1;
      if (!base) return prev;
      const unreal = base.positions.reduce((acc, p) => {
        const dir = p.side === 'long' ? 1 : -1;
        return acc + (p.entry ? p.size * dir * (bar.close - p.entry) / p.entry : 0);
      }, 0);
      const equity = STARTING_CAPITAL + offlineRealizedRef.current + unreal;
      const ip = Math.min(200, base.ip + 0.5);
      const exposure = base.positions.reduce((a, p) => a + Math.abs(p.size), 0);
      const first = offlineBarsRef.current[0]?.close ?? bar.close;
      const oppEquity = STARTING_CAPITAL + ((bar.close / first) - 1) * 100 * 0.6;
      const next: Record<string, PlayerState> = {
        p1: { ...base, ip, unrealized: unreal, equity, pnl: equity - STARTING_CAPITAL, exposure, buyingPower: Math.max(0, equity * 3) },
        p2: { ...(prev.p2 ?? playersRef.current.p2), id: 'p2', equity: oppEquity, pnl: oppEquity - STARTING_CAPITAL, unrealized: 0, positions: [], orders: [], ip: 50, tb: 100 },
      };
      playersRef.current = next;
      return next;
    });
  }, []);

  const endOffline = useCallback(() => {
    const fin = playersRef.current;
    const winner = resolveWinner(undefined, fin, 'p1');
    setEndResult({ winner, players: fin, you: 'p1' });
    setView('ended');
  }, []);

  // offline advance timer — only runs in offline mode while not paused (R>0)
  useEffect(() => {
    if (view !== 'match' || mode !== 'offline') return;
    if (tempo.R <= 0) return; // PAUSE freezes the clock
    const ms = Math.max(120, Math.floor(OFFLINE_BASE_MS / tempo.R));
    const id = setInterval(() => {
      const bars = offlineBarsRef.current;
      const nextIdx = offlineIdxRef.current + 1;
      if (nextIdx >= bars.length) { endOffline(); return; }
      offlineIdxRef.current = nextIdx;
      const bar = bars[nextIdx];
      pushBarToChart(bar);
      setT(bar.time);
      recomputeOfflinePlayers(bar);
    }, ms);
    return () => clearInterval(id);
  }, [view, mode, tempo.R, pushBarToChart, recomputeOfflinePlayers, endOffline]);

  // ---- equity curve sampling -------------------------------------------
  useEffect(() => {
    if (view !== 'match') return;
    const eq = players[you]?.equity;
    if (eq == null) return;
    const arr = equityCurveRef.current;
    if (arr.length === 0 || Math.abs(arr[arr.length - 1] - eq) > 1e-6) {
      equityCurveRef.current = [...arr, eq].slice(-120);
      setEquityCurve(equityCurveRef.current);
    }
  }, [players, you, view]);

  // ---- TP/SL/entry price lines on the chart ----------------------------
  useEffect(() => {
    const ctrl = ctrlRef.current;
    if (!ctrl || view !== 'match') return;
    const me = players[you];
    const desired = new Map<string, { price: number; color: string; title: string }>();
    if (me) {
      for (const pos of me.positions) {
        if (pos.entry) desired.set(`entry:${pos.instr}`, { price: pos.entry, color: '#6b7280', title: `Entry ${pos.entry.toFixed(2)}` });
      }
      for (const o of me.orders) {
        const isTp = o.kind === 'tp' || (o.reduceOnly && o.type === 'limit');
        const isSl = o.kind === 'sl' || (o.reduceOnly && o.type === 'stop');
        if (isTp && o.price != null) desired.set(`tp:${o.id}`, { price: o.price, color: '#22c55e', title: `TP ${o.price.toFixed(2)}` });
        else if (isSl && o.price != null) desired.set(`sl:${o.id}`, { price: o.price, color: '#ef4444', title: `SL ${o.price.toFixed(2)}` });
        else if (o.price != null) desired.set(`ord:${o.id}`, { price: o.price, color: '#3b82f6', title: `${String(o.type).toUpperCase()} ${o.price.toFixed(2)}` });
        if (o.tp != null) desired.set(`tpp:${o.id}`, { price: o.tp, color: '#22c55e', title: `TP ${o.tp.toFixed(2)}` });
        if (o.sl != null) desired.set(`slp:${o.id}`, { price: o.sl, color: '#ef4444', title: `SL ${o.sl.toFixed(2)}` });
      }
    }
    const prev = priceLinesRef.current;
    for (const id of prev) if (!desired.has(id)) ctrl.removePriceLine(id);
    for (const [id, v] of desired) ctrl.addPriceLine(v.price, v.title, v.color, id);
    priceLinesRef.current = new Set(desired.keys());
  }, [players, you, currentBar, view]);

  // ---- player actions ---------------------------------------------------
  const handleTempo = useCallback((level: TempoLevel) => {
    myLevelRef.current = level;
    if (modeRef.current === 'server') {
      sendWSAction('tb_influence', { level });
      setTempo((prev) => ({ ...prev, myLevel: level, R: prev.contested ? prev.R : levelToR(level) }));
    } else {
      setTempo({ R: levelToR(level), contested: false, myLevel: level });
    }
    addLog('tb', level === 'pause' ? 'Hold PAUSE (R=0)' : level === 'base' ? 'Release to 1×' : `Push ${level.toUpperCase()}`);
  }, [sendWSAction, addLog]);

  const opponentId = useCallback(() => {
    const o = otherPlayer(playersRef.current, youRef.current);
    return o?.id ?? (youRef.current === 'p1' ? 'p2' : 'p1');
  }, []);

  const handleOrder = useCallback((ord: OrderRequest) => {
    const bar = currentBarRef.current;
    const fillPrice = ord.price ?? bar?.close ?? 100;
    if (modeRef.current === 'server') {
      sendWSAction('submit_order', {
        type: ord.type, instr: 'X', side: ord.side, size: ord.size,
        ...(ord.price != null ? { price: ord.price } : {}),
        ...(ord.tp != null ? { tp: ord.tp } : {}),
        ...(ord.sl != null ? { sl: ord.sl } : {}),
      });
    }
    if (bar) ctrlRef.current?.addFillMarker(bar, ord.side, youRef.current, youRef.current, `${ord.side === 'long' ? 'BUY' : 'SELL'} ${ord.size}`);
    if (ord.type === 'market' && bar) {
      setPlayers((prev) => {
        const me = prev[youRef.current];
        if (!me) return prev;
        const next = { ...prev, [youRef.current]: { ...me, positions: [...me.positions, { instr: 'X', side: ord.side, size: ord.size, entry: fillPrice }] } };
        playersRef.current = next;
        return next;
      });
    }
    addLog('order', `${String(ord.side).toUpperCase()} ${ord.size} ${ord.type} @ ~${fillPrice.toFixed(2)}${ord.tp || ord.sl ? ' +bracket' : ''}`);
  }, [sendWSAction, addLog]);

  const handleClose = useCallback((instr: string, fraction: number) => {
    if (modeRef.current === 'server') {
      sendWSAction('close', { instr, fraction });
    } else {
      // offline: realize a fraction and shrink/remove the local position
      setPlayers((prev) => {
        const me = prev[youRef.current];
        if (!me) return prev;
        const bar = currentBarRef.current;
        const positions = me.positions.flatMap((p) => {
          if (p.instr !== instr) return [p];
          const dir = p.side === 'long' ? 1 : -1;
          const up = p.entry && bar ? p.size * dir * (bar.close - p.entry) / p.entry : 0;
          offlineRealizedRef.current += up * fraction;
          const remaining = p.size * (1 - fraction);
          return remaining > 0.0001 ? [{ ...p, size: remaining }] : [];
        });
        const next = { ...prev, [youRef.current]: { ...me, positions } };
        playersRef.current = next;
        return next;
      });
    }
    addLog('order', `Close ${fraction >= 1 ? 'all' : `${Math.round(fraction * 100)}%`} ${instr}`);
  }, [sendWSAction, addLog]);

  const handleSetBracketLeg = useCallback((instr: string, kind: 'tp' | 'sl', price: number) => {
    const me = playersRef.current[youRef.current];
    const existing = me?.orders.find((o) => o.instr === instr && (o.kind === kind || (o.reduceOnly && o.type === (kind === 'tp' ? 'limit' : 'stop'))));
    const pos = me?.positions.find((p) => p.instr === instr);
    if (modeRef.current === 'server') {
      if (existing?.id != null) {
        sendWSAction('modify_order', { id: existing.id, price });
      } else if (pos) {
        // create a fresh reduce-only-style leg opposite the position
        const exitSide = (pos.side === 'long') ? 'short' : 'long';
        sendWSAction('submit_order', { type: kind === 'tp' ? 'limit' : 'stop', instr, side: exitSide, size: Math.abs(pos.size), price });
      }
    }
    addLog('order', `Set ${kind.toUpperCase()} ${instr} @ ${price.toFixed(2)}`);
  }, [sendWSAction, addLog]);

  const handleCancelOrder = useCallback((id: string) => {
    if (modeRef.current === 'server') sendWSAction('cancel_order', { id });
    else setPlayers((prev) => {
      const me = prev[youRef.current];
      if (!me) return prev;
      const next = { ...prev, [youRef.current]: { ...me, orders: me.orders.filter((o) => String(o.id) !== id) } };
      playersRef.current = next; return next;
    });
    addLog('order', `Cancel order ${id}`);
  }, [sendWSAction, addLog]);

  const handleSabo = useCallback((a: Ability) => {
    const target = a.ability === 'peek' ? youRef.current : opponentId();
    if (modeRef.current === 'server') {
      sendWSAction('ip_spend', { cost: a.cost, ability: a.ability, target_player: target });
    }
    setPlayers((prev) => {
      const me = prev[youRef.current];
      if (!me) return prev;
      const next = { ...prev, [youRef.current]: { ...me, ip: Math.max(0, me.ip - a.cost) } };
      playersRef.current = next;
      return next;
    });
    if (a.ability !== 'peek' && currentBarRef.current) ctrlRef.current?.addSaboMarker(currentBarRef.current, a.ability);
    addLog(a.ability === 'peek' ? 'peek' : 'sabo', `${a.label} (-${a.cost} IP)`);
  }, [sendWSAction, addLog, opponentId]);

  // ---- navigation -------------------------------------------------------
  const exitToLobby = useCallback(() => {
    closeWs();
    voice.stop();
    setView('lobby');
    setMatchInfo(null);
    resetMatchState();
  }, [closeWs, voice, resetMatchState]);

  const rematch = useCallback(() => {
    const arenaId = matchInfo?.arenaId;
    const arena = arenas.find((a) => a.id === arenaId) ?? arenaForOffline(arenaId);
    setView('lobby');
    setEndResult(null);
    setTimeout(() => createMatch(arena), 50);
  }, [matchInfo, arenas, arenaForOffline, createMatch]);

  // ---- derived ----------------------------------------------------------
  const me = players[you] ?? null;
  const opp = otherPlayer(players, you);
  const lastClose = currentBar?.close ?? 100;
  const clockColor = timeLeft <= 30 ? '#ef4444' : timeLeft <= 60 ? '#eab308' : '#9ca3af';

  return (
    <div className="min-h-screen pvp-container">
      <header className="border-b border-[#2a313a] bg-[#0a0c10]/95 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="font-semibold tracking-[-1px] text-lg">chart-fights</div>
            {mode === 'offline' && view !== 'lobby' && <div className="text-[10px] px-2 py-0.5 rounded bg-[#eab308]/10 text-[#eab308]">OFFLINE</div>}
          </div>
          <div className="flex items-center gap-4 text-xs text-[#9ca3af]">
            {view === 'match' && (
              <span className="font-mono text-sm font-semibold" style={{ color: clockColor }}>⏱ {fmtClock(timeLeft)}</span>
            )}
            {view !== 'lobby' && matchInfo && (
              <>
                <span className="hidden sm:inline">{matchInfo.arenaLabel}</span>
                {matchInfo.bot && <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#3b82f6]/15 text-[#3b82f6]">vs BOT</span>}
                <span className="font-mono text-[10px] text-[#6b7280]">{matchInfo.matchId}</span>
                <button onClick={exitToLobby} className="underline">← LOBBY</button>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6">
        {view === 'lobby' && (
          <div className="space-y-8">
            <div className="max-w-2xl">
              <h1 className="text-4xl font-semibold tracking-tighter">1v1 me in stocks bro.</h1>
              <p className="mt-2 text-lg text-[#9ca3af]">Same normalized chart slice. Shared contested clock. Sabotage. Voice. 5 real minutes.</p>
              <button onClick={quickMatch} disabled={connecting}
                className={`mt-4 px-5 py-2.5 rounded-lg font-semibold text-black ${connecting ? 'bg-[#272d37] text-[#6b7280] cursor-wait' : 'bg-[#22c55e] hover:bg-[#16a34a]'}`}>
                ⚡ {connecting ? 'Matching…' : 'Quick Match'}
              </button>
              <span className="ml-3 text-xs text-[#6b7280]">random arena · vs bot if no human joins</span>
            </div>
            <ArenaLobby arenas={arenas} onSelect={createMatch} selectedId={selectedArenaId} connecting={connecting} />
            {loadingArenas && <div className="text-xs text-[#6b7280]">Loading arenas from {BACKEND_URL}/arenas…</div>}

            <div className="panel p-4 max-w-md">
              <div className="text-sm font-medium mb-1">Join an existing match</div>
              <div className="text-xs text-[#9ca3af] mb-3">Open a match on another tab/browser, copy its match id, and join as the second player.</div>
              <div className="flex gap-2">
                <input
                  value={joinId}
                  onChange={(e) => setJoinId(e.target.value)}
                  placeholder="match_id"
                  className="flex-1 bg-[#0b0e14] border border-[#2a313a] px-2 py-1.5 rounded text-sm font-mono"
                />
                <select value={joinAs} onChange={(e) => setJoinAs(e.target.value as 'p1' | 'p2')} className="bg-[#0b0e14] border border-[#2a313a] px-2 py-1.5 rounded text-sm">
                  <option value="p2">as p2</option>
                  <option value="p1">as p1</option>
                </select>
                <button onClick={joinExisting} className="px-3 py-1.5 rounded bg-white text-black text-sm font-medium hover:bg-[#e5e7eb]">JOIN</button>
              </div>
            </div>

            <div className="text-xs text-[#6b7280] max-w-prose">
              Backend: {BACKEND_URL}. Instruments are shown by sector only (real symbol revealed post-match). The chart reveals bars as the server advances T. If the backend is unreachable, an offline practice match runs locally.
            </div>
          </div>
        )}

        {view === 'match' && matchInfo && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            <div className="lg:col-span-8 space-y-3">
              <div className="match-header pb-2 flex items-center justify-between">
                <div>
                  <div className="font-semibold">{matchInfo.arenaLabel}</div>
                  <div className="text-xs text-[#9ca3af]">normalized • Sim Day {Math.round(T)} • you are {you}</div>
                </div>
                <div className="flex items-center gap-1.5 text-sm">
                  <button onClick={() => handleTempo('pause')} className={`px-3 py-1 rounded border ${tempo.myLevel === 'pause' ? 'border-[#eab308] text-[#eab308]' : 'border-[#2a313a] hover:bg-[#1a1f26]'}`}>⏸ PAUSE</button>
                  {(['base', 'ff2', 'ff3', 'ff5'] as TempoLevel[]).map((l) => (
                    <button key={l} onClick={() => handleTempo(l)} className={`px-2 py-1 rounded border ${tempo.myLevel === l ? 'border-[#ef4444] text-[#ef4444]' : 'border-[#2a313a] hover:bg-[#1a1f26]'}`}>
                      {l === 'base' ? '1×' : `×${levelToR(l)}`}
                    </button>
                  ))}
                </div>
              </div>
              <ChartView onControllerReady={handleCtrl} R={tempo.R} contested={tempo.contested} T={T} paused={tempo.R <= 0} />
              <IndicatorPanel indicators={indicators} />
              <NewsFeed items={news} />
            </div>

            <div className="lg:col-span-4 space-y-3">
              <Scoreboard you={me} opp={opp} curve={equityCurve} />
              <ResourceBars tb={me?.tb ?? 100} ip={me?.ip ?? 0} R={tempo.R} contested={tempo.contested} myLevel={tempo.myLevel} onTempo={handleTempo} />
              <OrderPanel onPlaceOrder={handleOrder} currentPrice={lastClose} buyingPower={me?.buyingPower} exposure={me?.exposure} />
              <PositionsTable
                me={me}
                markPrice={lastClose}
                sector={sectorOf(matchInfo)}
                onClose={handleClose}
                onSetBracketLeg={handleSetBracketLeg}
                onCancelOrder={handleCancelOrder}
              />
              <SaboPanel ip={me?.ip ?? 0} onCast={handleSabo} />
              <VoicePanel status={voice.status} micOn={voice.micOn} remoteActive={voice.remoteActive} errorMsg={voice.errorMsg} onStart={voice.start} onStop={voice.stop} onToggleMic={voice.toggleMic} />
              <EventLog events={events} />
            </div>
          </div>
        )}

        {view === 'ended' && endResult && (
          <EndScreen result={endResult} onRematch={rematch} onLobby={exitToLobby} />
        )}
      </main>

      <footer className="text-center text-[10px] py-6 text-[#6b7280] border-t border-[#2a313a]">
        chart-fights • progressive server-revealed chart • TB/IP/sabotage/voice • brackets · drawings · news
      </footer>
    </div>
  );
}

// Decide the winner by highest final equity (server `winner` wins if provided).
function resolveWinner(serverWinner: string | undefined, players: Record<string, PlayerState>, _you: string): string | null {
  if (serverWinner) return serverWinner;
  const ids = Object.keys(players);
  if (ids.length < 1) return null;
  let best: string | null = null;
  let bestEq = -Infinity;
  let tie = false;
  for (const id of ids) {
    const eq = players[id].equity;
    if (eq > bestEq) { bestEq = eq; best = id; tie = false; }
    else if (eq === bestEq) { tie = true; }
  }
  return tie ? null : best;
}
