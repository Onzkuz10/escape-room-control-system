import type { RoomState } from './types';
import { SlideMedia } from './PresentationPanel';
import { GameTimer, timerStage } from './GameTimer';
import { ResultScreen } from './ResultScreen';
import { IntroSequence } from './IntroSequence';
import { CodeSlide } from './CodeSlide';

export function Player({ state, connected }: { state: RoomState; connected: boolean }) {
  const solved = state.phase === 'solved', expired = state.phase === 'expired';
  const pregame = state.phase === 'pregame', ready = state.phase === 'ready';
  const numbers = state.game_view === 'digits';
  const slide = state.presentation.slides[state.slide_index];
  return <main className={`player-display ${state.running || state.phase === 'paused' ? timerStage(state.remaining_seconds) : ''} ${ready ? 'is-ready' : ''} ${solved ? 'is-solved' : ''} ${expired ? 'is-expired' : ''} ${numbers ? 'view-digits' : 'view-timer'} ${pregame || ready ? 'is-pregame' : ''}`} onDoubleClick={() => { if (document.fullscreenElement) void document.exitFullscreen().catch(() => {}); else void document.documentElement.requestFullscreen?.().catch(() => {}); }}>
    {solved || expired ? <ResultScreen key={`${state.phase}-${state.result_video_playing}`} won={solved} seconds={state.remaining_seconds} duration={state.duration_seconds} digits={state.solution_digits ?? state.digits.map(value => value ?? 0)} elapsed={state.result_at == null ? 5 : Math.max(0, state.server_time - state.result_at)} video={state.result_video_playing ? solved ? state.presentation.victory_video : state.presentation.defeat_video : null} /> : ready ? <p className="player-waiting">odotetaan seuraavan pelin käynnistystä...</p> : pregame && (slide.layout === 'seating' || slide.layout === 'movement') ? <IntroSequence slide={slide} /> : pregame && slide.layout === 'code' ? <CodeSlide key={state.slide_index} slide={slide} /> : pregame ? <div className="pregame-slide" key={`${state.slide_index}-${slide.media}-${slide.animation}`}>
      {slide.media && <SlideMedia key={slide.media} src={slide.media} title={slide.title} />}
      <div className={`slide-copy animation-${slide.animation}`}><h1>{slide.title}</h1><p>{slide.body}</p></div>
      <div className="slide-dots" aria-label={`Dia ${state.slide_index + 1} / ${state.presentation.slides.length}`}>{state.presentation.slides.map((_, i) => <i key={i} className={i === state.slide_index ? 'active' : ''} />)}</div>
    </div> : <div className="player-content">
      <GameTimer seconds={state.remaining_seconds} running={state.running} className="player-countdown" />
      <div className="player-timer-label">{state.phase === 'paused' ? 'AJASTIN PYSÄYTETTY' : 'AIKAA JÄLJELLÄ'}</div>
      <div className="player-indicators" aria-label="Luetut numerot">{state.digits.map((digit, i) => <div className="player-indicator" key={i}><span className="player-slot">0{i + 1}</span><div className="player-lamp"><span>{digit ?? ''}</span></div><span className="lamp-label">NUMERO</span></div>)}</div>
      {numbers && <p className="player-instruction">Aseta numerot oikeaan järjestykseen.</p>}
    </div>}
    {!connected && <div className="player-connection" role="status">Yhteys palautuu…</div>}

  </main>;
}
