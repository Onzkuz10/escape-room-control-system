import { useEffect, useRef, useState } from 'react';
import { Check, Pause, Play, Upload, VolumeX } from 'lucide-react';
import type { RoomState, SendCommand, SoundChoice } from './types';

export function VictorySoundPicker({ state, command, disabled, onPreviewChange }: { state: RoomState; command: SendCommand; disabled: boolean; onPreviewChange: (value: boolean) => void }) {
  const audio = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const choices = state.presentation.victory_sounds ?? [];
  useEffect(() => {
    if (audio.current) { audio.current.volume = state.presentation.volume; audio.current.muted = state.presentation.muted; }
  }, [state.presentation.volume, state.presentation.muted]);
  useEffect(() => {
    const element = audio.current;
    return () => { element?.pause(); onPreviewChange(false); };
  }, [onPreviewChange]);
  function stop() { audio.current?.pause(); setPlaying(null); onPreviewChange(false); }
  async function preview(choice: SoundChoice) {
    if (playing === choice.file) { stop(); return; }
    const element = audio.current;
    if (!element) return;
    element.pause(); element.src = choice.file; element.currentTime = 0;
    element.volume = state.presentation.volume; element.muted = state.presentation.muted;
    setPlaying(choice.file); setError(''); onPreviewChange(true);
    try { await element.play(); } catch { stop(); setError('Ääntä ei voitu toistaa. Tarkista tiedosto.'); }
  }
  async function choose(file: string | null) {
    stop(); setBusy(true); setError('');
    try { if (!await command('victory_sound', file)) setError('Äänen valinta ei tallentunut. Yritä uudelleen.'); }
    finally { setBusy(false); }
  }
  async function upload(file: File | undefined) {
    if (!file) return;
    setBusy(true); setError('');
    if (file.size > 80 * 1024 * 1024) { setBusy(false); setError('Äänitiedoston enimmäiskoko on 80 Mt.'); return; }
    const url = URL.createObjectURL(file);
    try {
      const duration = await new Promise<number>((resolve, reject) => {
        const probe = new Audio(); probe.preload = 'metadata'; probe.src = url;
        probe.onloadedmetadata = () => { resolve(probe.duration); probe.removeAttribute('src'); probe.load(); };
        probe.onerror = () => reject(new Error('Äänitiedostoa ei voitu lukea.'));
      });
      if (!Number.isFinite(duration) || duration < .1 || duration > 30) throw new Error('Lopetusäänen enimmäiskesto on 30 sekuntia.');
      const response = await fetch(`/api/victory-sounds?filename=${encodeURIComponent(file.name)}&duration_seconds=${duration}`, { method: 'POST', headers: { 'Content-Type': 'application/octet-stream' }, body: file });
      if (!response.ok) { const result = await response.json(); throw new Error(result.detail); }
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Äänen lisääminen epäonnistui.'); }
    finally { URL.revokeObjectURL(url); setBusy(false); }
  }
  return <section className="panel victory-sound-picker"><div className="panel-heading"><h2>Mekaaninen lopetusääni</h2><span className="badge">{choices.length} / 4</span></div><div className="victory-sound-body">
    <p>Kuuntele vaihtoehdot ja valitse yksi. Valinta tallentuu heti. Pelissä lyhyt klikki toistuu jokaisen numeron loksahtaessa.</p>
    <audio ref={audio} onEnded={stop} onError={() => { stop(); setError('Ääntä ei voitu toistaa.'); }} />
    <div className="sound-choice-list">{choices.map(choice => <div className={`sound-choice ${state.presentation.victory_sound === choice.file ? 'is-selected' : ''}`} key={choice.file}>
      <button className="button secondary icon-only" aria-label={`${playing === choice.file ? 'Pysäytä' : 'Kuuntele'} ${choice.name}`} onClick={() => void preview(choice)} disabled={disabled}>{playing === choice.file ? <Pause size={16} /> : <Play size={16} />}</button>
      <span><strong>{choice.name}</strong><small>{choice.duration_seconds.toFixed(1)} s</small></span>
      <button className="button secondary small" aria-pressed={state.presentation.victory_sound === choice.file} disabled={disabled || busy} onClick={() => void choose(choice.file)}>{state.presentation.victory_sound === choice.file ? <><Check size={14} />Valittu</> : 'Käytä tätä ääntä'}</button>
    </div>)}</div>
    {!choices.length && <p className="sound-empty">Äänivaihtoehtoja ei ole vielä lisätty.</p>}
    <div className="sound-picker-actions"><button className="button subtle small" aria-pressed={!state.presentation.victory_sound} disabled={disabled || busy} onClick={() => void choose(null)}><VolumeX size={14} />{state.presentation.victory_sound ? 'Poista lopetusääni käytöstä' : 'Äänetön valittu'}</button>
      {choices.length < 4 && <label className="file-choice"><Upload size={14} />{busy ? 'Lisätään…' : 'Lisää äänivaihtoehto'}<input type="file" accept=".mp3,.wav,.ogg,.m4a" disabled={disabled || busy} onChange={event => { void upload(event.target.files?.[0]); event.target.value = ''; }} /></label>}
    </div>{state.presentation.muted && <p className="editor-note">Ääni on mykistetty. Poista mykistys livesäädöstä kuullaksesi esikuuntelun.</p>}{error && <p className="inline-error" role="alert">{error}</p>}
  </div></section>;
}
