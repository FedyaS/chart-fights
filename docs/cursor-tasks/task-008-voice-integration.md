# Cursor Agent Task: Voice Integration (WebRTC or 3rd-party Fallback) + Chat Polish

**Context**: Chart-Fights. References:
- docs/design/architecture-overview.md (voice section)
- docs/design/game-mechanics-spec.md (voice + text chat as core psychological layer)
- docs/design/GDD.md (social layer, voice for trash talk/mind games)

**Goal**: Add voice chat using WebRTC (P2P with WS signaling) or easy 3rd-party fallback (Twilio/Agora). Integrate with existing text chat and match UI. Ensure low latency (<150ms target), reliable join, push-to-talk/mute, text fallback.

## Requirements (from specs + arch)
- Signaling over the match WebSocket room (reuse task-005 backend).
- WebRTC for direct P2P audio between the two players.
- UI controls: Mute, push-to-talk, volume per player, disconnect fallback.
- If WebRTC fails (NAT issues), seamless fallback to 3rd-party provider.
- Text chat polish: Timestamps, emoji quick reactions, scroll to latest.
- Permissions: Browser mic access prompt on match start.
- Accessibility: Clear visual indicators when speaking.

**MVP Scope**: 1v1 only. Text-first if voice not ready. No recording/post-match voice log yet (Phase 4).

**Non-goals**: Full spectator voice, mobile optimization, advanced audio effects.

## Acceptance Criteria
1. WebRTC peer connection setup with WS signaling (offer/answer/ICE).
2. Audio stream capture and playback with controls.
3. Fallback logic to 3rd-party if P2P fails (configurable).
4. Integrated UI in match screen (voice panel next to text chat).
5. Text chat enhancements (reactions, better UX).
6. Tests for connection states and fallback.
7. Graceful handling of mic permission denial (fall back to text + notify).

## Cursor Agent Prompt (copy-paste ready)
"Implement voice integration for Chart-Fights per docs/cursor-tasks/task-008-voice-integration.md + architecture-overview.md voice section + game-mechanics-spec.md.

Add WebRTC (P2P with existing match WS for signaling) or configurable 3rd-party fallback. Include mic controls, mute, PTT, per-player volume. Polish the text chat with reactions and timestamps. Make it reliable for 1v1 with <150ms target latency. Follow the 'psychological warfare' and 'trash talk' emphasis from the vision.

Reuse the match WS room from the realtime backend. Provide clear fallback and error UX. No recording in MVP."

## Integration Notes
- Depends on task-005 (WS room/signaling).

**Fresh WebRTC + Psych UX Sub Research (sub 019f05db... 86s complete, 2026-06-26)**:
Key excerpts for task-008 handoff (full transcript in sub/STATUS):
- WS signaling (FastAPI/Starlette): Extend match rooms (offer/answer/ICE JSON forward; RoomManager broadcast exclude sender; reuse /ws/{match_id}). "Signaling is not media—dumb forwarder." Perfect negotiation (polite/impolite) for collisions. Trickle ICE.
- P2P WebRTC: RTCPeerConnection + getUserMedia({audio: {echoCancellation:true,...}}). Opus codec (20-64kbps, FEC/DTX). onicecandidate, ontrack, onconnectionstatechange. Start offer/answer flow on match join.
- STUN/TURN: Coturn self-host primary (ephemeral creds server-gen, regional VPS) + Twilio/Agora configurable fallback. NAT: ~15-30% need relay. Prioritize UDP; test home/corp/mobile.
- Latency: <150ms target (conversational; direct P2P sub-60 possible; Opus + low jitter). Monitor iceConnectionState/getStats; fallback on failed/disconnected/high loss.
- Fallback + perms: On NotAllowedError or fail: disable audio, show "Voice unavailable (text only)", notify; seamless continue text (already WS).
- Psych/trash talk UX (FXR validated "mental warfare"): Tie voice to game events (sabo notifies, TB holds, peeks). Taunts e.g. "Nice SLs...?" on delete-SL event; "Holding pause? Scared?" during R=0. VAD/WebAudio speaking indicators + visual pulses next to chat. PTT/mute/volume per-player. Emoji reactions in text sync with voice moments. VoicePanel sidebar next to TextChat (Zustand + WS). Opt-in, accessible.
- UI: Controls in match (per task-007). Indicators for speaking. Graceful mic denial -> text notify.
- Gaming analogs: FXR direct (live voice+text for taunts/strategy in historical duels); Colyseus/Photon patterns (room voice).
- Recs for agent: Signaling first (extend 005 rooms); Coturn + fallback; psych UX with sabo/TB exs; VAD indicators; test NAT cross-net early. 1v1 P2P perfect fit. Text-first MVP ok. Full sketches in sub (media constraints, PC flow, manager).
High readiness. See arch voice section + STATUS for more excerpts/psych ties. Follow exactly.

**Priority**: Medium-High (psych layer for fun/retention; Phase 4 stretch but strong validation).
**Size**: Medium (WebRTC + UI integration).
- UI builds on task-007 frontend.
- Huge differentiator per research (FXR Battles voice is key fun factor).

**Priority**: High for the "fun" social layer.
**Size**: Medium (WebRTC + UI + fallback logic).
**Voice Sub Insights (from 019f058c, appended 2026-06-26 15m review)**:
Key for task-008: Signaling over 005 WS rooms (offer/answer/ICE), P2P WebRTC (getUserMedia, RTCPeerConnection), <150ms (Opus), STUN+ TURN (Coturn), graceful fallback, mic perms handling, WebAudio speaking indicators, NAT mitigations (test cross-net), FXR psych: "mental warfare... trash talk... taunts" + exs tied to sabo ("Nice SLs...?"), TB ("holding pause"), peeks. UI: VoicePanel next to TextChat (task-007), Zustand + WS, emoji reactions to events. Recs: 1. signaling skeleton, 2. native P2P, 3. controls/indicators, 4. fallback, 5. text polish/perms, 6. tests. Sources: MDN, FXR, project specs. High readiness.

**Fresh sub 019f05bc-ed2b-2084 (WebRTC deep ~90s)**: FXR tie perfect: "live voice chat to talk strategy or trash... taunts" — "mental warfare" validated; low-latency enables reactive psych. Setup: HTTPS; getUserMedia({audio: {echoCancellation:true,...}}); RTCPeerConnection({iceServers: [stun..., {urls: turn coturn, username ephemeral, credential}] }); pc.addTrack; createOffer/Answer + setLocal/Remote; trickle ICE via WS. WS reuse task-005 room: forward offer/answer/ice JSON. getStats for adapt. Opus default low BW 20-64kbps. TURN ~20-30% cases (symmetric NAT/CGNAT/firewall UDP block); prioritize UDP; regional Coturn for RTT<150. Fallback: Daily.co / Twilio / Agora (cheap audio). VAD: @ricky0123/vad or WebRTC built-in for pulsing indicators. PTT: track.enabled=false on hold. Recs: native + Coturn primary (ephemeral creds server-gen); signaling first (extend 005); permission context (battle start "for trash talk"); VAD + volume + mute UI next to chat; reconnect on state failed; tests on real NATs. Pseudocode full in sub output. <150ms feasible direct (Opus~20-50). 1v1 ideal P2P. Integrate UI patterns (Discord HUD sidebar). High readiness + psych power.

---

## Deep Research Resolutions (sibling worker, 2026-06-26)

This section **extends** the WebRTC/psych notes above with concrete, MVP-scoped resolutions grounded
in **current (2026) WebRTC guidance**: the MDN *perfect negotiation* pattern, Coturn TURN-REST
ephemeral credentials, Opus latency math, real-world TURN-relay prevalence, and `@ricky0123/vad-web`.
Stays consistent with the architecture: **signaling reuses the task-005 match WS**, **text-first then
P2P WebRTC**, **1v1 P2P audio**, **graceful fallback**.

### Q1. Self-hosted Coturn (STUN/TURN) vs provider (Twilio/Agora/Daily) — recommendation + tradeoffs

**Resolution (MVP): STUN from a public/own server + a *managed TURN provider* behind a thin
`/ice-servers` abstraction; document Coturn self-host as the scale-time cost optimization.**

Rationale: TURN is the one piece that *must just work* (15–30% of sessions depend on it — Q2) and
running Coturn correctly (UDP/TCP/TLS ports, public IP, regional placement, cert rotation, abuse
control) is real ops work that is wasteful for a Phase-4 MVP. A managed TURN service
(Cloudflare TURN / Twilio Network Traversal / Metered) gives reliable, geo-distributed relays in
minutes. **Crucially, abstract the ICE config behind one endpoint** so swapping managed → Coturn is
a server-only change with **zero client edits**.

| Option | Pros | Cons | Use when |
|---|---|---|---|
| **Managed TURN** (Cloudflare/Twilio/Metered) | Reliable, global, pay-per-GB, no ops, ephemeral creds built-in | Per-GB cost at scale, vendor dep | **MVP / launch** |
| **Self-host Coturn** | Cheap at volume, full control, regional placement near players | Ops burden, monitoring, cert/secret rotation | **Scale** (when relay GB cost > VPS) |
| **Full media provider** (Agora/Daily/LiveKit SFU) | Turnkey audio, recording, noise suppress | Overkill + cost for 1v1 P2P; SFU not needed for 2 peers | Only if P2P proves unreliable broadly |

**Ephemeral credentials (same pattern for both managed and Coturn):** never ship a static TURN
password. Coturn's TURN-REST uses time-limited creds — `username = "<expiryUnix>:<userId>"`,
`password = base64(HMAC-SHA1(secret, username))` — validated by the server by re-computing the HMAC
(no DB lookup). Lifetime ~ match length + margin (e.g. 1 h). ([Coturn TURN-REST][turn-rest], [Coturn wiki][turn-wiki])

```python
# task-005 backend: GET /ice-servers  -> returns iceServers for the client (per match join)
import time, hmac, hashlib, base64
def ice_servers(user_id: str, ttl=3600, secret=TURN_SHARED_SECRET):
    expiry = int(time.time()) + ttl
    username = f"{expiry}:{user_id}"
    password = base64.b64encode(hmac.new(secret.encode(), username.encode(), hashlib.sha1).digest()).decode()
    return {"iceServers": [
        {"urls": ["stun:stun.l.google.com:19302"]},
        {"urls": ["turn:turn.chart-fights.example:3478?transport=udp",
                   "turn:turn.chart-fights.example:3478?transport=tcp",
                   "turns:turn.chart-fights.example:5349?transport=tcp"],   # TLS for restrictive firewalls
         "username": username, "credential": password},
    ]}
```

```conf
# coturn turnserver.conf (scale-time): static secret + REST API
use-auth-secret
static-auth-secret=<TURN_SHARED_SECRET>
realm=chart-fights.example
listening-port=3478
tls-listening-port=5349
min-port=49152
max-port=65535
fingerprint
no-cli
```

### Q2. What % of connections need TURN relay? Symmetric NAT / CGNAT handling

**Resolution: budget ~15–25% relay for our (desktop, home-Wi-Fi-heavy) audience; treat TURN as
mandatory, not optional.** Published 2026 data:

- **General/consumer:** ~15–30% need a relay; Chrome UMA ≈ **20–25%** of sessions use relay candidates. ([getstream STUN/TURN][gs-stunturn], [dev.to NAT][nat-dev])
- **Mobile / CGNAT:** ~25–35%. **Enterprise/corporate firewalls:** ~30–60% (some report up to ~85%). ([celloip TURN guide 2026][cello-turn], [liveapi NAT][liveapi-nat])
- **Cause:** **symmetric NAT** (endpoint-dependent port mapping) — common on mobile carriers (CGNAT)
  and corporate routers — defeats STUN hole-punching; **two symmetric NATs ⇒ relay is the only path**. ([dev.to NAT][nat-dev], [celloip][cello-turn])

Handling:
- Always provide both STUN **and** TURN; include `transport=tcp` and `turns:` (TLS/443-style) so
  firewalls that block UDP still connect.
- Don't force relay for everyone (wastes bandwidth); let ICE pick the best pair. Only force
  `iceTransportPolicy:'relay'` as a diagnostic.
- Place TURN **regionally** to keep relayed RTT within the <150 ms budget (Q3).
- Symmetric-NAT detection is implicit: if the only working candidate pair is `relay`, you're behind
  a hard NAT — surface a subtle "relayed" badge but otherwise proceed.

### Q3. Latency budget (<150 ms) with Opus; getStats monitoring + fallback triggers

**Resolution: <150 ms one-way is comfortably achievable on a good direct P2P path; the dominant,
least-controllable term is the network leg.** Opus end-to-end budget (one-way):

| Stage | Typical | Note |
|---|---|---|
| Capture + WebRTC APM (AEC/NS/AGC) | ~10–20 ms | buffering + cleanup |
| Opus encode (20 ms frame) | ~20 ms | 26.5 ms algorithmic delay at libopus defaults |
| Packetize/send | ~1 ms | RTP+SRTP |
| **Network (one way)** | **~10–150 ms** | **dominant**; keep TURN regional |
| Jitter buffer (NetEQ) | ~20–100 ms | adaptive |
| Decode + render | ~10–30 ms | output device buffer |
| **Total (good net)** | **~70–120 ms** | below target |

([Opus codec][opus-fora], [WebRTC audio pipeline][fora-pipeline], [Opus wiki][opus-wiki])

**Opus tuning for a 1v1 trash-talk game:**
- `useinbandfec=1` (recover isolated packet loss without retransmit) — keep ON.
- **`usedtx=1` (DTX ON)** is fine here (saves bandwidth during silence; the STT-specific reason to
  disable it does not apply to human-to-human voice). ([RFC 7587][rfc7587], [Opus tuning 2026][callsphere])
- 20 ms frame (browser default) — good latency/efficiency trade-off.
- Voice bitrate ~24–32 kbps via `RTCRtpSender.setParameters` (cheap, plenty for speech).

```ts
// constrain capture for low-latency voice
const stream = await navigator.mediaDevices.getUserMedia({
  audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
});
// cap bitrate without SDP munging
const sender = pc.addTrack(stream.getAudioTracks()[0], stream);
const p = sender.getParameters(); p.encodings = [{ maxBitrate: 32_000 }]; await sender.setParameters(p);
// optionally SDP-munge useinbandfec=1; usedtx=1 in the a=fmtp:111 line if you need to force it
```

**getStats monitoring + fallback triggers** (poll every ~2–3 s):

```ts
async function sampleStats(pc: RTCPeerConnection) {
  const stats = await pc.getStats();
  let rttMs = 0, lossFrac = 0, jitterMs = 0;
  stats.forEach(r => {
    if (r.type === 'candidate-pair' && r.state === 'succeeded' && r.nominated)
      rttMs = (r.currentRoundTripTime ?? 0) * 1000;
    if (r.type === 'inbound-rtp' && r.kind === 'audio') {
      jitterMs = (r.jitter ?? 0) * 1000;
      lossFrac = r.packetsReceived ? (r.packetsLost ?? 0) / (r.packetsLost + r.packetsReceived) : 0;
    }
  });
  return { rttMs, lossFrac, jitterMs };
}
// Fallback / degrade triggers:
//   - pc.connectionState === 'failed'                      -> restartIce(); then provider/text fallback
//   - no 'connected' within ~8 s of negotiation start      -> fallback
//   - sustained rttMs > 300 or lossFrac > 0.10 over ~10 s   -> warn "poor connection", consider relay/provider
//   - 'disconnected' for > ~5 s                             -> restartIce()
pc.oniceconnectionstatechange = () => { if (pc.iceConnectionState === 'failed') pc.restartIce(); };
```

### Q4. Perfect negotiation (polite/impolite) + trickle ICE over the match WS

**Resolution: implement the MDN perfect-negotiation pattern verbatim; the task-005 server is a dumb
forwarder that also assigns the polite role.** Server picks one peer polite (e.g. first joiner, or
lower `playerId`) and tells each client its flag on join. Signaling messages ride the existing
`/ws/{match_id}` room; the room forwards `{type:'description'|'candidate'}` to the *other* peer.
([MDN perfect negotiation][mdn-pn], [WebRTC.rs deep dive][rs-pn], [signaling server][signal-med])

```ts
let makingOffer = false, ignoreOffer = false, polite = serverAssignedPoliteFlag;

pc.onnegotiationneeded = async () => {
  try { makingOffer = true; await pc.setLocalDescription();
        ws.send(JSON.stringify({ type: 'description', description: pc.localDescription })); }
  finally { makingOffer = false; }
};
pc.onicecandidate = ({ candidate }) =>            // trickle ICE: forward each candidate as discovered
  candidate && ws.send(JSON.stringify({ type: 'candidate', candidate }));
pc.ontrack = ({ streams }) => { remoteAudioEl.srcObject = streams[0]; };

ws.onmessage = async ({ data }) => {
  const msg = JSON.parse(data);
  if (msg.type === 'description') {
    const d = msg.description;
    const offerCollision = d.type === 'offer' && (makingOffer || pc.signalingState !== 'stable');
    ignoreOffer = !polite && offerCollision;       // impolite ignores colliding offers
    if (ignoreOffer) return;
    await pc.setRemoteDescription(d);              // polite rolls back implicitly (impl. rollback)
    if (d.type === 'offer') { await pc.setLocalDescription();
      ws.send(JSON.stringify({ type: 'description', description: pc.localDescription })); }
  } else if (msg.type === 'candidate') {
    try { await pc.addIceCandidate(msg.candidate); }
    catch (e) { if (!ignoreOffer) throw e; }       // swallow candidate errors for ignored offers
  }
};
```

Server side (task-005 reuse — *do not parse SDP/ICE, just relay*):

```python
# on join: assign roles, nudge first peer once the second arrives
async def on_join(room, ws, player_id):
    room.add(ws)
    polite = (player_id == sorted(room.player_ids)[0])      # deterministic, stable
    await ws.send_json({"type": "role", "polite": polite})
    if len(room) == 2:                                       # 'ready' nudge so neither offers into empty room
        await room.broadcast({"type": "ready"})
async def on_signal(room, sender_ws, msg):                  # msg.type in {description, candidate}
    await room.broadcast(msg, exclude=sender_ws)            # dumb forward to the other peer
```

Don't add tracks / start offering until the **other peer is present** (`ready` nudge) so you never
offer into an empty room; grab the mic before wiring the socket so the only `await` happens first.

### Q5. Mic permission denial UX + device errors

**Resolution: prompt with *context* and degrade gracefully to text — never block the match.**
- Prompt at match start, opt-in, with a reason ("Enable mic for live trash talk?"). Voice is
  additive; text chat always works.
- Map `getUserMedia` errors:
  - `NotAllowedError` / `SecurityError` → user denied → `voiceState='denied'`, show
    **"Voice unavailable (text only)"** + a "Enable mic" retry button (re-prompts).
  - `NotFoundError` → no mic device → "No microphone found".
  - `NotReadableError` → device busy (another app) → "Mic in use by another app".
- Requires **HTTPS** (secure context) for `getUserMedia`.

```ts
async function enableVoice() {
  try { return await navigator.mediaDevices.getUserMedia({ audio: {/* constraints */} }); }
  catch (e) {
    const n = (e as DOMException).name;
    store.setVoiceState(n === 'NotAllowedError' ? 'denied'
      : n === 'NotFoundError' ? 'no-device' : n === 'NotReadableError' ? 'busy' : 'error');
    store.pushNotification({ kind: 'voice', text: 'Voice unavailable — text chat only.' });
    return null;                                  // seamless: text chat already live over WS
  }
}
```

### Q6. PTT / mute / per-player volume

**Resolution: PTT and mute toggle `track.enabled`; per-player volume is per-`<audio>` element
`.volume` (or a `GainNode`).**

```ts
// Push-to-talk: hold Space to transmit (default muted when not held)
localTrack.enabled = false;
addEventListener('keydown', e => { if (e.code === 'Space' && !pttHeld) { pttHeld = true; localTrack.enabled = true; }});
addEventListener('keyup',   e => { if (e.code === 'Space') { pttHeld = false; localTrack.enabled = false; }});
// Mute toggle (open-mic mode):
function toggleMute() { localTrack.enabled = !localTrack.enabled; }
// Per-opponent volume slider (0..1) — playback only, no renegotiation:
remoteAudioEl.volume = sliderValue;
```

`track.enabled = false` stops transmitting audio frames (sends silence/DTX) without renegotiating —
ideal for instant PTT/mute. Offer a clear visual mic state in the VoicePanel.

### Q7. VAD speaking indicators (@ricky0123/vad-web)

**Resolution: detect *local* speech with `@ricky0123/vad-web` (Silero v5 via ONNX-wasm), and drive
the *opponent's* indicator by broadcasting tiny speaking start/stop events over the WS** (decouples
the remote pulse from audio analysis; works even when relayed).

- `@ricky0123/vad-web` v0.0.30 (Nov 2025), ~142k weekly downloads; React hook `useMicVAD` lives in
  `@ricky0123/vad-react`. Loads worklet + ONNX + wasm assets — **self-host these** via `baseAssetPath`
  / `onnxWASMBasePath` to avoid CDN coupling. ([vad-web npm][vad-npm], [vad docs][vad-docs])

```tsx
import { useMicVAD } from '@ricky0123/vad-react';
function useSpeakingIndicator(ws: WebSocket) {
  const [selfSpeaking, setSelf] = useState(false);
  useMicVAD({
    baseAssetPath: '/vad/', onnxWASMBasePath: '/vad/',     // self-hosted assets
    onSpeechStart: () => { setSelf(true);  ws.send(JSON.stringify({ type: 'speaking', on: true })); },
    onSpeechEnd:   () => { setSelf(false); ws.send(JSON.stringify({ type: 'speaking', on: false })); },
  });
  return selfSpeaking;   // pulse own avatar; opponent's pulse driven by their 'speaking' WS events
}
```

Alternative remote-only path (no extra lib): read `audioLevel` from inbound-rtp `getStats`, or a Web
Audio `AnalyserNode` on the remote stream. The WS-event approach is cheaper and the recommended MVP.

### Q8. Recording opt-in (deferred)

**Out of MVP scope (Phase 4+).** When added: `MediaRecorder` on a mixed/own track, **two-party
explicit consent**, clear recording indicator, and storage/retention policy. Note legal two-party
consent concerns. Do not build for MVP.

### Q9. Psych UX — tie voice/text to game events + VoicePanel placement

**Resolution: VoicePanel sits directly beside the TextChat in the match HUD sidebar; game events
(from `EventDelta`) drive emote suggestions, indicator emphasis, and quick-taunt buttons.** Voice is
the "all-chat MOBA salt" + poker-tell layer (FXR "mental warfare"). Always-notify-victim sabotage
(mech-spec §7) is what creates the bluff/counter-bluff window.

| Game event (EventDelta) | Voice/Text hook | Example taunt (quick-button) |
|---|---|---|
| Delete SLs cast (30 IP) | victim toast + caster VAD pulse | "Nice SLs… or were they?" |
| Holding Pause (R=0, +4 TB/s) | global "PAUSED (contested)" + pulse | "Holding pause — you're wasting IP." |
| Expensive Peek (60 IP) | 👀 reaction on peek event | "Just peeked the headline — gl on that." |
| Inject Fake News (40 IP) | "misinformation?" flag | "That wick look familiar?" |
| Big fill / equity swing | equity-curve flash + emote | "Right into my TP." |

Implementation: VoicePanel (mic/PTT/mute toggle, per-player volume, self+opponent speaking pulses)
+ TextChat (timestamps, emoji quick-reactions, auto-scroll-to-latest) share a sidebar; both read the
same Zustand store and the same WS room. Emoji reactions broadcast over WS and can be **auto-suggested
on key events** (e.g. 💥 when a sabotage `EventDelta` arrives). Anti-toxicity: easy mute, per-player
volume, PTT default; no recording in MVP.

### Sources (verified 2026-06-26)

- MDN — WebRTC perfect negotiation: [developer.mozilla.org/.../Perfect_negotiation][mdn-pn]
- WebRTC.rs — perfect negotiation deep dive (2026): [webrtc.rs/blog/2026/01/23/...][rs-pn]
- DIY WebRTC signaling server (polite flag, ready nudge, 2026): [medium.com/@jamesbordane57/...][signal-med]
- Coturn TURN-REST (ephemeral creds): [github.com/coturn/coturn/wiki/turnserver][turn-rest], [README.turnserver][turn-wiki]
- TURN relay prevalence: [getstream STUN/TURN][gs-stunturn], [dev.to NAT traversal][nat-dev], [CelloIP TURN 2026][cello-turn], [LiveAPI NAT][liveapi-nat]
- Opus latency: [Opus codec explained][opus-fora], [WebRTC audio pipeline][fora-pipeline], [Opus (Wikipedia)][opus-wiki], [RFC 7587][rfc7587], [Opus tuning 2026][callsphere]
- VAD: [@ricky0123/vad-web npm][vad-npm], [vad docs][vad-docs]

[mdn-pn]: https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Perfect_negotiation
[rs-pn]: https://webrtc.rs/blog/2026/01/23/perfect-negotiation-webrtc-deep-dive.html
[signal-med]: https://medium.com/@jamesbordane57/webrtc-signaling-server-how-it-works-build-one-node-js-or-skip-it-890e244d90ae
[turn-rest]: https://github.com/coturn/coturn/wiki/turnserver
[turn-wiki]: https://github.com/coturn/coturn/blob/master/README.turnserver
[gs-stunturn]: https://getstream.io/resources/projects/webrtc/advanced/stun-turn/
[nat-dev]: https://dev.to/alakkadshaw/nat-traversal-how-it-works-4dnc
[cello-turn]: https://celloip.com/blog/webrtc-turn-server-production-guide/
[liveapi-nat]: https://liveapi.com/blog/nat-traversal/
[opus-fora]: https://www.forasoft.com/learn/audio-for-video/articles-audio/opus-codec-explained
[fora-pipeline]: https://www.forasoft.com/learn/audio-for-video/articles-audio/webrtc-audio-pipeline-end-to-end
[opus-wiki]: https://en.wikipedia.org/wiki/Opus_(audio_format)
[rfc7587]: https://datatracker.ietf.org/doc/rfc7587/
[callsphere]: https://callsphere.ai/blog/vw1e-opus-codec-tuning-ai-voice
[vad-npm]: https://www.npmjs.com/package/@ricky0123/vad-web
[vad-docs]: https://docs.vad.ricky0123.com/user-guide/browser/
