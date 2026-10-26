import { ArrowDown } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { Slide } from './types';

export function CodeSlide({ slide }: { slide: Slide }) {
  const [digits, setDigits] = useState(() => Array.from({ length: 4 }, () => Math.floor(Math.random() * 10)));
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    function schedule() {
      timer = setTimeout(() => {
        const index = Math.floor(Math.random() * 4);
        setDigits(previous => previous.map((digit, i) => i === index ? (digit + 1 + Math.floor(Math.random() * 9)) % 10 : digit));
        schedule();
      }, 100 + Math.random() * 200);
    }
    schedule();
    return () => clearTimeout(timer);
  }, []);
  return <section className="code-slide" aria-label="Ratkaistava koodi on pöydällä">
    <h1>{slide.title}</h1>
    <div className="code-slide-graphic" aria-hidden="true">
      <div className="code-slide-slots">{digits.map((digit, index) => <div className="code-slide-slot" key={index} style={{ animationDelay: `${index * .12}s` }}><span className="code-slide-blur-number">{digit}</span></div>)}</div>
      <div className="code-slide-guide"><span /><ArrowDown strokeWidth={1.2} /></div>
    </div>
  </section>;
}
