import type { RoomState } from './types';
import { SlideMedia } from './PresentationPanel';
import { GameTimer, timerStage } from './GameTimer';
import { ResultScreen } from './ResultScreen';
import { IntroSequence } from './IntroSequence';
import { CodeSlide } from './CodeSlide';
import { useLayoutEffect, useRef } from 'react';
import { MORPH_SECONDS, RELEASE_AT } from './mechanicalSequence';
import { DEFAULT_SLOT_ICONS, SlotIcon } from './SlotIcon';

export function Player({ state, connected }: { state: RoomState; connected: boolean }) {
  const solved = state.phase === 'solved', expired = state.phase === 'expired';
  const pregame = state.phase === 'pregame', ready = state.phase === 'ready';
  const numbers = state.game_view === 'digits';
  const slotIcons = state.slot_icons ?? DEFAULT_SLOT_ICONS;
  const hasSlotIcons = slotIcons.some(Boolean);
  const slide = state.presentation.slides[state.slide_index];
  const display = useRef<HTMLElement>(null);
  const origin = useRef<{ cards: { box: DOMRect; font: number }[]; timer?: DOMRect } | null>(null);
  const animations = useRef<Animation[]>([]);
  useLayoutEffect(() => {
    const root = display.current;
    if (!root) return;
    if (!solved) {
      animations.current.forEach(animation => animation.cancel());
      animations.current = [];
      origin.current = state.phase === 'running' || state.phase === 'paused' ? {
        cards: Array.from(root.querySelectorAll('.player-lamp')).map(card => ({ box: card.getBoundingClientRect(), font: parseFloat(getComputedStyle(card.querySelector('span')!).fontSize) })),
        timer: root.querySelector('.player-countdown')?.getBoundingClientRect(),
      } : null;
      return;
    }
    const previous = origin.current;
    origin.current = null;
    if (!previous || state.result_video_playing || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const age = state.result_at == null ? Infinity : Math.max(0, state.server_time - state.result_at);
    if (age >= RELEASE_AT) return;
    const duration = Math.max(.25, MORPH_SECONDS - age) * 1000;
    function morph(element: Element, from: DOMRect) {
      const to = element.getBoundingClientRect();
      if (!to.width || !to.height) return;
      animations.current.push(element.animate([
        { transform: `translate(${from.x - to.x}px, ${from.y - to.y}px) scale(${from.width / to.width}, ${from.height / to.height})`, transformOrigin: 'top left' },
        { transform: 'translate(0, 0) scale(1, 1)', transformOrigin: 'top left' },
      ], { duration, easing: 'cubic-bezier(.22,.7,.2,1)', fill: 'both' }));
    }
    root.querySelectorAll('.solution-slot').forEach((card, index) => {
      const from = previous.cards[index], digit = card.querySelector('.drum-face > span');
      if (!from) return;
      const to = card.getBoundingClientRect();
      if (digit && to.width && to.height) {
        const font = parseFloat(getComputedStyle(digit).fontSize);
        animations.current.push(digit.animate([
          { transform: `scale(${from.font / font / (from.box.width / to.width)}, ${from.font / font / (from.box.height / to.height)})` },
          { transform: 'scale(1, 1)' },
        ], { duration, easing: 'cubic-bezier(.22,.7,.2,1)', fill: 'both' }));
      }
      morph(card, from.box);
    });
    const remaining = root.querySelector('.solution-remaining-value');
    if (remaining && previous.timer) morph(remaining, previous.timer);
    root.querySelectorAll('.solution-heading, .solution-summary > p, .solution-time-label, .solution-used-time').forEach(element => {
      animations.current.push(element.animate([{ opacity: 0, transform: 'translateY(12px)' }, { opacity: 1, transform: 'translateY(0)' }], {
        duration: 650, delay: Math.min(1100, duration * .45), easing: 'ease-out', fill: 'both',
      }));
    });
  }, [state, solved]);
  useLayoutEffect(() => () => animations.current.forEach(animation => animation.cancel()), []);
  return <main ref={display} className={`player-display ${state.running || state.phase === 'paused' ? timerStage(state.remaining_seconds) : ''} ${ready ? 'is-ready' : ''} ${solved ? 'is-solved' : ''} ${expired ? 'is-expired' : ''} ${numbers ? 'view-digits' : state.game_view === 'lights_off' ? 'view-lights-off' : 'view-timer'} ${pregame || ready ? 'is-pregame' : ''}`} onDoubleClick={() => { if (document.fullscreenElement) void document.exitFullscreen().catch(() => {}); else void document.documentElement.requestFullscreen?.().catch(() => {}); }}>
    {solved || expired ? <ResultScreen key={`${state.phase}-${state.result_video_playing}`} won={solved} seconds={state.remaining_seconds} duration={state.duration_seconds} digits={state.solution_digits ?? state.digits.map(value => value ?? 0)} elapsed={state.result_at == null ? 5 : Math.max(0, state.server_time - state.result_at)} video={state.result_video_playing ? solved ? state.presentation.victory_video : state.presentation.defeat_video : null} /> : ready ? <p className="player-waiting">odotetaan seuraavan pelin käynnistystä...</p> : pregame && (slide.layout === 'seating' || slide.layout === 'movement') ? <IntroSequence slide={slide} /> : pregame && slide.layout === 'code' ? <CodeSlide key={state.slide_index} slide={slide} /> : pregame ? <div className="pregame-slide" key={`${state.slide_index}-${slide.media}-${slide.animation}`}>
      {slide.media && <SlideMedia key={slide.media} src={slide.media} title={slide.title} />}
      <div className={`slide-copy animation-${slide.animation}`}><h1>{slide.title}</h1><p>{slide.body}</p></div>
      <div className="slide-dots" aria-label={`Dia ${state.slide_index + 1} / ${state.presentation.slides.length}`}>{state.presentation.slides.map((_, i) => <i key={i} className={i === state.slide_index ? 'active' : ''} />)}</div>
    </div> : <div className="player-content">
      <div className="player-timer-frame">
        <div className="timer-light-strip" aria-hidden="true"><div className="led-strip"><i className="led-lights led-even" /><i className="led-lights led-odd" /></div></div>
        <GameTimer seconds={state.remaining_seconds} running={state.running} className="player-countdown" />
        <div className="player-timer-label">{state.phase === 'paused' ? 'AJASTIN PYSÄYTETTY' : 'AIKAA JÄLJELLÄ'}</div>
      </div>
      <div className={`player-indicators ${hasSlotIcons ? 'has-slot-icons' : ''}`} aria-label="Luetut numerot">{state.digits.map((digit, i) => <div className="player-indicator" key={i}>{hasSlotIcons && <div className="player-slot-icon"><SlotIcon icon={slotIcons[i]} /></div>}<div className="player-lamp"><span>{digit ?? ''}</span></div><span className="lamp-label">NUMERO</span></div>)}</div>
    </div>}
    {!connected && <div className="player-connection" role="status">Yhteys palautuu…</div>}

  </main>;
}
