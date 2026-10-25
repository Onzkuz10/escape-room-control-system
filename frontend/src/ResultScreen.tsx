import { useState } from 'react';
import { formatTime } from './types';
import { SolutionReveal } from './SolutionReveal';

export function ResultScreen({ won, seconds, duration, digits, elapsed, video }: { won: boolean; seconds: number; duration: number; digits: number[]; elapsed: number; video: string | null }) {
  const [failed, setFailed] = useState(false);
  return <section className={`result-screen ${won ? 'result-victory' : 'result-defeat'} ${video && !failed ? 'has-video' : ''}`} aria-label={won ? 'Voitto' : 'Häviö'}>
    {video && !failed && <video className="result-video" src={video} autoPlay muted playsInline preload="auto" onError={() => setFailed(true)} aria-label={won ? 'Voittovideo' : 'Häviövideo'} />}
    {won && (!video || failed) ? <SolutionReveal digits={digits} elapsed={elapsed} usedSeconds={Math.floor(Math.max(0, duration - seconds))} remaining={seconds} /> : <div className="result-copy" role="status">
      <h1>{won ? 'Huone ratkaistu' : 'AIKA LOPPUI'}</h1>
      {won && <p className="result-time">AIKA <strong>{formatTime(Math.floor(Math.max(0, duration - seconds)))}</strong></p>}
      {failed && <p className="media-error">Videota ei voitu toistaa. Tarkista tiedosto ohjauskeskuksesta.</p>}
    </div>}
  </section>;
}
