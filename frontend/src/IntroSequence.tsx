import { useEffect, useState } from 'react';
import type { CSSProperties } from 'react';
import { Check, PersonStanding, X } from 'lucide-react';
import type { Slide } from './types';

export function IntroSequence({ slide }: { slide: Slide }) {
  const movement = slide.layout === 'movement';
  const [lights, setLights] = useState(true);
  const [blinking, setBlinking] = useState(false);
  const [demonstrating, setDemonstrating] = useState(false);
  useEffect(() => {
    setLights(true); setBlinking(false); setDemonstrating(false);
    if (!movement) return;
    const begin = setTimeout(() => setDemonstrating(true), 1100);
    const toggle = setInterval(() => setLights(previous => !previous), 6000);
    const blinkStart = setTimeout(() => setBlinking(true), 4000);
    const blinkEnd = setTimeout(() => setBlinking(false), 6000);
    let blinkLoop: ReturnType<typeof setInterval> | undefined;
    let blinkStop: ReturnType<typeof setTimeout> | undefined;
    const startLoop = setTimeout(() => {
      setBlinking(true);
      blinkStop = setTimeout(() => setBlinking(false), 2000);
      blinkLoop = setInterval(() => { setBlinking(true); blinkStop = setTimeout(() => setBlinking(false), 2000); }, 12000);
    }, 16000);
    return () => { clearTimeout(begin); clearInterval(toggle); clearTimeout(blinkStart); clearTimeout(blinkEnd); clearTimeout(startLoop); clearInterval(blinkLoop); clearTimeout(blinkStop); };
  }, [movement]);
  const canMove = !lights || blinking;
  return <section className={`intro-sequence ${movement ? 'intro-movement' : 'intro-seated'} ${lights ? 'lights-on' : 'lights-off'} ${blinking ? 'lights-blinking' : ''} ${demonstrating ? 'is-demonstrating' : ''}`} aria-label={movement ? 'Valonauhan liikkumisohje' : 'Jakautuminen pöytiin'}>
    <h1>{movement ? 'Kun valonauha välkkyy tai sammuu, saatte liikkua.' : slide.title}</h1>
    {!movement && slide.body && <p className="intro-subtitle">{slide.body}</p>}
    <div className="intro-room" role="img" aria-label={movement ? blinking ? 'Valonauha välkkyy. Alueelta saa poistua.' : lights ? 'Valonauha palaa. Alueelta ei saa poistua.' : 'Valonauha on sammunut. Alueelta saa poistua.' : 'Neljä pöytää ja kuusi henkilöä kunkin pöydän ääressä.'}>
      <div className="intro-light-strip" aria-hidden="true"><i className="led-lights led-even" /><i className="led-lights led-odd" /></div>
      {Array.from({ length: 4 }, (_, table) => <div key={table} className={`seating-group intro-group-${table}`} style={{ '--table-delay': `${table * .12}s` } as CSSProperties}>
        <div className="seating-table"><span>PÖYTÄ</span><strong>0{table + 1}</strong></div>
        {Array.from({ length: 6 }, (_, seat) => <span key={seat} className={`seating-person seat-${seat} ${table === 2 && seat === 3 ? 'intro-runner-origin' : ''}`}><i /></span>)}
      </div>)}
      <div key={String(canMove)} className="intro-runner" aria-hidden="true"><PersonStanding strokeWidth={2} /></div>
      <div key={`sign-${canMove}`} className="intro-verdict" aria-hidden="true">{canMove ? <Check size={29} strokeWidth={3} /> : <X size={29} strokeWidth={3} />}</div>
    </div>
  </section>;
}
