import { useEffect, useState } from 'react';
import { ArrowUpRight, AudioLines, Check, CheckCheck, ChevronRight, CircleHelp, Clock3, ExternalLink, LayoutDashboard, List, LockKeyhole, Monitor, Radio, RotateCcw, Settings2, ShieldCheck, X, Zap } from 'lucide-react';
import { CameraPanel } from './CameraPanel';
import { PresentationPanel } from './PresentationPanel';
import { ControllerMusic } from './ControllerMusic';
import { AudioControls } from './AudioControls';
import { SettingsPage } from './SettingsPage';
import { GameTimer, timerStage } from './GameTimer';
import type { RecognitionDiagnostic, RoomEvent, RoomState, SendCommand } from './types';

const phaseLabels = { ready: 'Valmiina', pregame: 'Pre-game', running: 'Peli käynnissä', paused: 'Pysäytetty', solved: 'Huone ratkaistu', expired: 'Aika loppui' };
const eventLabels: Record<string, string> = { 'pregame.started': 'Pre-game aloitettu', 'pregame.slide': 'Esityksen dia vaihdettu', 'game.view': 'Pelaajien näkymä vaihdettu', 'system.ready': 'Ohjausjärjestelmä valmis', 'timer.started': 'Ajastin käynnistetty', 'timer.paused': 'Ajastin pysäytetty', 'timer.warning': 'Aikaa jäljellä alle 5 minuuttia', 'timer.expired': 'Peliaika päättyi', 'game.reset': 'Huone nollattu uutta peliä varten', 'game.solved': 'Kaikki numerot oikein — huone ratkaistu', 'game.simulated': 'Ratkaisun simulointi käynnistetty', 'mode.changed': 'Tunnistustila vaihdettu', 'config.changed': 'Asetukset tallennettu', 'camera.status': 'Kameran tila muuttui', 'digits.changed': 'Numerohavainto päivittyi' };
function eventText(e: RoomEvent) {
  if (e.type === 'game.solved' && e.payload.approved_by_operator) return 'Ohjaaja hyväksyi ratkaisun';
  if (e.type === 'digits.changed') return `Numerot: ${(e.payload.digits as (number | null)[]).map(d => d ?? '–').join('  ')}`;
  if (e.type === 'mode.changed') return `Tunnistustila: ${e.payload.mode === 'manual' ? 'manuaalinen' : 'kamera'}`;
  if (e.type === 'camera.status') return String(e.payload.message);
  return eventLabels[e.type] ?? e.type;
}

export function Dashboard({ state, connected, command, error, clearError }: { state: RoomState; connected: boolean; command: SendCommand; error: string; clearError: () => void }) {
  const [help, setHelp] = useState(false);
  const [resetDialog, setResetDialog] = useState<'reset' | 'approve' | null>(null);
  const [showAllEvents, setShowAllEvents] = useState(false);
  const [section, setSection] = useState(location.hash === '#settings' ? 'settings' : 'dashboard');
  const settingsPage = section === 'settings';
  const [busy, setBusy] = useState(false);
  const [previewingSound, setPreviewingSound] = useState(false);
  const [showCamera, setShowCamera] = useState(state.mode === 'camera');
  useEffect(() => { if (state.mode === 'camera' || state.camera.status === 'on') setShowCamera(true); }, [state.mode, state.camera.status]);
  useEffect(() => {
    if (!help && !resetDialog) return;
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') { setHelp(false); setResetDialog(null); } };
    document.addEventListener('keydown', onKey);
    const close = document.querySelector<HTMLButtonElement>('.modal-close'); close?.focus();
    return () => document.removeEventListener('keydown', onKey);
  }, [help, resetDialog]);
  const terminal = state.phase === 'solved' || state.phase === 'expired';
  const disabled = !connected || busy;
  const correctCount = state.correct.filter(Boolean).length;
  async function send(action: string, value?: unknown) { setBusy(true); const ok = await command(action, value); setBusy(false); return ok; }
  function navigate(id: string) {
    const next = id === 'settings' || id === 'presentation-settings' ? 'settings' : id;
    setSection(next);
    history.replaceState(null, '', next === 'settings' ? '#settings' : next === 'events' ? '#events' : location.pathname);
    requestAnimationFrame(() => { if (next === 'events') document.getElementById('events')?.scrollIntoView({ behavior: 'smooth' }); else if (id === 'presentation-settings') document.getElementById('settings-presentation')?.scrollIntoView({ behavior: 'smooth' }); else window.scrollTo({ top: 0 }); });
  }
  return <div className="dashboard-layout">
    <aside className="sidebar"><a className="brand" href="/"><div className="brand-icon"><LockKeyhole size={22} /></div><div><strong>LOCK<span> / </span></strong><small>ESCAPE ROOM CONTROL</small></div></a>
      <div className="workspace-label">TYÖTILA<span>V1.0</span></div>
      <div className="room-selector"><span className="room-avatar">01</span><div><strong>Huone 01</strong><small>Paikallinen ympäristö</small></div><ChevronRight size={15} /></div>
      <div className="nav-label">HALLINTA</div><nav><button className={section === 'dashboard' ? 'selected' : ''} onClick={() => navigate('dashboard')}><LayoutDashboard size={17} />Ohjauspaneeli<span className="nav-active-dot" /></button><a href="/player" target="_blank" rel="noreferrer"><Monitor size={17} />Pelaajien näyttö<ArrowUpRight size={14} /></a><button className={section === 'settings' ? 'selected' : ''} onClick={() => navigate('settings')}><Settings2 size={17} />Peliasetukset</button><button className={section === 'events' ? 'selected' : ''} onClick={() => navigate('events')}><List size={17} />Tapahtumaloki</button></nav>
      <div className="sidebar-note"><AudioLines size={19} /><strong>Ääni ohjauskeskuksesta</strong><p>Pidä tämä välilehti auki pelin ajan. Musiikki ja lopetusvideoiden ääni kuuluvat tämän laitteen kaiuttimista.</p></div>
      <div className="sidebar-bottom"><div className="connection"><span className={`small-dot ${connected ? 'on' : 'warning'}`} /><strong>{connected ? 'Paikallinen yhteys' : 'Yhdistetään uudelleen'}</strong></div><button onClick={() => setHelp(true)}><CircleHelp size={15} />Käyttöohje<ArrowUpRight size={12} /></button></div>
    </aside>
    <main className="main-content" id="dashboard"><header className="page-header"><div><div className="eyebrow"><span className="small-dot on" />HUONE 01 <span className="slash">/</span> OHJAUSKESKUS</div><h1>{settingsPage ? 'Peliasetukset' : 'Huoneen ohjaus'}<span>.</span></h1><p>{settingsPage ? 'Tallenna pelin tiedot, esitys ja mediat.' : 'Esitys, peliaika ja numerot yhdessä paikassa.'}</p></div><a className="button secondary player-link" href="/player" target="_blank" rel="noreferrer"><Monitor size={16} />Avaa pelaajien näyttö<ExternalLink size={13} /></a></header>
      {!connected && <div className="connection-banner" role="status">Yhteys katkesi. Näytetty tila on viimeisin vastaanotettu. Yhteys palautuu automaattisesti.</div>}
      {error && <div className="error-banner" role="alert"><span>{error}</span><button onClick={clearError} aria-label="Sulje virheilmoitus"><X size={16} /></button></div>}
      <ControllerMusic state={state} previewing={previewingSound} />
      <AudioControls state={state} command={command} disabled={!connected} />
      {settingsPage && <SettingsPage onPreviewChange={setPreviewingSound} state={state} command={command} disabled={disabled} onBack={() => navigate('dashboard')} />}
      <div hidden={settingsPage}>
      <div className="overview-strip"><div><span className={`overview-icon ${state.running || state.phase === 'solved' ? 'green' : ''}`}><Radio size={17} /></span><div><small>HUONEEN TILA</small><strong>{phaseLabels[state.phase]}</strong></div></div><div><span className="overview-icon"><ScanIcon /></span><div><small>TUNNISTUS</small><strong>{state.mode === 'manual' ? 'Manuaalinen testitila' : 'Kameratunnistus'}</strong></div></div><div><span className={`overview-icon ${correctCount ? 'green' : ''}`}><ShieldCheck size={17} /></span><div><small>KOODIN EDISTYMINEN</small><strong>{correctCount}<span className="muted"> / 4 numeroa oikein</span></strong></div><div className="mini-progress">{state.correct.map((c, i) => <i key={i} className={c ? 'complete' : ''} />)}</div></div></div>
      <PresentationPanel onSettings={() => navigate('presentation-settings')} state={state} command={command} disabled={disabled} onReset={() => { if (state.phase === 'ready' && state.digits.every(d => d === null)) void send('reset'); else setResetDialog('reset'); }} />
      <div className="control-grid"><div className="left-column"><details className="camera-disclosure" open={showCamera} onToggle={event => setShowCamera(event.currentTarget.open)}><summary><span>Kamera ja rajaukset</span><span className={`badge ${state.camera.status === 'on' ? 'green' : ''}`}>{state.camera.status === 'on' ? 'LIVE' : 'AVAA ASETUKSET'}</span></summary><CameraPanel state={state} command={command} disabled={disabled} /></details>
        <section className="panel detection-panel"><div className="panel-heading"><div className="title-with-icon"><Zap size={17} /><h2>Numerotunnistus</h2></div><div className="segmented" role="group" aria-label="Tunnistustila"><button className={state.mode === 'camera' ? 'selected' : ''} disabled={disabled || terminal} onClick={() => send('mode', 'camera')}>Kamera</button><button className={state.mode === 'manual' ? 'selected' : ''} disabled={disabled || terminal} onClick={() => send('mode', 'manual')}>Manuaalinen</button></div></div>
          <p className="panel-intro">{state.mode === 'manual' ? 'Syötä numerot ja testaa merkkivalot ilman kameraa.' : terminal ? 'Tunnistus on pysähtynyt pelin päätyttyä. Nollaa huone jatkaaksesi kameratunnistusta.' : 'Näet alla myös hylättyjen havaintojen mallipisteet ja hylkäyssyyn.'}</p>
          <div className="digit-grid">{state.digits.map((digit, i) => <div className={`digit-card ${state.correct[i] ? 'correct' : digit !== null ? 'incorrect' : ''}`} key={i}><div className="digit-card-top"><span>PAIKKA 0{i + 1}</span><span className="digit-indicator">{state.correct[i] && <Check size={10} strokeWidth={3} />}</span></div><div className="detected-digit">{digit ?? ''}</div><span className="digit-status">{state.correct[i] ? 'Oikein' : digit !== null ? 'Väärä numero' : 'Odottaa numeroa'}</span>{state.mode === 'manual' ? <label className="manual-input"><span>Testinumero</span><input aria-label={`Testinumero ${i + 1}`} inputMode="numeric" type="text" maxLength={1} placeholder="" value={digit ?? ''} disabled={disabled || terminal} onChange={e => { const value = e.target.value; if (/^[0-9]?$/.test(value)) void command('digit', { index: i, digit: value === '' ? null : Number(value) }); }} /></label> : <><span className="confidence">{state.confidences[i] !== null ? `Havaintopisteet ${Math.round(state.confidences[i]!)} / 100` : 'Ei vakaata havaintoa'}</span><OcrDetails info={state.recognition_diagnostics?.[i] ?? null} stale={state.recognition_at == null || state.server_time - state.recognition_at > 3} /></>}</div>)}</div>
          <div className="section-footnote"><span><ShieldCheck size={13} />{state.mode === 'manual' ? 'Testisyötteet synkronoituvat pelaajien näytölle' : 'Ajallinen vakautus käytössä · epävarmat havainnot hylätään'}</span>{state.mode === 'manual' && <button disabled={disabled || terminal || state.digits.every(d => d === null)} onClick={() => send('digits', [null, null, null, null])}>Tyhjennä numerot</button>}</div>
        </section>
      </div><div className="right-column"><section className={`panel timer-panel ${state.running || state.phase === 'paused' ? timerStage(state.remaining_seconds) : ''} ${state.phase === 'solved' ? 'solved' : ''}`}><div className="panel-heading"><div className="title-with-icon"><Clock3 size={17} /><h2>Peliaika</h2></div><span className={`badge ${state.running || state.phase === 'solved' ? 'green' : state.phase === 'expired' ? 'amber' : ''}`}><span className="status-dot" />{phaseLabels[state.phase]}</span></div><GameTimer seconds={state.remaining_seconds} running={state.running} className="timer-value" /><div className="timer-label">AIKAA JÄLJELLÄ</div><div className="timer-progress"><span style={{ width: `${Math.min(100, state.remaining_seconds / state.duration_seconds * 100)}%` }} /></div><p className="timer-sync"><span className={`small-dot ${connected ? 'on' : 'warning'}`} />{connected ? 'Synkronoitu pelaajien näytön kanssa' : 'Odotetaan palvelinyhteyttä'}</p></section>
        <section className="panel operator-safety"><div className="panel-heading"><div className="title-with-icon"><ShieldCheck size={17} /><h2>Varmistus ja hätävara</h2></div></div>
          <label className="approval-switch"><span><strong>Vaadi ihmisen tarkistus</strong><small>{state.require_human_approval ? 'Voitto vaatii ohjaajan hyväksynnän.' : 'Oikea koodi ratkaisee pelin automaattisesti.'}</small></span><input type="checkbox" role="switch" aria-label="Vaadi ihmisen tarkistus" checked={state.require_human_approval} disabled={disabled || terminal} onChange={event => void send('require_human_approval', event.target.checked)} /></label>
          {state.require_human_approval && correctCount === 4 && ['running', 'paused'].includes(state.phase) && <p className="approval-pending" role="status">Kaikki numerot oikein. Odotetaan hyväksyntääsi.</p>}
          <button className="button secondary full-width approve-solution" disabled={disabled || !['running', 'paused'].includes(state.phase)} onClick={() => setResetDialog('approve')}><CheckCheck size={16} />Hyväksy ratkaisu</button>
          <p className="subtle-note">Hätävara: päättää pelin voittoon myös silloin, kun kamera ei tunnista oikeaa ratkaisua.</p>
        </section>
      </div></div>
      <section className="panel events-panel" id="events"><div className="panel-heading"><div className="title-with-icon"><List size={17} /><h2>Tapahtumaloki</h2><span className="event-count">{state.events.length}</span></div><button className="text-button" onClick={() => setShowAllEvents(!showAllEvents)}>{showAllEvents ? 'Näytä viimeisimmät' : 'Näytä kaikki'}<ChevronRight size={13} /></button></div><div className="event-list" aria-live="off">{state.events.slice(0, showAllEvents ? 60 : 4).map(event => <div className="event-row" key={event.id}><span className={`event-mark ${event.type === 'game.solved' ? 'success' : ''}`}>{event.type === 'game.solved' ? <CheckCheck size={14} /> : <span />}</span><span>{eventText(event)}</span><time dateTime={event.at}>{new Date(event.at).toLocaleTimeString('fi-FI', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</time></div>)}</div></section>

      </div>
    </main>
    {(help || resetDialog) && <div className="modal-backdrop" onClick={() => { setHelp(false); setResetDialog(null); }}><dialog open className="modal" aria-labelledby="modal-title" onClick={e => e.stopPropagation()} onKeyDown={e => { if (e.key === 'Tab') { const elements = Array.from(e.currentTarget.querySelectorAll<HTMLButtonElement | HTMLAnchorElement>('button:not(:disabled), a[href]')); const first = elements[0], last = elements[elements.length - 1]; if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); } else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); } } }}><button className="modal-close icon-button" aria-label="Sulje" onClick={() => { setHelp(false); setResetDialog(null); }}><X size={20} /></button>{resetDialog ? <><div className="modal-icon"><RotateCcw size={25} /></div><h2 id="modal-title">{resetDialog === 'approve' ? 'Hyväksytäänkö ratkaisu?' : 'Valmis uuteen peliin?'}</h2><p>{resetDialog === 'approve' ? 'Peli päättyy heti voittoon. Voittovideo käynnistetään erikseen Seuraava näkymä -painikkeesta. Kameran tunnistamaa koodia ei tarkisteta. Tätä ei voi perua nollaamatta peliä.' : 'Nollaus palauttaa koko peliajan, tyhjentää numerot ja poistaa ratkaisun. Tallennetut asetukset säilyvät.'}</p><div className="modal-actions"><button className="button secondary" onClick={() => setResetDialog(null)}>Peruuta</button><button className="button primary" onClick={async () => { if (await send(resetDialog === 'approve' ? 'approve_solution' : 'reset')) setResetDialog(null); }}>{resetDialog === 'approve' ? 'Hyväksy ja päätä peli' : 'Nollaa huone'}</button></div></> : <><div className="modal-icon"><CircleHelp size={25} /></div><h2 id="modal-title">Näin käynnistät huoneen</h2><ol><li>Avaa pelaajien näyttö toisessa välilehdessä tai saman verkon laitteella osoitteessa <code>{location.origin}/player</code>.</li><li>Valitse peliaika ja oikea nelinumeroinen koodi.</li><li>Testaa numerot manuaalisesti tai käynnistä kamera, valitse Kamera-tila ja rajaa jokainen numerolappu omaan alueeseensa.</li><li>Aloita pre-game, vaihda diat ja paina Käynnistä peli. Paina pelin aikana Seuraava näkymä: numerot suurenevat ja oikeellisuus tarkistetaan automaattisesti.</li></ol><p>Pelaajien näytön kaksoisnapsautus avaa koko näytön. Fyysistä kameraa käytetään palvelinta ajavalla Macilla. Näkymän voi näyttää erillisellä laitteella ilman kameraa.</p><a className="button secondary" href="/printables/numerolaput.html" target="_blank" rel="noreferrer">Avaa tulostettavat numerolaput<ExternalLink size={14} /></a></>}</dialog></div>}
  </div>;
}
function ScanIcon() { return <span className="scan-icon">#</span>; }

function OcrDetails({ info, stale }: { info: RecognitionDiagnostic | null; stale: boolean }) {
  const score = info?.ocr_confidence;
  const formatScore = (value: number) => value.toLocaleString('fi-FI', { maximumFractionDigits: 1 });
  return <div className={`ocr-details ${stale ? 'stale' : ''}`}>
    <strong>Käsialamalli <span>{score == null ? '—' : formatScore(score)}<small> / 100</small></span></strong>
    <span>Luettu: <b>{info?.ocr_text ?? '—'}</b></span>
    <span>Hyväksymisraja: {info?.ocr_threshold == null ? '—' : `${info.ocr_threshold} / 100`}</span>
    <span>{info?.engine ?? 'MNIST CNN (ONNX)'}</span>
    {info?.roi_image && <><small>Tunnistukseen leikattu kamerakuva</small><img className="roi-preview" src={info.roi_image} alt="Backendin käyttämä alkuperäinen kamerarajaus" /></>}
    {info?.input_image && <><small>Mallin syöte 28 × 28</small><img className="model-input" src={info.input_image} alt="Käsialamallille annettu 28 kertaa 28 pikselin numerokuva" /></>}
    {info?.alternatives?.length ? <span>Ehdokkaat: {info.alternatives.map(a => `${a.digit}: ${formatScore(a.score)}`).join(' · ')}</span> : null}
    <p>{stale ? 'Ei tuoretta analyysiä. ' : ''}{info?.reason ?? 'Odotetaan kamerakuvaa.'}</p>
    {score == null && info && <small>Mallille ei löytynyt luettavaa numerokuvaa.</small>}
  </div>;
}
