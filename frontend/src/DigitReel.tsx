import { useLayoutEffect, useRef, useState } from 'react';

// Keep the visual lock and the controller's V2 click on the same beat.
export const DIGIT_LOCK_SECONDS = .55;

export function DigitReel({ digit, enabled }: { digit: number | null; enabled: boolean }) {
  const previous = useRef(digit);
  const [shown, setShown] = useState(digit);
  const [spinning, setSpinning] = useState(false);
  const [landed, setLanded] = useState(false);

  useLayoutEffect(() => {
    const changed = previous.current !== digit;
    previous.current = digit;
    if (!changed || digit === null || !enabled || matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setShown(digit);
      setSpinning(false);
      setLanded(false);
      return;
    }
    setLanded(false);
    setSpinning(true);
    setShown((digit + 1 + Math.floor(Math.random() * 9)) % 10);
    const reel = window.setInterval(() => setShown((digit + 1 + Math.floor(Math.random() * 9)) % 10), 70);
    let settle: number | undefined;
    const lock = window.setTimeout(() => {
      clearInterval(reel); setShown(digit); setSpinning(false); setLanded(true);
      settle = window.setTimeout(() => setLanded(false), 240);
    }, DIGIT_LOCK_SECONDS * 1000);
    return () => { clearInterval(reel); clearTimeout(lock); if (settle) clearTimeout(settle); };
  }, [digit, enabled]);

  return <span className={`digit-reel ${spinning ? 'is-spinning' : landed ? 'is-landed' : ''}`} aria-hidden="true">{shown ?? ''}</span>;
}
