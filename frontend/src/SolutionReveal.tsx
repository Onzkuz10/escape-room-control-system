import { formatTime } from './types';
import { useEffect, useState } from 'react';
import { LOCK_STOPS, LOCK_LEAD_SECONDS, RELEASE_AT } from './mechanicalSequence';

export function SolutionReveal({ digits, usedSeconds, remaining, elapsed }: { digits: number[]; usedSeconds: number; remaining: number; elapsed: number }) {
  const [initialElapsed] = useState(elapsed);
  const [locked, setLocked] = useState(() => LOCK_STOPS.map(stop => elapsed >= stop - LOCK_LEAD_SECONDS));
  const [released, setReleased] = useState(elapsed >= RELEASE_AT);
  useEffect(() => {
    const timers = LOCK_STOPS.map((stop, index) => setTimeout(() => setLocked(previous => previous.map((value, i) => i === index ? true : value)), Math.max(0, stop - LOCK_LEAD_SECONDS - initialElapsed) * 1000));
    timers.push(setTimeout(() => setReleased(true), Math.max(0, RELEASE_AT - initialElapsed) * 1000));
    return () => timers.forEach(clearTimeout);
  }, [initialElapsed]);
  return <div className={`solution-reveal glass-result ${released ? 'is-released' : ''}`}>
      <h1 className="solution-heading">Huone ratkaistu</h1>
      <div className="solution-slots" aria-label={`Lopullinen koodi ${digits.join(' ')}`}>
        {digits.map((digit, index) => <div className={`solution-slot ${locked[index] ? 'is-locked' : ''}`} key={index} aria-hidden="true"><span className="drum-face"><span>{digit}</span></span></div>)}
      </div>
      <div className="solution-summary is-visible" role="status">
        <p>Ryhmänne ratkaisi tämän pelin ajassa:</p>
        <span className="solution-time-label">AIKA</span>
        <strong className="solution-used-time">{formatTime(usedSeconds)}</strong>
        <small>Aikaa jäljellä <span className="solution-remaining-value">{formatTime(remaining)}</span></small>
      </div>
  </div>;
}
