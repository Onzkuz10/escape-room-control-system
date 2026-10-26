import { useEffect, useRef, useState } from 'react';
import type { RoomState } from './types';
import { VictoryClicks } from './VictoryClicks';

const SILENT_AUDIO = 'data:audio/wav;base64,UklGRkQDAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YSADAACAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgA==';

export function ControllerMusic({ state, previewing = false }: { state: RoomState; previewing?: boolean }) {
  const audio = useRef<HTMLAudioElement>(null);
  const [error, setError] = useState('');
  const ready = state.phase === 'ready';
  const terminal = state.phase === 'solved' || state.phase === 'expired';
  const { pregame_music, game_music, victory_video, defeat_video, volume, muted } = state.presentation;
  const active = state.phase === 'pregame' || state.phase === 'running' || (state.phase === 'expired' && !state.result_video_playing) || (terminal && state.result_video_playing);
  const source = terminal && state.result_video_playing ? state.phase === 'solved' ? victory_video : defeat_video : state.phase === 'solved' ? null : ready || state.phase === 'pregame' ? pregame_music : game_music;
  const finishedLossMusic = useRef(false);
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
      if (!element || (!ready && !playback.current.active) || !element.paused || element.ended || (state.phase === 'expired' && !state.result_video_playing && finishedLossMusic.current)) return;
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
  }, [ready, source, state.phase, state.result_video_playing]);

  return <><VictoryClicks state={state} previewing={previewing} /><audio ref={audio} src={source ?? SILENT_AUDIO} loop={!terminal} preload="auto" onEnded={() => { if (state.phase === 'expired' && !state.result_video_playing) finishedLossMusic.current = true; }} onError={() => { if (source) setError('Äänitiedostoa ei voitu toistaa. Tarkista tiedosto ohjauspaneelista.'); }} />{error && <p className="error-banner" role="status">{error}</p>}</>;
}
