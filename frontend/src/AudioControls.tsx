import { useCallback, useEffect, useRef, useState } from 'react';
import { Volume2, VolumeX } from 'lucide-react';
import type { RoomState, SendCommand } from './types';

export function AudioControls({ state, command, disabled }: { state: RoomState; command: SendCommand; disabled: boolean }) {
  const [volume, setVolume] = useState(state.presentation.volume);
  const [muted, setMuted] = useState(state.presentation.muted);
  const [failed, setFailed] = useState(false);
  const latest = useRef<{ volume: number; muted: boolean } | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sending = useRef(false);
  const flush = useCallback(async () => {
    timer.current = null;
    if (sending.current || !latest.current) return;
    const value = latest.current;
    latest.current = null;
    sending.current = true;
    try { setFailed(!await command('audio_settings', value)); }
    finally {
      sending.current = false;
      if (latest.current) timer.current = setTimeout(() => { void flush(); }, 60);
    }
  }, [command]);
  useEffect(() => {
    if (!sending.current && !latest.current && !timer.current) {
      setVolume(state.presentation.volume); setMuted(state.presentation.muted);
    }
  }, [state.presentation.volume, state.presentation.muted]);
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);
  function update(nextVolume: number, nextMuted: boolean) {
    setVolume(nextVolume); setMuted(nextMuted);
    latest.current = { volume: nextVolume, muted: nextMuted };
    if (!timer.current) timer.current = setTimeout(() => { void flush(); }, 60);
  }
  return <section className="live-audio" aria-label="Äänenvoimakkuuden livesäätö">
    {muted ? <VolumeX size={17} /> : <Volume2 size={17} />}
    <label htmlFor="live-volume">Äänenvoimakkuus</label>
    <input id="live-volume" type="range" min="0" max="100" step="1" value={Math.round(volume * 100)} disabled={disabled} onChange={event => update(Number(event.target.value) / 100, muted)} />
    <output htmlFor="live-volume">{Math.round(volume * 100)} %</output>
    <button className={`button subtle small ${muted ? 'active' : ''}`} aria-pressed={muted} disabled={disabled} onClick={() => update(volume, !muted)}>{muted ? 'Poista mykistys' : 'Mykistä'}</button>
    <small role="status">{failed ? 'Tallennus epäonnistui. Säädä uudelleen.' : 'LIVE · tallentuu automaattisesti'}</small>
  </section>;
}
