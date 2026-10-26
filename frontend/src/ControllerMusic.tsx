import { useEffect, useRef, useState } from 'react';
import type { RoomState } from './types';
import { VictoryClicks } from './VictoryClicks';

const SILENT_AUDIO = 'data:audio/wav;base64,UklGRkQDAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YSADAACAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgA==';

export function ControllerMusic({ state, previewing = false }: { state: RoomState; previewing?: boolean }) {
  const audio = useRef<HTMLAudioElement>(null);
  const introAudio = useRef<HTMLAudioElement>(null);
  const [error, setError] = useState('');
  const ready = state.phase === 'ready';
  const terminal = state.phase === 'solved' || state.phase === 'expired';
  const { pregame_music, game_music, victory_video, defeat_video, volume, muted } = state.presentation;
  const active = state.phase === 'running' || (state.phase === 'expired' && !state.result_video_playing) || (terminal && state.result_video_playing);
  const source = terminal && state.result_video_playing ? state.phase === 'solved' ? victory_video : defeat_video : state.phase === 'solved' || ready || state.phase === 'pregame' ? null : game_music;
  const finishedLossMusic = useRef(false);
  const previousPhase = useRef(state.phase);
  const introGain = useRef(1);
  const introSettings = useRef({ volume, muted, previewing });
  introSettings.current = { volume, muted, previewing };
  if (state.phase !== 'expired') finishedLossMusic.current = false;
  const playback = useRef({ active, volume, muted });
  playback.current = { active, volume, muted };

  useEffect(() => {
    const element = audio.current;
    if (!element) return;
    element.volume = previewing ? volume * .1 : volume;
    element.muted = muted;
  }, [volume, muted, previewing]);

  useEffect(() => {
    const element = introAudio.current;
    if (!element) return;
    element.muted = muted;
    element.volume = Math.max(0, Math.min(1, volume * (previewing ? .1 : 1) * introGain.current));
  }, [volume, muted, previewing]);

  useEffect(() => {
    const element = introAudio.current;
    if (!element) return;
    const was = previousPhase.current;
    previousPhase.current = state.phase;
    let frame = 0;
    let stopTimer: ReturnType<typeof setTimeout> | undefined;
    if (state.phase === 'pregame' && pregame_music) {
      introGain.current = 1;
      const settings = introSettings.current;
      element.volume = settings.volume * (settings.previewing ? .1 : 1);
      void element.play().catch(reason => {
        if (reason.name !== 'AbortError') setError('Musiikin toisto estyi. Napsauta ohjauspaneelia ja tarkista valittu musiikkitiedosto.');
      });
    } else if (state.phase === 'running' && was === 'pregame' && pregame_music) {
      const age = state.game_started_at == null ? 0 : Math.max(0, state.server_time - state.game_started_at);
      const start = performance.now() - age * 1000;
      const fade = () => {
        introGain.current = Math.max(0, 1 - (performance.now() - start) / 2000);
        const settings = introSettings.current;
        element.volume = settings.volume * (settings.previewing ? .1 : 1) * introGain.current;
        if (introGain.current > 0) frame = requestAnimationFrame(fade);
        else element.pause();
      };
      fade();
      stopTimer = setTimeout(() => { introGain.current = 0; element.pause(); }, Math.max(0, 2000 - age * 1000));
    } else {
      introGain.current = 1;
      element.pause();
      if (state.phase === 'ready') element.currentTime = 0;
    }
    return () => { cancelAnimationFrame(frame); if (stopTimer) clearTimeout(stopTimer); };
  }, [state.phase, pregame_music]);

  useEffect(() => {
    const element = audio.current;
    if (!element) return;
    if (ready) element.currentTime = 0;
    setError('');
    if (!active || muted || !source || (state.phase === 'expired' && !state.result_video_playing && finishedLossMusic.current)) { element.pause(); return; }
    let cancelled = false;
    void element.play().catch(reason => {
      if (!cancelled && reason.name !== 'AbortError') setError('Musiikin toisto estyi. Napsauta ohjauspaneelia ja tarkista valittu musiikkitiedosto.');
    });
    return () => { cancelled = true; element.pause(); };
  }, [active, ready, muted, source]);

  useEffect(() => {
    const element = audio.current;
    if (!element) return;
    // Prime this same audio element during the operator's normal click before
    // the asynchronous pre-game command returns. No player-side gesture needed.
    function playFromGesture() {
      const intro = introAudio.current;
      if (intro && (ready || state.phase === 'pregame') && intro.paused && !intro.ended) {
        intro.volume = state.phase === 'pregame' && pregame_music ? playback.current.volume : 0;
        void intro.play().then(() => { if (state.phase !== 'pregame' || !pregame_music || playback.current.muted) intro.pause(); intro.volume = playback.current.volume * introGain.current; }).catch(() => {});
      }
      if (!element || (!ready && state.phase !== 'pregame' && !playback.current.active) || !element.paused || element.ended || (state.phase === 'expired' && !state.result_video_playing && finishedLossMusic.current)) return;
      element.volume = playback.current.active && source ? playback.current.volume : 0;
      void element.play().then(() => {
        if (!playback.current.active || playback.current.muted || !source) element.pause();
        element.volume = playback.current.volume;
        setError('');
      }).catch(reason => {
        if (playback.current.active && reason.name !== 'AbortError') setError('Musiikkitiedostoa ei voitu toistaa. Tarkista tiedosto ohjauspaneelista.');
      });
    }
    document.addEventListener('pointerdown', playFromGesture, true);
    document.addEventListener('keydown', playFromGesture, true);
    return () => {
      document.removeEventListener('pointerdown', playFromGesture, true);
      document.removeEventListener('keydown', playFromGesture, true);
    };
  }, [ready, source, pregame_music, state.phase, state.result_video_playing]);

  return <><VictoryClicks state={state} previewing={previewing} /><audio ref={introAudio} className="pregame-audio" src={pregame_music ?? SILENT_AUDIO} loop preload="auto" /><audio ref={audio} className="game-audio" src={source ?? SILENT_AUDIO} loop={!terminal} preload="auto" onEnded={() => { if (state.phase === 'expired' && !state.result_video_playing) finishedLossMusic.current = true; }} onError={() => { if (source) setError('Äänitiedostoa ei voitu toistaa. Tarkista tiedosto ohjauspaneelista.'); }} />{error && <p className="error-banner" role="status">{error}</p>}</>;
}
