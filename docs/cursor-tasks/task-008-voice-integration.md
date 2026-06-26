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
