import { useEffect, useRef, useState } from 'react';
import type { RoomState } from './types';
import { LOCK_STOPS, RELEASE_AT } from './mechanicalSequence';

/** Find the first substantial attack and keep only its short, tactile body. */
export function trimClick(context: BaseAudioContext, source: AudioBuffer) {
  const step = Math.max(1, Math.round(source.sampleRate * .005));
  const levels: number[] = [];
  for (let start = 0; start < source.length; start += step) {
    let energy = 0, count = 0;
    for (let channel = 0; channel < source.numberOfChannels; channel++) {
      const samples = source.getChannelData(channel);
      for (let i = start; i < Math.min(start + step, source.length); i++) { energy += samples[i] ** 2; count++; }
    }
    levels.push(Math.sqrt(energy / count));
  }
  const peak = Math.max(...levels);
  if (peak < .0001) throw new Error('Äänitiedostosta ei löytynyt klikkiä.');
  const attack = levels.findIndex(level => level >= peak * .35) * step;
  const start = Math.max(0, attack - Math.round(source.sampleRate * .006));
  const length = Math.min(Math.round(source.sampleRate * .18), source.length - start);
  const click = context.createBuffer(source.numberOfChannels, length, source.sampleRate);
  for (let channel = 0; channel < source.numberOfChannels; channel++) {
    const input = source.getChannelData(channel), output = click.getChannelData(channel);
    for (let i = 0; i < length; i++) {
      const fade = Math.min(1, i / (source.sampleRate * .002), (length - 1 - i) / (source.sampleRate * .014));
      output[i] = input[start + i] * fade;
    }
  }
  return { buffer: click, attackOffset: (attack - start) / source.sampleRate };
}

export function VictoryClicks({ state, previewing }: { state: RoomState; previewing: boolean }) {
  const context = useRef<AudioContext | null>(null);
  const gain = useRef<GainNode | null>(null);
  const nodes = useRef<AudioBufferSourceNode[]>([]);
  const [clip, setClip] = useState<{ file: string; buffer: AudioBuffer; attackOffset: number } | null>(null);
  const [error, setError] = useState('');
  const file = state.presentation.victory_sound;
  const age = state.result_at == null ? Infinity : Math.max(0, state.server_time - state.result_at);
  const clock = useRef({ age, received: performance.now() });
  clock.current = { age, received: performance.now() };
  const active = state.phase === 'solved' && !state.result_video_playing;

  useEffect(() => {
    const audioContext = new AudioContext();
    context.current = audioContext;
    gain.current = audioContext.createGain();
    gain.current.connect(audioContext.destination);
    function unlock() { void audioContext.resume().catch(() => setError('Ääni ei käynnistynyt. Napsauta ohjauskeskusta.')); }
    document.addEventListener('pointerdown', unlock, true);
    document.addEventListener('keydown', unlock, true);
    return () => {
      document.removeEventListener('pointerdown', unlock, true);
      document.removeEventListener('keydown', unlock, true);
      void audioContext.close();
    };
  }, []);

  useEffect(() => {
    if (gain.current && context.current) gain.current.gain.setTargetAtTime(state.presentation.muted ? 0 : state.presentation.volume * (previewing ? .1 : 1), context.current.currentTime, .015);
  }, [state.presentation.volume, state.presentation.muted, previewing]);

  useEffect(() => {
    const audioContext = context.current;
    if (!file || !audioContext) { setClip(null); return; }
    const abort = new AbortController();
    setError('');
    void (async () => {
      try {
        const response = await fetch(file, { signal: abort.signal });
        if (!response.ok) throw new Error('Äänitiedostoa ei voitu ladata.');
        const decoded = await audioContext.decodeAudioData(await response.arrayBuffer());
        if (!abort.signal.aborted) setClip({ file, ...trimClick(audioContext, decoded) });
      } catch (failure) {
        if (!abort.signal.aborted) setError(failure instanceof Error ? failure.message : 'Lopetusääntä ei voitu valmistella.');
      }
    })();
    return () => abort.abort();
  }, [file]);

  useEffect(() => {
    const audioContext = context.current, output = gain.current;
    if (!active || !clip || clip.file !== file || !audioContext || !output) return;
    const currentAge = clock.current.age + (performance.now() - clock.current.received) / 1000;
    if (currentAge >= RELEASE_AT) return;
    if (audioContext.state !== 'running') { setError('Lopetusääni odottaa selaimen äänilupaa. Napsauta ohjauskeskusta ennen peliä.'); return; }
    LOCK_STOPS.forEach((stop, index) => {
      const delay = stop - currentAge - clip.attackOffset;
      if (delay < 0) return; // Reconnecting must never replay old clicks.
      const node = audioContext.createBufferSource();
      node.buffer = clip.buffer;
      node.connect(output);
      node.start(audioContext.currentTime + delay);
      nodes.current.push(node);
      node.onended = () => { node.disconnect(); console.debug(`Lopetusklikki ${index + 1}/4 valmis`); };
    });
    return () => { nodes.current.forEach(node => { try { node.stop(); } catch { /* Already ended. */ } node.disconnect(); }); nodes.current = []; };
  }, [active, clip, file, state.result_at]);

  return error ? <p className="error-banner" role="status">{error}</p> : null;
}
