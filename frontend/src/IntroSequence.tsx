import { useEffect, useState } from 'react';
import type { CSSProperties } from 'react';
import { Check, PersonStanding, X } from 'lucide-react';
import type { Slide } from './types';

export function IntroSequence({ slide }: { slide: Slide }) {
  const movement = slide.layout === 'movement';
  const [lights, setLights] = useState(true);
  const [demonstrating, setDemonstrating] = useState(false);
  useEffect(() => {
    setLights(true); setDemonstrating(false);
    if (!movement) return;
    const begin = setTimeout(() => setDemonstrating(true), 1100);
    const toggle = setInterval(() => setLights(previous => !previous), 6000);
    return () => { clearTimeout(begin); clearInterval(toggle); };
  }, [movement]);
  return <section className={`intro-sequence ${movement ? 'intro-movement' : 'intro-seated'} ${lights ? 'lights-on' : 'lights-off'} ${demonstrating ? 'is-demonstrating' : ''}`} aria-label={movement ? 'Valonauhan liikkumisohje' : 'Jakautuminen pöytiin'}>
    <h1>{movement ? lights ? 'Tasainen valo: pysykää alueella.' : 'Valonauha välkkyy: saatte liikkua.' : slide.title}</h1>
    {!movement && slide.body && <p className="intro-subtitle">{slide.body}</p>}
    <div className="intro-room" role="img" aria-label={movement ? lights ? 'Tasaisesti palava valonauha. Hahmo pysähtyy ja punainen X näyttää, ettei alueelta saa poistua.' : 'Himmeästi välkkyvä valonauha. Hahmo kävelee ulos ja vihreä merkki näyttää, että saa liikkua.' : 'Neljä pöytää ja kuusi henkilöä kunkin pöydän ääressä.'}>
      <div className="intro-light-strip" aria-hidden="true"><i className="led-lights led-even" /><i className="led-lights led-odd" /></div>
      {Array.from({ length: 4 }, (_, table) => <div key={table} className={`seating-group intro-group-${table}`} style={{ '--table-delay': `${table * .12}s` } as CSSProperties}>
        <div className="seating-table"><span>PÖYTÄ</span><strong>0{table + 1}</strong></div>
        {Array.from({ length: 6 }, (_, seat) => <span key={seat} className={`seating-person seat-${seat} ${table === 2 && seat === 3 ? 'intro-runner-origin' : ''}`}><i /></span>)}
      </div>)}
      <div key={String(lights)} className="intro-runner" aria-hidden="true"><PersonStanding strokeWidth={2} /></div>
      <div key={`sign-${lights}`} className="intro-verdict" aria-hidden="true">{lights ? <X size={29} strokeWidth={3} /> : <Check size={29} strokeWidth={3} />}</div>
    </div>
  </section>;
}
