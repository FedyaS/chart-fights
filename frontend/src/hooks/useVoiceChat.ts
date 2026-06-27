'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

export type VoiceStatus = 'idle' | 'connecting' | 'connected' | 'error' | 'unsupported';

export type VoiceSignalType = 'voice_offer' | 'voice_answer' | 'voice_ice';

interface UseVoiceChatReturn {
  status: VoiceStatus;
  micOn: boolean;
  remoteActive: boolean;
  errorMsg: string | null;
  start: () => Promise<void>;
  stop: () => void;
  toggleMic: () => void;
  handleSignal: (type: VoiceSignalType, payload: any) => Promise<void>;
}

const ICE_SERVERS: RTCIceServer[] = [{ urls: 'stun:stun.l.google.com:19302' }];

// Minimal P2P WebRTC voice. One side calls start() (sends an offer); the other
// auto-answers on receiving the offer. WS relays offer/answer/ICE via sendSignal.
export function useVoiceChat(
  sendSignal: (type: VoiceSignalType, payload: any) => void,
): UseVoiceChatReturn {
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  const audioElRef = useRef<HTMLAudioElement | null>(null);
  const pendingIceRef = useRef<RTCIceCandidateInit[]>([]);

  const [status, setStatus] = useState<VoiceStatus>('idle');
  const [micOn, setMicOn] = useState(false);
  const [remoteActive, setRemoteActive] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const supported = useCallback(() => {
    return typeof window !== 'undefined'
      && typeof RTCPeerConnection !== 'undefined'
      && !!navigator?.mediaDevices?.getUserMedia;
  }, []);

  const getAudioEl = useCallback(() => {
    if (typeof document === 'undefined') return null;
    if (!audioElRef.current) {
      const el = document.createElement('audio');
      el.autoplay = true;
      (el as any).playsInline = true;
      audioElRef.current = el;
    }
    return audioElRef.current;
  }, []);

  const ensurePc = useCallback(() => {
    if (pcRef.current) return pcRef.current;
    const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });
    pc.onicecandidate = (e) => {
      if (e.candidate) sendSignal('voice_ice', e.candidate.toJSON());
    };
    pc.ontrack = (e) => {
      const el = getAudioEl();
      if (el && e.streams[0]) {
        el.srcObject = e.streams[0];
        el.play?.().catch(() => {});
      }
      setRemoteActive(true);
    };
    pc.onconnectionstatechange = () => {
      const st = pc.connectionState;
      if (st === 'connected') setStatus('connected');
      else if (st === 'failed' || st === 'closed' || st === 'disconnected') {
        setStatus((prev) => (prev === 'connected' ? 'idle' : prev));
      }
    };
    pcRef.current = pc;
    return pc;
  }, [getAudioEl, sendSignal]);

  const ensureMic = useCallback(async () => {
    if (localStreamRef.current) return localStreamRef.current;
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    localStreamRef.current = stream;
    setMicOn(true);
    const pc = ensurePc();
    stream.getTracks().forEach((t) => pc.addTrack(t, stream));
    return stream;
  }, [ensurePc]);

  const drainPendingIce = useCallback(async (pc: RTCPeerConnection) => {
    const pending = pendingIceRef.current;
    pendingIceRef.current = [];
    for (const c of pending) {
      try { await pc.addIceCandidate(c); } catch {}
    }
  }, []);

  const start = useCallback(async () => {
    if (!supported()) { setStatus('unsupported'); setErrorMsg('WebRTC / microphone not available in this environment.'); return; }
    try {
      setStatus('connecting');
      setErrorMsg(null);
      await ensureMic();
      const pc = ensurePc();
      const offer = await pc.createOffer({ offerToReceiveAudio: true });
      await pc.setLocalDescription(offer);
      sendSignal('voice_offer', offer);
    } catch (e: any) {
      setStatus('error');
      setErrorMsg(e?.message ?? 'Failed to start voice');
    }
  }, [ensureMic, ensurePc, sendSignal, supported]);

  const handleSignal = useCallback(async (type: VoiceSignalType, payload: any) => {
    if (!supported()) { setStatus('unsupported'); return; }
    try {
      const pc = ensurePc();
      if (type === 'voice_offer') {
        setStatus('connecting');
        await ensureMic();
        await pc.setRemoteDescription(new RTCSessionDescription(payload));
        await drainPendingIce(pc);
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);
        sendSignal('voice_answer', answer);
      } else if (type === 'voice_answer') {
        await pc.setRemoteDescription(new RTCSessionDescription(payload));
        await drainPendingIce(pc);
      } else if (type === 'voice_ice') {
        if (pc.remoteDescription) {
          try { await pc.addIceCandidate(payload); } catch {}
        } else {
          pendingIceRef.current.push(payload);
        }
      }
    } catch (e: any) {
      setStatus('error');
      setErrorMsg(e?.message ?? 'Voice signaling error');
    }
  }, [drainPendingIce, ensureMic, ensurePc, sendSignal, supported]);

  const toggleMic = useCallback(() => {
    const stream = localStreamRef.current;
    if (!stream) { void start(); return; }
    const next = !micOn;
    stream.getAudioTracks().forEach((t) => { t.enabled = next; });
    setMicOn(next);
  }, [micOn, start]);

  const stop = useCallback(() => {
    try { pcRef.current?.close(); } catch {}
    pcRef.current = null;
    localStreamRef.current?.getTracks().forEach((t) => t.stop());
    localStreamRef.current = null;
    if (audioElRef.current) audioElRef.current.srcObject = null;
    pendingIceRef.current = [];
    setMicOn(false);
    setRemoteActive(false);
    setStatus('idle');
  }, []);

  useEffect(() => () => { stop(); }, [stop]);

  return { status, micOn, remoteActive, errorMsg, start, stop, toggleMic, handleSignal };
}
