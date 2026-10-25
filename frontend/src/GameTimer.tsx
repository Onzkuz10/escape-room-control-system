import { useEffect, useState } from 'react';
import { formatTime } from './types';

export function timerStage(seconds: number) {
  return seconds <= 60 ? 'timer-final' : seconds <= 180 ? 'timer-danger' : seconds <= 300 ? 'timer-warning' : '';
}

export function GameTimer({ seconds, running, className }: { seconds: number; running: boolean; className: string }) {
  const [smoothSeconds, setSmoothSeconds] = useState(seconds);
  const milliseconds = seconds > 0 && seconds <= 60;
  useEffect(() => {
    setSmoothSeconds(seconds);
    if (!running || !milliseconds) return;
    const receivedAt = performance.now();
    let frame: number;
    function tick() {
      setSmoothSeconds(Math.max(0, seconds - (performance.now() - receivedAt) / 1000));
      frame = requestAnimationFrame(tick);
    }
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [seconds, running, milliseconds]);
  const total = Math.max(0, Math.ceil((running ? smoothSeconds : seconds) * 1000));
  const whole = Math.floor(total / 1000);
  return <div className={`${className}${milliseconds ? ' has-milliseconds' : ''}`} aria-label={`Aikaa jäljellä ${formatTime(seconds)}`}>
    {milliseconds ? <>{String(Math.floor(whole / 60)).padStart(2, '0')}:{String(whole % 60).padStart(2, '0')}<span className="timer-fraction">.{String(total % 1000).padStart(3, '0')}</span></> : formatTime(seconds)}
  </div>;
}
