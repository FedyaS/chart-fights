'use client';

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { ArenaLobby } from '../components/ArenaLobby';
import { ChartView } from '../components/ChartView';
import { ResourceBars } from '../components/ResourceBars';
import { SaboPanel } from '../components/SaboPanel';
import { OrderPanel } from '../components/OrderPanel';
import { VoicePanel } from '../components/VoicePanel';
import { EventLog } from '../components/EventLog';
import { SAMPLE_ARENAS } from '../lib/sampleArenas';
import type { Arena, LogEvent, Bar } from '../types';

// Config: native WS to backend. ws://localhost:8000/ws/{match} (or NEXT_PUBLIC_BACKEND_URL for Fly)
// (In GameUI/ReplayController equivalent: connect, deltas for tb/ip/current bar, pass to series.update + range)
const BACKEND_URL = typeof window !== 'undefined' ? ((window as any).CHART_BACKEND || (process as any)?.env?.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000') : 'http://localhost:8000';
const WS_BASE = BACKEND_URL.replace('https:', 'wss:').replace('http:', 'ws:');

export default function ChartFightsApp() {
  const [matchState, setMatchState] = useState<'lobby' | 'match'>('lobby');
  const [selectedArena, setSelectedArena] = useState<Arena | null>(null);
  const [currentBars, setCurrentBars] = useState<Bar[]>([]);
  // Real WS match state (per user task + GDD): connect ws://.../ws/{match}, deltas update tb/ip/T
  const [matchId, setMatchId] = useState<string | null>(null);
  const [serverT, setServerT] = useState<number>(0);
  const wsRef = useRef<WebSocket | null>(null);
  const [realArenas, setRealArenas] = useState<any[]>([]);
  const [isConnecting, setIsConnecting] = useState(false);
  const [loadingArenas, setLoadingArenas] = useState(false);

  const [tb, setTb] = useState(82); const [ip, setIp] = useState(64); const [currentR, setCurrentR] = useState(1);
  const [events, setEvents] = useState<LogEvent[]>([]);
  const [ctrl, setCtrl] = useState<any>(null);
  const [pendingMarkers, setPendingMarkers] = useState<any[]>([]); const [pendingSabo, setPendingSabo] = useState<any[]>([]);
  const [displayT, setDisplayT] = useState(0);

  const addLog = useCallback((type: LogEvent['type'], message: string, t = 0) => { setEvents(p => [...p, { t: t || (ctrl?.currentIndex || 0), type, message }].slice(-30)); }, [ctrl]);

  // Load real arena list from /arenas (GDD lobby + task-007)
  useEffect(() => {
    setLoadingArenas(true); // note: declare loading if want spinner, stub ok
    fetch(`${BACKEND_URL}/arenas`).then(r => r.json()).then(d => {
      const list = (d.arenas || []).map((a: any) => ({ id: a.id, name: `${a.ticker || a.id} Arena`, ticker: a.ticker, description: `bars:${a.bars || '?'}`, bars: [] }));
      setRealArenas(list.length ? list : SAMPLE_ARENAS.map(a => ({...a, bars: a.bars})));
    }).catch(() => setRealArenas(SAMPLE_ARENAS)).finally(() => setLoadingArenas(false));
  }, []);

  // Helper to send WS action (tempo influence, ip_spend)
  const sendWSAction = (actionType: string, payload: any) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'action', action_type: actionType, payload }));
    }
  };

  // Create real match + connect WS native. Mock equity from deltas for now.
  const startRealMatch = async (arena: any) => {
    const arenaId = arena.id || 'AAPL_00000';
    setIsConnecting(true);
    try {
      // 1. POST /matches to get id (GDD flow)
      const resp = await fetch(`${BACKEND_URL}/matches`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ arena_id: arenaId, player_ids: ['p1'] }),
      });
      const data = await resp.json();
      const mId = data.match_id;
      setMatchId(mId);

      // Use real-ish bars: match sample or default
      let barsForChart: Bar[] = (arena.bars && arena.bars.length) ? arena.bars : [];
      if (!barsForChart.length) {
        const matchSample = SAMPLE_ARENAS.find(s => s.id === arenaId) || SAMPLE_ARENAS[0];
        barsForChart = matchSample.bars as any;
      }
      setSelectedArena({ ...(arena as Arena), name: arena.name || arenaId, bars: barsForChart as any });
      setCurrentBars(barsForChart as any);
      setMatchState('match');
      setTb(50); setIp(50); setCurrentR(1); setServerT(0); setEvents([]);

      // 2. Connect native WS ws://.../ws/{match}?player_id=p1
      const wsUrl = `${WS_BASE}/ws/${mId}?player_id=p1`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        addLog('info', `WS connected to match ${mId}`);
      };

      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type === 'snapshot' || msg.type === 'delta') {
            const t = typeof msg.t === 'number' ? msg.t : (msg.state?.T ?? serverT);
            setServerT(t);
            // Update state from delta (tb, ip, current bar T)
            if (msg.resources) {
              // resources {p1: {ip, equity}, ...}
              const p = msg.resources.p1 || Object.values(msg.resources)[0] as any;
              if (p) {
                if (typeof p.ip === 'number') setIp(Math.floor(p.ip));
                // equity mock for now
              }
            }
            if (msg.r != null) setCurrentR(msg.r);
            if (msg.tb && msg.tb.tbs) {
              // server tb snapshot per player
              const myTb = msg.tb.tbs.p1 || Object.values(msg.tb.tbs)[0];
              if (typeof myTb === 'number') setTb(myTb);
            }
            // Pass real updates to Replay: use updateFromServer or T drive
            if (ctrl && ctrl.updateFromServer && currentBars.length) {
              const barIdx = Math.floor(t);
              const bar = currentBars[barIdx] || currentBars[currentBars.length-1];
              if (bar) ctrl.updateFromServer(barIdx, bar);
            }
            addLog('info', `Delta T=${t.toFixed(1)} R=${msg.r ?? currentR}`);
          } else if (msg.type === 'match_end') {
            addLog('info', 'Match ended');
          }
        } catch {}
      };

      ws.onclose = () => { addLog('info', 'WS closed'); wsRef.current = null; };
      ws.onerror = () => addLog('info', 'WS error (fall to mock)');

      // Send initial if needed
    } catch (e) {
      addLog('info', 'Backend not reachable, using local match');
      // Fallback to local sample
      setSelectedArena(arena); setCurrentBars(arena.bars || SAMPLE_ARENAS[0].bars); setMatchState('match');
    } finally {
      setIsConnecting(false);
    }
  };

  const enterMatch = (arena: Arena) => {
    // Real path: create match then WS (GDD lobby flow)
    startRealMatch(arena);
  };
  const exitToLobby = () => {
    setMatchState('lobby'); setMatchId(null); setServerT(0);
    if (wsRef.current) { try { wsRef.current.close(); } catch {} wsRef.current = null; }
    if (ctrl) ctrl.pause(); setCtrl(null);
  };

  const handlePlay = () => { if (ctrl) { ctrl.play(); setCurrentR(ctrl.speed); addLog('tb', `Play @ ${ctrl.speed}x`); } };
  const handlePause = () => { if (ctrl) { ctrl.pause(); setCurrentR(0); addLog('tb', 'Paused'); setTb(v => Math.min(100, v + 6)); } };
  const handleSpeed = (s: number) => { if (ctrl) { ctrl.setSpeed(s); setCurrentR(s); addLog('tb', `Set speed ×${s}`); setTb(v => Math.max(0, v - (s > 1 ? 3 : 0))); } };
  const handleTBAction = (mult?: number) => { if (!ctrl) return; const lvl = mult ? (mult===2?'ff2':mult===3?'ff3':mult===5?'ff5':'base') : 'pause'; sendWSAction('tb_influence', {level: lvl}); if (mult) { ctrl.setSpeed(mult); setCurrentR(mult); setTb(v => Math.max(0, v - (mult===5?14:mult===3?7:3))); addLog('tb', `FF ×${mult} [WS sent]`); } else { ctrl.pause(); setCurrentR(0); setTb(v => Math.min(100, v + 7)); addLog('tb', 'Pause [WS sent]'); } };
  const handleOrder = (ord: any) => {
    const t = ctrl?.currentIndex || 0; const price = ord.price || (currentBars[t]?.close || 100);
    sendWSAction('submit_order', {
      type: ord.type,
      instr: 'X',
      side: ord.side,
      size: ord.size,
      ...(ord.price != null ? { price: ord.price } : {}),
    });
    addLog('order', `${ord.side} ${ord.size} @${price.toFixed(2)} (${ord.type}) [WS sent]`, t);
    if (ctrl && currentBars[t]) { const isB = ord.side==='long'; ctrl.addPlayerMarker(t, isB, 'p1'); ctrl.addPriceLine(price*(isB?0.985:1.015), isB?'ENTRY':'SHORT', isB?'#22c55e':'#ef4444'); }
    setIp(v => Math.min(120, v+1));
  };
  const handleSabo = (action: string, cost: number) => {
    if (ip < cost) return; const t = ctrl?.currentIndex || 0; setIp(v => Math.max(0, v-cost)); addLog('sabo', `${action} (-${cost}IP)`, t);
    // Send real sabo via ip_spend (keep UI)
    sendWSAction('ip_spend', { cost, ability: action.includes('sl') ? 'delete_sl' : action.includes('news') ? 'fake_news' : 'widen', target_player: 'p2' });
    if (ctrl && currentBars[t]) { ctrl.addSaboMarker(t, action.slice(0,8)); if (action.includes('sl')||action.includes('spread')) ctrl.addPriceLine((currentBars[t].close||100)*0.97, 'SABO', '#a855f7'); }
    setTb(v => Math.max(0, v-3));
  };
  const handleMic = (on: boolean) => addLog('voice', on?'Mic on':'Mic off');
  const handlePTT = (d: boolean) => { if (d) addLog('voice', 'PTT'); };
  const handleIndex = (i: number) => setDisplayT(i);
  const handleCtrl = (c: any) => { setCtrl(c); setCurrentR(c.speed || 1); /* c.updateFromServer available for real bars from deltas */ };

  React.useEffect(() => { if (!ctrl?.isPlaying) return; const id = setInterval(() => { setTb(v => Math.max(5, v - (currentR>1?1:0.4))); setIp(v => Math.min(120,v+0.1)); }, 1400); return () => clearInterval(id); }, [ctrl?.isPlaying, currentR]);

  return (
    <div className="min-h-screen pvp-container">
      <header className="border-b border-[#2a313a] bg-[#0a0c10]/95 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3"><div className="font-semibold tracking-[-1px] text-lg">chart-fights</div><div className="text-[10px] px-2 py-0.5 rounded bg-[#ef4444]/10 text-[#ef4444]">MVP SKELETON</div></div>
          <div className="flex items-center gap-4 text-xs text-[#9ca3af]">{matchState==='match' && selectedArena && <><span>{selectedArena.name}</span><button onClick={exitToLobby} className="underline">← LOBBY</button></>}<span className="hidden sm:inline">1v1 historical duels • TB/IP • sabo • voice</span></div>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-4 py-6">
        {matchState === 'lobby' && (
          <div className="space-y-8">
            <div className="max-w-2xl"><h1 className="text-4xl font-semibold tracking-tighter">1v1 me in stocks bro.</h1><p className="mt-2 text-lg text-[#9ca3af]">Same normalized chart slice. Shared contested clock. Sabotage. Voice. 5 real minutes.</p></div>
            <ArenaLobby arenas={(realArenas.length ? realArenas : SAMPLE_ARENAS) as any} onSelect={enterMatch} />
            {loadingArenas && <div className="text-xs">Loading arenas from /arenas...</div>}
            <div className="text-xs text-[#6b7280] max-w-prose">/arenas + /matches + native WS ws://.../ws/{matchId}. ReplayController series.update() + range from server deltas. TB/IP/sabo/tempo wired to WS sends. Per GDD+tasks(007,002). Config for Fly.</div>
          </div>
        )}
        {matchState === 'match' && selectedArena && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            <div className="lg:col-span-8 space-y-3">
              <div className="match-header pb-2 flex items-center justify-between">
                <div><div className="font-semibold">{selectedArena.name}</div><div className="text-xs text-[#9ca3af]">{selectedArena.ticker} • normalized • Sim Day {displayT}</div></div>
                <div className="flex items-center gap-1.5 text-sm">
                  <button onClick={handlePause} className="px-3 py-1 rounded border border-[#2a313a] hover:bg-[#1a1f26]">⏸ PAUSE</button>
                  <button onClick={handlePlay} className="px-3 py-1 rounded border border-[#2a313a] bg-white text-black font-medium hover:bg-[#e5e7eb]">▶ PLAY</button>
                  {[1,2,3,5].map(s => <button key={s} onClick={() => handleSpeed(s)} className={`px-2 py-1 rounded border ${currentR===s ? 'border-[#ef4444] text-[#ef4444]' : 'border-[#2a313a] hover:bg-[#1a1f26]'}`}>{s}×</button>)}
                  <button onClick={() => ctrl?.reset()} className="text-xs px-2 py-1 underline">RESET</button>
                </div>
              </div>
              <ChartView bars={currentBars} onControllerReady={handleCtrl} externalMarkers={pendingMarkers} externalSabo={pendingSabo} onIndexChange={handleIndex} serverT={serverT} />
              <div className="flex gap-2 text-[11px] text-[#9ca3af]"><div>Logical replay • update() streaming • markers + priceLines</div><div className="flex-1" /><div>T={displayT} • R={currentR}</div></div>
            </div>
            <div className="lg:col-span-4 space-y-3">
              <ResourceBars tb={tb} ip={ip} currentR={currentR} onPause={() => handleTBAction()} onFF={(m)=>handleTBAction(m)} />
              <SaboPanel ip={ip} onSabo={handleSabo} />
              <OrderPanel onPlaceOrder={handleOrder} currentPrice={currentBars[displayT]?.close} />
              <VoicePanel onToggleMic={handleMic} onPTT={handlePTT} />
              <EventLog events={events} />
            </div>
            <div className="lg:col-span-12 pt-2 text-[10px] text-[#6b7280] border-t border-[#2a313a]">Real WS connected (native) to backend. Deltas update TB/IP/T → ReplayController series.update + range. /arenas + /matches used. Mock equity. GDD flow.</div>
          </div>
        )}
      </main>
      <footer className="text-center text-[10px] py-6 text-[#6b7280] border-t border-[#2a313a]">chart-fights • WS to localhost:8000 or Fly via NEXT_PUBLIC_BACKEND_URL • GDD + task-007/002</footer>
    </div>
  );
}
