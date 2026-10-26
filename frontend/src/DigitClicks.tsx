import { useEffect, useRef, useState } from 'react';
import type { RoomState } from './types';
import { useMediaLibrary } from './MediaLibrary';
import { digitRoll } from './digitRoll';
import { trimClick } from './VictoryClicks';

export function DigitClicks({ state, previewing }: { state: RoomState; previewing: boolean }) {
  const { files } = useMediaLibrary();
  const folderV2 = files.find(file => file.category === 'sound-effects' && file.name.toLowerCase() === 'lopetus-2.wav');
  const file = folderV2?.url ?? state.presentation.victory_sounds?.[1]?.file ?? null;
  const context = useRef<AudioContext | null>(null);
  const gain = useRef<GainNode | null>(null);
  const pending = useRef<(AudioBufferSourceNode | null)[]>([null, null, null, null]);
  const previous = useRef([...state.digits]);
  const lastNumbers = useRef([...state.digits]);
  const [clip, setClip] = useState<{ file: string; buffer: AudioBuffer; attackOffset: number } | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const audioContext = new AudioContext();
    context.current = audioContext;
    gain.current = audioContext.createGain();
    gain.current.connect(audioContext.destination);
    const unlock = () => { void audioContext.resume().catch(() => {}); };
    document.addEventListener('pointerdown', unlock, true);
    document.addEventListener('keydown', unlock, true);
    return () => {
      document.removeEventListener('pointerdown', unlock, true);
      document.removeEventListener('keydown', unlock, true);
      pending.current.forEach(node => { if (node) { try { node.stop(); } catch { /* Already finished. */ } } });
      void audioContext.close();
    };
  }, []);

  useEffect(() => {
    if (gain.current && context.current) gain.current.gain.setTargetAtTime(state.presentation.muted ? 0 : state.presentation.volume * .35 * (previewing ? .1 : 1), context.current.currentTime, .015);
  }, [state.presentation.volume, state.presentation.muted, previewing]);

  useEffect(() => {
    const audioContext = context.current;
    if (!file || !audioContext) { setClip(null); return; }
    const abort = new AbortController();
    setClip(null);
    setError('');
    void (async () => {
      try {
        const response = await fetch(file, { signal: abort.signal });
        if (!response.ok) throw new Error('Numeron ääntä ei voitu ladata.');
        const decoded = await audioContext.decodeAudioData(await response.arrayBuffer());
        if (!abort.signal.aborted) setClip({ file, ...trimClick(audioContext, decoded) });
      } catch (failure) {
        if (!abort.signal.aborted) setError(failure instanceof Error ? failure.message : 'Numeron ääntä ei voitu valmistella.');
      }
    })();
    return () => abort.abort();
  }, [file]);

  useEffect(() => {
    const before = previous.current;
    previous.current = [...state.digits];
    const live = state.phase === 'running' || state.phase === 'paused';
    if (state.phase === 'ready') lastNumbers.current = [null, null, null, null];
    state.digits.forEach((digit, index) => {
      if (!live || digit !== before[index]) {
        const old = pending.current[index];
        if (old) { try { old.stop(); } catch { /* Already finished. */ } pending.current[index] = null; }
      }
      const audioContext = context.current;
      const from = lastNumbers.current[index];
      if (live && digit !== null && digit !== before[index]) lastNumbers.current[index] = digit;
      if (!live || digit === null || digit === before[index] || !clip || clip.file !== file || !audioContext || !gain.current || audioContext.state !== 'running') return;
      const node = audioContext.createBufferSource();
      node.buffer = clip.buffer;
      node.connect(gain.current);
      const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
      node.start(audioContext.currentTime + Math.max(0, (reduced ? 0 : digitRoll(from, digit).seconds) - clip.attackOffset));
      pending.current[index] = node;
      node.onended = () => { node.disconnect(); if (pending.current[index] === node) pending.current[index] = null; };
    });
  }, [state.digits, state.phase, clip, file]);

  return error ? <p className="error-banner" role="status">{error}</p> : null;
}
