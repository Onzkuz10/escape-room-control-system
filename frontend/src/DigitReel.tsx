import { useLayoutEffect, useRef, useState, type CSSProperties } from 'react';
import { digitRoll } from './digitRoll';

type Reel = { digits: number[]; steps: number; seconds: number; rolling: boolean };

export function DigitReel({ digit, enabled }: { digit: number | null; enabled: boolean }) {
  const previous = useRef(digit);
  const lastNumber = useRef(digit);
  const [reel, setReel] = useState<Reel>(() => ({ digits: digit === null ? [] : [digit], steps: 0, seconds: 0, rolling: false }));

  useLayoutEffect(() => {
    const changed = previous.current !== digit;
    previous.current = digit;
    if (!changed) return;
    if (digit === null) {
      setReel({ digits: [], steps: 0, seconds: 0, rolling: false });
      return;
    }
    const plan = digitRoll(lastNumber.current, digit);
    lastNumber.current = digit;
    if (!enabled || !plan.steps || matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setReel({ digits: [digit], steps: 0, seconds: 0, rolling: false });
      return;
    }
    setReel({ ...plan, rolling: true });
    const finish = window.setTimeout(() => setReel({ digits: [digit], steps: 0, seconds: 0, rolling: false }), plan.seconds * 1000);
    return () => clearTimeout(finish);
  }, [digit, enabled]);

  const style = { '--reel-steps': reel.steps, '--reel-duration': `${reel.seconds}s` } as CSSProperties;
  return <span className={`digit-reel ${reel.rolling ? 'is-spinning' : ''}`} style={style} aria-hidden="true"><span className="digit-reel-track">{reel.digits.map((value, index) => <span key={index}>{value}</span>)}</span></span>;
}
