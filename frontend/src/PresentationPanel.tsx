import { useState } from 'react';
import { AudioLines, ChevronLeft, ChevronRight, Pause, Play, Plus, RotateCcw, Trash2 } from 'lucide-react';
import type { Presentation, RoomState, SendCommand, Slide } from './types';
import { MediaSelect, type LibraryMedia } from './MediaLibrary';

export function PresentationPanel({ state, command, disabled, onReset, onSettings }: { state: RoomState; command: SendCommand; disabled: boolean; onReset: () => void; onSettings: () => void }) {
  const [busy, setBusy] = useState(false);
  const locked = disabled || busy;
  const pregame = state.phase === 'pregame';
  const playing = state.phase === 'running' || state.phase === 'paused';
  const finished = state.phase === 'solved' || state.phase === 'expired';
  const resultVideo = state.phase === 'solved' ? state.presentation.victory_video : state.presentation.defeat_video;
  async function send(action: string) {
    setBusy(true);
    try { await command(action); } finally { setBusy(false); }
  }
  return <section className="panel presentation-panel">
    <div className="panel-heading"><div className="title-with-icon"><AudioLines size={18} /><h2>Pelin ohjaus</h2></div><span className="badge">{pregame ? `DIA ${state.slide_index + 1} / ${state.presentation.slides.length}` : playing ? state.game_view === 'timer' ? 'AJASTIN' : state.game_view === 'lights_flicker' ? 'VALOT VÄLKKYVÄT' : state.game_view === 'lights_off' ? 'VALOT SAMMUNEET' : 'NUMEROT' : state.phase === 'solved' ? 'VOITTO' : state.phase === 'expired' ? 'AIKA LOPPUI' : 'PELIVALMISTELUT'}</span></div>
    <div className="presentation-flow" aria-label="Pelin vaiheet"><span className={pregame || state.phase === 'ready' ? 'active' : ''}>Alkudiat</span><ChevronRight size={14} /><span className={playing && state.game_view === 'timer' ? 'active' : ''}>Ajastin</span><ChevronRight size={14} /><span className={playing && state.game_view === 'lights_flicker' ? 'active' : ''}>Valot välkkyvät</span><ChevronRight size={14} /><span className={playing && state.game_view === 'lights_off' ? 'active' : ''}>Valot sammuneet</span><ChevronRight size={14} /><span className={playing && state.game_view === 'digits' ? 'active' : ''}>Numerot</span></div>
    <div className="presentation-actions">
      {state.phase === 'ready' && <button className="button primary" disabled={locked} onClick={() => send('pregame')}><Play size={15} />Aloita pre-game näkymä</button>}
      {pregame && <><button className="button primary" disabled={locked} onClick={() => send('start')}><Play size={15} />Käynnistä peli</button><div className="view-navigation"><button className="button secondary" disabled={locked || state.slide_index === 0} onClick={() => send('previous_slide')}><ChevronLeft size={15} />Edellinen dia</button><button className="button secondary" disabled={locked || state.slide_index >= state.presentation.slides.length - 1} onClick={() => send('next_slide')}>Seuraava dia<ChevronRight size={15} /></button></div></>}
      {playing && <><button className="button primary" disabled={locked} onClick={() => send(state.running ? 'pause' : 'start')}>{state.running ? <Pause size={15} /> : <Play size={15} />}{state.running ? 'Pysäytä ajastin' : 'Jatka peliä'}</button><div className="view-navigation"><button className="button secondary" disabled={locked || state.game_view === 'timer'} onClick={() => send('previous_view')}><ChevronLeft size={15} />Edellinen näkymä</button><button className="button secondary" disabled={locked || state.game_view === 'digits'} onClick={() => send('next_view')}>Seuraava näkymä<ChevronRight size={15} /></button></div></>}
      {finished && <div className="view-navigation"><button className="button secondary" disabled={locked || !state.result_video_playing} onClick={() => send('previous_view')}><ChevronLeft size={15} />Edellinen näkymä</button><button className="button primary" disabled={locked || state.result_video_playing || !resultVideo} onClick={() => send('next_view')}>Seuraava näkymä<ChevronRight size={15} /></button></div>}
      <button className="button subtle reset-game" disabled={locked} onClick={onReset}><RotateCcw size={14} />Nollaa huone</button>
    </div>
    <p className="session-description">{pregame ? `Pelaajien näytöllä: ${state.presentation.slides[state.slide_index].title} Peliaika ei vielä kulu.` : playing ? state.game_view === 'timer' ? 'Seuraava näkymä käynnistää valonauhan välkkymisen. Ohjaa fyysistä valonauhaa erikseen.' : state.game_view === 'lights_flicker' ? 'Valot välkkyvät: pelaajat saavat liikkua. Valot sammuvat 20 sekunnin jälkeen tai painikkeesta.' : state.game_view === 'lights_off' ? 'Valot ovat sammuneet. Pelaajat saavat liikkua. Seuraava näkymä suurentaa numerot.' : state.require_human_approval ? 'Numeronäkymä on käytössä. Ratkaisu odottaa ohjaajan hyväksyntää Varmistus ja hätävara -kohdassa.' : 'Numeronäkymä on käytössä. Kaikki oikeat numerot ratkaisevat pelin automaattisesti.' : state.phase === 'solved' ? state.result_video_playing ? 'Voittovideo on käytössä. Edellinen näkymä palauttaa tuloksen.' : resultVideo ? 'Tulos ja jäljellä oleva aika näkyvät pelaajille. Seuraava näkymä käynnistää voittovideon.' : 'Tulos ja jäljellä oleva aika näkyvät pelaajille. Voittovideota ei ole valittu.' : state.phase === 'expired' ? state.result_video_playing ? 'Häviövideo on käytössä. Edellinen näkymä palauttaa tulokseen.' : resultVideo ? 'Aika loppui. Seuraava näkymä käynnistää häviövideon.' : 'Aika loppui. Häviövideota ei ole valittu.' : 'Tarkista peliaika ja koodi. Avaa pelaajien näyttö ja aloita alkuesitys, kun ryhmä on paikalla.'}</p>
    <div className="presentation-open-settings"><button className="text-button" onClick={onSettings}><AudioLines size={14} />Diat, musiikki ja lopetusvideot<ChevronRight size={14} /></button></div>
  </section>;
}

export function PresentationEditor({ presentation, command, disabled, library = [] }: { presentation: Presentation; command: SendCommand; disabled: boolean; library?: LibraryMedia[] }) {
  const [draft, setDraft] = useState(presentation);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const locked = disabled || saving || uploading;
  const dirty = JSON.stringify({ ...draft, volume: presentation.volume, muted: presentation.muted, victory_sound: presentation.victory_sound, victory_sounds: presentation.victory_sounds }) !== JSON.stringify(presentation);
  function updateSlide(index: number, patch: Partial<Slide>) {
    setDraft(previous => ({ ...previous, slides: previous.slides.map((slide, i) => i === index ? { ...slide, ...patch } : slide) }));
    setMessage('');
  }
  async function upload(file: File | undefined, onDone: (url: string) => void) {
    if (!file) return;
    setMessage(''); setError('');
    if (file.size > 80 * 1024 * 1024) { setError('Tiedoston enimmäiskoko on 80 Mt.'); return; }
    setUploading(true);
    try {
      const response = await fetch(`/api/media?filename=${encodeURIComponent(file.name)}`, { method: 'POST', headers: { 'Content-Type': 'application/octet-stream' }, body: file, signal: AbortSignal.timeout(120000) });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Tiedoston lataus epäonnistui.');
      onDone(result.url);
      setMessage(`${file.name} ladattu. Ota muutos käyttöön tallentamalla esitys.`);
    } catch (err) { setError(err instanceof Error ? err.message : 'Tiedoston lataus epäonnistui.'); }
    finally { setUploading(false); }
  }
  async function save() {
    setSaving(true); setMessage('');
    try { if (await command('presentation', { ...draft, volume: presentation.volume, muted: presentation.muted, victory_sound: presentation.victory_sound, victory_sounds: presentation.victory_sounds })) setMessage('Esitys tallennettu.'); }
    finally { setSaving(false); }
  }
  return <div className="presentation-editor">
    <p className="editor-note">Musiikki kuuluu ohjauskeskuksen laitteesta ja seuraa pelin vaihetta. Pidä ohjauskeskuksen välilehti auki. Lisää omat tiedostosi ja tallenna esitys. Asetukset ja media säilyvät palvelimella.</p>
    <fieldset disabled={locked}>
      <div className="music-settings">{(['pregame_music', 'game_music', 'victory_music'] as const).map(field => {
        const label = field === 'pregame_music' ? 'Pre-game-musiikki' : field === 'game_music' ? 'Pelin taustamusiikki' : 'Voiton äänimaisema';
        return <div className="music-choice" key={field}><strong>{label}</strong><span>{draft[field] ? 'Oma äänitiedosto valittu' : 'Ei ääntä valittuna'}</span><MediaSelect files={library} category="music" value={draft[field]} label={`${label} mediakansiosta`} onChange={url => setDraft(previous => ({ ...previous, [field]: url }))} /><label className="file-choice">{draft[field] ? 'Vaihda ääni' : 'Lisää ääni'}<input type="file" accept=".mp3,.wav,.ogg,.m4a" aria-label={label} onChange={e => { void upload(e.target.files?.[0], url => setDraft(previous => ({ ...previous, [field]: url }))); e.target.value = ''; }} /></label>{draft[field] && <><audio controls preload="none" src={draft[field]} /><button className="text-button" onClick={() => setDraft(previous => ({ ...previous, [field]: null }))}>Poista äänivalinta</button></>}</div>;
      })}</div>

      <div className="music-settings result-video-settings">{(['victory_video', 'defeat_video'] as const).map(field => <div className="music-choice" key={field}>
        <strong>{field === 'victory_video' ? 'Voittovideo' : 'Häviövideo'}</strong>
        <span>{draft[field] ? 'Video valittu · käynnistyy Seuraava näkymä -painikkeesta' : 'Ei videota · näytetään lopputulos'}</span>
        {field === 'victory_video' ? <><MediaSelect files={library} category="videos" value={draft[field]} label="Voittovideo mediakansiosta" onChange={url => setDraft(previous => ({ ...previous, [field]: url }))} /><label className="file-choice">{draft[field] ? 'Vaihda video' : 'Lisää video'}<input type="file" accept=".mp4,.webm" aria-label="Voittovideo" onChange={e => { void upload(e.target.files?.[0], url => setDraft(previous => ({ ...previous, [field]: url }))); e.target.value = ''; }} /></label></> : <span>Kiinteä häviövideo</span>}
        {draft[field] && <><video className="slide-media" src={draft[field]} controls muted playsInline preload="metadata" />{field === 'victory_video' && <button className="text-button" onClick={() => setDraft(previous => ({ ...previous, [field]: null }))}>Poista video</button>}</>}
      </div>)}</div>
      <p className="editor-note">Lopetusvideot: MP4 tai WebM, enintään 80 Mt / tiedosto. Kuva toistuu pelaajien näytöllä, videon ääni ohjauskeskuksen laitteesta. Lopetusvideo käynnistyy pelin päätyttyä Seuraava näkymä -painikkeesta ja toistuu kerran.</p>
      <div className="slide-editor-list">{draft.slides.map((slide, index) => <article className={`slide-editor ${slide.locked ? 'is-locked' : ''}`} key={index}>
        <div className="slide-editor-heading"><strong>Dia {index + 1}{slide.locked ? ' · KIINTEÄ OHJEDIA' : ''}</strong><div><button className="button secondary icon-only" aria-label={`Siirrä dia ${index + 1} aiemmaksi`} disabled={index === 0 || slide.locked || draft.slides[index - 1]?.locked} onClick={() => setDraft(previous => { const slides = [...previous.slides]; [slides[index - 1], slides[index]] = [slides[index], slides[index - 1]]; return { ...previous, slides }; })}><ChevronLeft size={14} /></button><button className="button secondary icon-only" aria-label={`Siirrä dia ${index + 1} myöhemmäksi`} disabled={index === draft.slides.length - 1 || slide.locked || draft.slides[index + 1]?.locked} onClick={() => setDraft(previous => { const slides = [...previous.slides]; [slides[index], slides[index + 1]] = [slides[index + 1], slides[index]]; return { ...previous, slides }; })}><ChevronRight size={14} /></button><button className="button secondary icon-only" aria-label={`Poista dia ${index + 1}`} disabled={draft.slides.length === 1 || slide.locked} onClick={() => setDraft(previous => ({ ...previous, slides: previous.slides.filter((_, i) => i !== index) }))}><Trash2 size={14} /></button></div></div>
        <fieldset className="slide-content-fields" disabled={!!slide.locked}><label>Otsikko<input maxLength={120} value={slide.title} onChange={e => updateSlide(index, { title: e.target.value })} /></label>
        <label>Teksti<textarea maxLength={2000} rows={3} value={slide.body} onChange={e => updateSlide(index, { body: e.target.value })} /></label>
        <label>Tekstin animaatio<select value={slide.animation} onChange={e => updateSlide(index, { animation: e.target.value as Slide['animation'] })}><option value="fade">Häivytys</option><option value="float">Rauhallinen liike</option><option value="pulse">Hengitys</option><option value="none">Ei animaatiota</option></select></label>
        <label>Dian asettelu<select value={slide.layout ?? 'text'} onChange={e => updateSlide(index, { layout: e.target.value as Slide['layout'] })}><option value="text">Teksti ja media</option><option value="seating">Neljä pöytää ja animoidut paikat</option><option value="movement">Valonauhaohje (kiinteä pari pöytäohjeen kanssa)</option><option value="code">Koodi ja nuoli pöydälle</option></select></label>
        <label className="file-choice">{slide.media ? 'Vaihda animaatio tai kuva' : 'Lisää animaatio tai kuva'}<input type="file" accept=".gif,.mp4,.webm,.png,.jpg,.jpeg,.webp" aria-label={`Dian ${index + 1} animaatio`} onChange={e => { void upload(e.target.files?.[0], url => updateSlide(index, { media: url })); e.target.value = ''; }} /></label>
        <MediaSelect files={library} category="videos" value={slide.media} label={`Dian ${index + 1} video mediakansiosta`} onChange={url => updateSlide(index, { media: url })} />
        </fieldset>{slide.locked && <p className="editor-note"><strong>{slide.title}</strong><br />Pöytä- ja valonauhaohje muodostavat kiinteän animaatioparin. Järjestys, grafiikka ja siirtymä on lukittu.</p>}
        {slide.media && <><SlideMedia key={slide.media} src={slide.media} title={slide.title} controls /><button className="text-button" onClick={() => updateSlide(index, { media: null })}>Poista dian media</button></>}
      </article>)}</div>
      <button className="button secondary" disabled={draft.slides.length >= 20} onClick={() => setDraft(previous => ({ ...previous, slides: [...previous.slides, { title: 'Uusi dia', body: '', animation: 'fade', media: null }] }))}><Plus size={15} />Lisää dia</button>
      <p className="editor-note">Animaatiot: GIF, MP4 tai WebM. Myös tavalliset kuvat käyvät. Videoiden ääni on mykistetty. Enintään 20 diaa, 80 Mt / tiedosto.</p>
    </fieldset>
    <div className="editor-save"><button className="button primary" disabled={locked || !dirty} onClick={save}>{saving ? 'Tallennetaan…' : 'Tallenna esitys'}</button><span role="status">{uploading ? 'Ladataan tiedostoa…' : dirty ? 'Tallentamattomia muutoksia' : 'Esitys tallennettu'}</span></div>
    {message && <p className="editor-note" role="status">{message}</p>}{error && <p className="inline-error" role="alert">{error}</p>}
  </div>;
}

export function SlideMedia({ src, title, controls = false }: { src: string; title: string; controls?: boolean }) {
  const [failed, setFailed] = useState(false);
  if (failed) return <p className="media-error" role="status">Mediaa ei voitu näyttää. Tarkista tiedosto ja selaimen tuki.</p>;
  return /\.(mp4|webm)$/i.test(src) ? <video className="slide-media" src={src} autoPlay={!controls} loop muted playsInline controls={controls} onError={() => setFailed(true)} aria-label={title} /> : <img className="slide-media" src={src} alt={title} onError={() => setFailed(true)} />;
}
