import { Check, LockKeyhole } from 'lucide-react';
import type { RoomState } from './types';
import { formatTime } from './types';

export function Player({ state, connected }: { state: RoomState; connected: boolean }) {
  const solved = state.phase === 'solved', expired = state.phase === 'expired';
  return <main className={`player-display ${solved ? 'is-solved' : ''} ${expired ? 'is-expired' : ''}`} onDoubleClick={() => { if (document.fullscreenElement) void document.exitFullscreen().catch(() => {}); else void document.documentElement.requestFullscreen?.().catch(() => {}); }}>
    <div className="player-grid" /><div className="player-orbit orbit-1" /><div className="player-orbit orbit-2" />
    <header className="player-header"><span><LockKeyhole size={17} />LOCK /</span><span>HUONE 01</span></header>
    <div className="player-content"><div className="player-eyebrow">{solved ? 'PROTOKOLLA AVATTU' : expired ? 'YHTEYS SULJETTU' : 'PAKO ON VAIN AJAN KYSYMYS'}</div>
      {solved ? <div className="success-story" role="status"><div className="success-emblem"><Check size={54} strokeWidth={1.5} /><span /></div><h1>Reitti on auki<span>.</span></h1><p>Ratkaisitte koodin. Vapaus odottaa.</p><div className="success-time">AIKAA JÄI <strong>{formatTime(state.remaining_seconds)}</strong></div></div> : <><div className="player-countdown" aria-label={`Aikaa jäljellä ${formatTime(state.remaining_seconds)}`}>{formatTime(state.remaining_seconds)}</div><div className="player-timer-label">{expired ? 'AIKA ON LOPPUNUT' : 'AIKAA JÄLJELLÄ'}</div></>}
      <div className="player-indicators" aria-label="Koodin merkkivalot">{state.digits.map((digit, i) => <div className={`player-indicator ${state.correct[i] ? 'correct' : ''}`} key={i}><span className="player-slot">0{i + 1}</span><div className="player-lamp"><span>{digit ?? '–'}</span>{state.correct[i] && <Check size={18} />}</div><span className="lamp-label">{state.correct[i] ? 'AVATTU' : 'LUKITTU'}</span></div>)}</div>
      <p className="player-instruction">{solved ? 'NELJÄ NUMEROA. YKSI YHTEINEN RATKAISU.' : expired ? 'Jokaisella tarinalla on loppunsa.' : 'Löydä numerot. Aseta ne oikeaan järjestykseen.'}</p>
    </div><footer className="player-footer"><span>04 LUKKOA <i /> 01 REITTI ULOS</span><span className="player-footer-line" /><span>{solved ? 'VAPAUS SAAVUTETTU' : 'RATKAISU ON TEIDÄN KÄSISSÄNNE'}</span></footer>
    {!connected && <div className="player-connection" role="status">Yhteys palautuu…</div>}
    {solved && <div className="success-particles" aria-hidden="true">{Array.from({ length: 24 }, (_, i) => <i key={i} style={{ left: `${(i * 43) % 100}%`, animationDelay: `${i * .11}s`, animationDuration: `${3 + i % 4}s` }} />)}</div>}
  </main>;
}
