import { useCallback, useEffect, useRef, useState } from 'react';
import { Camera, ScanLine, SlidersHorizontal, RotateCcw, Move, Maximize2, FileDown } from 'lucide-react';
import type { Region, RoomState, SendCommand } from './types';

interface CameraDevice { index: number; name: string }

export function CameraPanel({ state, command, disabled }: { state: RoomState; command: SendCommand; disabled: boolean }) {
  const [editing, setEditing] = useState(false);
  const [regions, setRegions] = useState(state.regions);
  const [active, setActive] = useState(0);
  const [index, setIndex] = useState(state.camera_index);
  const [devices, setDevices] = useState<CameraDevice[]>([]);
  const [discovering, setDiscovering] = useState(true);
  const [discoveryError, setDiscoveryError] = useState('');
  const discoveryPending = useRef(false);
  const selectedIndex = useRef(index);
  selectedIndex.current = index;
  const cameraActive = state.camera.status === 'on' || state.camera.status === 'starting';
  const activeCamera = useRef(cameraActive);
  activeCamera.current = cameraActive;
  const refreshCameras = useCallback(async () => {
    if (discoveryPending.current) return;
    discoveryPending.current = true;
    setDiscovering(true);
    try {
      const response = await fetch('/api/cameras', { cache: 'no-store', signal: AbortSignal.timeout(10000) });
      if (!response.ok) throw new Error('Kameroiden haku epäonnistui. Tarkista kameran käyttöoikeudet ja päivitä lista.');
      const data: { devices: CameraDevice[] } = await response.json();
      setDevices(data.devices);
      setDiscoveryError('');
      if (!activeCamera.current && data.devices.length && !data.devices.some(device => device.index === selectedIndex.current)) {
        setIndex(data.devices[0].index);
      }
    } catch (error) {
      setDiscoveryError(error instanceof Error ? error.message : 'Kameroiden haku epäonnistui. Päivitä lista.');
    } finally {
      discoveryPending.current = false;
      setDiscovering(false);
    }
  }, []);
  useEffect(() => {
    void refreshCameras();
    const timer = setInterval(() => { void refreshCameras(); }, 10000);
    return () => clearInterval(timer);
  }, [refreshCameras]);
  useEffect(() => {
    if (cameraActive) setIndex(state.camera_index);
  }, [cameraActive, state.camera_index]);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const draft = useRef(state.regions);
  const frame = useRef<HTMLDivElement>(null);
  const drag = useRef<{ index: number; mode: 'move' | 'resize'; x: number; y: number; region: Region } | null>(null);
  useEffect(() => {
    if (!dirty && !saving && !dragging) {
      draft.current = state.regions;
      setRegions(state.regions);
    }
  }, [state.regions, dirty, saving, dragging]);
  const locked = disabled || state.phase === 'solved' || state.phase === 'expired';
  const cameraOn = state.camera.status === 'on';
  const save = useCallback(async (closeEditor = false) => {
    const submitted = draft.current;
    const signature = JSON.stringify(submitted);
    setSaving(true);
    try {
      const ok = await command('regions', submitted);
      setSaveError(!ok);
      if (ok && JSON.stringify(draft.current) === signature) {
        setDirty(false);
        if (closeEditor) setEditing(false);
      }
      return ok;
    } catch {
      setSaveError(true);
      return false;
    } finally {
      setSaving(false);
    }
  }, [command]);
  useEffect(() => {
    if (!dirty || dragging || saving || saveError || locked) return;
    const timer = setTimeout(() => { void save(); }, 350);
    return () => clearTimeout(timer);
  }, [dirty, dragging, saving, saveError, locked, regions, save]);
  function changeRegions(next: Region[]) {
    draft.current = next;
    setRegions(next);
    setDirty(true);
    setSaveError(false);
  }
  function endDrag() { drag.current = null; setDragging(false); }
  function pointerDown(e: React.PointerEvent, i: number, mode: 'move' | 'resize') {
    if (!editing || locked) return;
    e.stopPropagation(); e.preventDefault();
    e.currentTarget.setPointerCapture(e.pointerId);
    drag.current = { index: i, mode, x: e.clientX, y: e.clientY, region: { ...draft.current[i] } };
    setDragging(true);
    setActive(i);
  }
  function pointerMove(e: React.PointerEvent) {
    const d = drag.current, rect = frame.current?.getBoundingClientRect();
    if (!d || !rect || locked) return;
    const dx = (e.clientX - d.x) / rect.width, dy = (e.clientY - d.y) / rect.height;
    const r = { ...d.region };
    if (d.mode === 'move') { r.x = Math.max(0, Math.min(1 - r.width, r.x + dx)); r.y = Math.max(0, Math.min(1 - r.height, r.y + dy)); }
    else { r.width = Math.max(.04, Math.min(1 - r.x, r.width + dx)); r.height = Math.max(.08, Math.min(1 - r.y, r.height + dy)); }
    changeRegions(draft.current.map((value, i) => i === d.index ? r : value));
  }
  async function cameraToggle() {
    setBusy(true);
    try { await command(cameraOn || state.camera.status === 'starting' ? 'camera_stop' : 'camera_start', index); }
    finally { setBusy(false); }
  }
  function update(key: keyof Region, value: number) {
    if (!Number.isFinite(value)) return;
    const r = { ...draft.current[active], [key]: value / 100 };
    r.width = Math.max(.04, Math.min(r.width, 1)); r.height = Math.max(.08, Math.min(r.height, 1));
    r.x = Math.max(0, Math.min(r.x, 1 - r.width)); r.y = Math.max(0, Math.min(r.y, 1 - r.height));
    changeRegions(draft.current.map((v, i) => i === active ? r : v));
  }
  return <section className="panel camera-panel" id="camera">
    <div className="panel-heading"><div className="title-with-icon"><Camera size={17} /><h2>Kameranäkymä</h2></div><span className={`badge ${cameraOn ? 'green' : ''}`}><span className="status-dot" />{cameraOn ? 'LIVE' : state.mode === 'manual' ? 'TESTITILA' : 'EI KUVAA'}</span></div>
    <div className={`camera-frame ${editing ? 'is-editing' : ''}`} style={{ maxWidth: 650 * state.camera.width / state.camera.height + 2 }}><div ref={frame} className="camera-surface" style={{ aspectRatio: `${state.camera.width}/${state.camera.height}` }} onPointerMove={pointerMove} onPointerUp={endDrag} onPointerCancel={endDrag} onLostPointerCapture={endDrag}>
      {cameraOn ? <img draggable={false} className="camera-image" src="/api/camera/stream" alt="Webkameran reaaliaikainen kuva" /> : state.mode === 'manual' ? <div className="demo-scene" aria-label="Manuaalisen testin esikatselu, ei kamerakuvaa">
        <div className="scene-grain" /><div className="paper-row">{state.digits.map((d, i) => <div className={`paper paper-${i}`} key={i}><span>{d ?? '?'}</span><small>{String(i + 1).padStart(2, '0')}</small></div>)}</div>
      </div> : <div className="camera-empty"><Camera size={32} strokeWidth={1.2} /><strong>{state.camera.status === 'starting' ? 'Kameraa avataan' : 'Kamera odottaa'}</strong><span>{state.camera.message}</span></div>}
      {(cameraOn || state.mode === 'manual') && regions.map((r, i) => <div key={i} className={`roi ${state.correct[i] ? 'correct' : ''} ${editing && active === i ? 'selected' : ''}`} style={{ left: `${r.x * 100}%`, top: `${r.y * 100}%`, width: `${r.width * 100}%`, height: `${r.height * 100}%` }} onPointerDown={e => pointerDown(e, i, 'move')}>
        <span className="roi-label">{String(i + 1).padStart(2, '0')}{state.correct[i] && ' ✓'}</span><i className="corner tl" /><i className="corner tr" /><i className="corner bl" /><i className="corner br" />
        {editing && <><Move className="move-icon" size={18} /><button aria-label={`Muuta alueen ${i + 1} kokoa`} className="resize-handle" onPointerDown={e => pointerDown(e, i, 'resize')}><Maximize2 size={12} /></button></>}
      </div>)}
      <div className="frame-caption"><span><ScanLine size={12} />{cameraOn ? `${state.camera.width} × ${state.camera.height}` : 'MANUAALINEN ESIKATSELU'}</span><span>4 TUNNISTUSALUETTA</span></div>
    </div>
    </div>
    <div className="camera-picker">
      <label htmlFor="camera-device">Kamera<select id="camera-device" value={devices.some(device => device.index === index) ? index : ''} disabled={disabled || busy || cameraActive} onChange={event => setIndex(Number(event.target.value))}>
        {!devices.some(device => device.index === index) && <option value="">{cameraActive ? 'Käytössä oleva kamera' : discovering ? 'Haetaan kameroita…' : 'Ei valittavaa kameraa'}</option>}
        {devices.map(device => <option key={device.index} value={device.index}>{device.name} ({device.index + 1})</option>)}
      </select></label>
      <button className="button small secondary" disabled={discovering || disabled} onClick={() => void refreshCameras()}><RotateCcw size={14} />{discovering ? 'Haetaan…' : 'Päivitä kamerat'}</button>
    </div>
    {discoveryError ? <p className="inline-error" role="alert">{discoveryError}</p> : !discovering && !devices.length && <p className="inline-error" role="status">Kameroita ei löytynyt palvelinta ajavalta tietokoneelta. Kytke kamera ja päivitä lista. Macissa salli terminaaliohjelman kameran käyttö Järjestelmäasetukset → Tietosuoja ja suojaus → Kamera.</p>}
    {cameraActive && <p className="camera-selection-help">Sulje kamera ennen toisen kameran valitsemista.</p>}
    <div className="camera-toolbar"><span className="muted"><span className={`small-dot ${cameraOn ? 'on' : ''}`} />{cameraOn ? 'Kamera yhdistetty' : 'Kamera ei ole käytössä'}</span><div><button className={`button subtle small ${editing ? 'active' : ''}`} onClick={() => setEditing(!editing)} disabled={locked}><SlidersHorizontal size={14} />Säädä alueita</button><button className="button small secondary" onClick={cameraToggle} disabled={disabled || busy || (!cameraActive && (!devices.some(device => device.index === index) || !!discoveryError))}><Camera size={14} />{busy ? 'Odota…' : cameraActive ? 'Sulje kamera' : 'Käynnistä kamera'}</button></div></div>
    {(editing || dirty || saving || saveError) && <p className={`crop-save-status ${saveError ? 'error' : ''}`} role={saveError ? 'alert' : 'status'}>{saveError ? 'Rajauksen tallennus epäonnistui. Tunnistus käyttää aiempia alueita. Yritä uudelleen Tallenna nyt -painikkeella.' : saving ? 'Rajauksia tallennetaan tunnistukseen…' : dirty ? dragging ? 'Rajaus muuttuu. Tunnistus päivittyy, kun vapautat kehyksen.' : 'Rajaukset ovat muuttuneet; automaattinen tallennus odottaa.' : 'Rajaukset tallennettu. Näkyvät kehykset ovat tunnistuksen käytössä.'}</p>}
    {!state.camera.ocr_available && <p className="inline-error">Käsialamalli puuttuu tai on vioittunut. Kamerakuva toimii, mutta numerotunnistus ei ole käytettävissä.</p>}
    {state.camera.status === 'error' && <p className="inline-error">{state.camera.message}</p>}
    {editing && <div className="calibration"><div className="calibration-top"><p>Vedä aluetta tai sen alakulmaa. Muutokset tallentuvat automaattisesti vapauttamisen jälkeen.</p><button className="icon-button" title="Palauta tallennetut alueet" aria-label="Palauta tallennetut alueet" disabled={saving} onClick={() => { draft.current = state.regions; setRegions(state.regions); setDirty(false); setSaveError(false); }}><RotateCcw size={15} /></button></div>
      <div className="calibration-fields"><label>Alue<select value={active} onChange={e => setActive(Number(e.target.value))}>{regions.map((_, i) => <option key={i} value={i}>0{i + 1}</option>)}</select></label>{(['x', 'y', 'width', 'height'] as const).map(key => <label key={key}>{({ x: 'X %', y: 'Y %', width: 'Leveys %', height: 'Korkeus %' })[key]}<input type="number" min={0} max={100} step={.1} value={Number((regions[active][key] * 100).toFixed(1))} onChange={e => update(key, Number(e.target.value))} /></label>)}</div>
      <div className="calibration-bottom"><button className="button primary small" disabled={locked || !dirty || saving} onClick={() => void save(true)}>{saving ? 'Tallennetaan…' : dirty ? 'Tallenna nyt' : 'Alueet tallennettu'}</button></div>
    </div>}
    <div className="camera-footnote"><span>Rajaa jokaiseen kehykseen yksi numero · musta numero valkoisella paperilla</span><a href="/printables/numerolaput.html" target="_blank" rel="noreferrer"><FileDown size={12} />Tulosta laput</a></div>
  </section>;
}
