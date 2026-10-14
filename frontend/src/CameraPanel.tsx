import { useEffect, useRef, useState } from 'react';
import { Camera, ScanLine, SlidersHorizontal, RotateCcw, Move, Maximize2, FileDown } from 'lucide-react';
import type { Region, RoomState, SendCommand } from './types';

export function CameraPanel({ state, command, disabled }: { state: RoomState; command: SendCommand; disabled: boolean }) {
  const [editing, setEditing] = useState(false);
  const [regions, setRegions] = useState(state.regions);
  const [active, setActive] = useState(0);
  const [index, setIndex] = useState(state.camera_index);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const frame = useRef<HTMLDivElement>(null);
  const drag = useRef<{ index: number; mode: 'move' | 'resize'; x: number; y: number; region: Region } | null>(null);
  useEffect(() => { if (!dirty) setRegions(state.regions); }, [state.regions, dirty]);
  const locked = disabled || state.phase === 'solved' || state.phase === 'expired';
  const cameraOn = state.camera.status === 'on';
  function pointerDown(e: React.PointerEvent, i: number, mode: 'move' | 'resize') {
    if (!editing || locked) return;
    e.stopPropagation(); e.preventDefault();
    e.currentTarget.setPointerCapture(e.pointerId);
    drag.current = { index: i, mode, x: e.clientX, y: e.clientY, region: { ...regions[i] } };
    setActive(i);
  }
  function pointerMove(e: React.PointerEvent) {
    const d = drag.current, rect = frame.current?.getBoundingClientRect();
    if (!d || !rect) return;
    const dx = (e.clientX - d.x) / rect.width, dy = (e.clientY - d.y) / rect.height;
    const r = { ...d.region };
    if (d.mode === 'move') { r.x = Math.max(0, Math.min(1 - r.width, r.x + dx)); r.y = Math.max(0, Math.min(1 - r.height, r.y + dy)); }
    else { r.width = Math.max(.04, Math.min(1 - r.x, r.width + dx)); r.height = Math.max(.08, Math.min(1 - r.y, r.height + dy)); }
    setRegions(prev => prev.map((value, i) => i === d.index ? r : value)); setDirty(true);
  }
  async function cameraToggle() {
    setBusy(true);
    await command(cameraOn || state.camera.status === 'starting' ? 'camera_stop' : 'camera_start', index);
    setBusy(false);
  }
  async function save() { if (await command('regions', regions)) { setDirty(false); setEditing(false); } }
  function update(key: keyof Region, value: number) {
    const r = { ...regions[active], [key]: value / 100 };
    r.width = Math.max(.04, Math.min(r.width, 1)); r.height = Math.max(.08, Math.min(r.height, 1));
    r.x = Math.max(0, Math.min(r.x, 1 - r.width)); r.y = Math.max(0, Math.min(r.y, 1 - r.height));
    setRegions(regions.map((v, i) => i === active ? r : v)); setDirty(true);
  }
  return <section className="panel camera-panel" id="camera">
    <div className="panel-heading"><div className="title-with-icon"><Camera size={17} /><h2>Kameranäkymä</h2></div><span className={`badge ${cameraOn ? 'green' : ''}`}><span className="status-dot" />{cameraOn ? 'LIVE' : state.mode === 'manual' ? 'TESTITILA' : 'EI KUVAA'}</span></div>
    <div ref={frame} className={`camera-frame ${editing ? 'is-editing' : ''}`} style={{ aspectRatio: `${state.camera.width}/${state.camera.height}` }} onPointerMove={pointerMove} onPointerUp={() => { drag.current = null; }} onPointerCancel={() => { drag.current = null; }}>
      {cameraOn ? <img className="camera-image" src="/api/camera/stream" alt="Webkameran reaaliaikainen kuva" /> : state.mode === 'manual' ? <div className="demo-scene" aria-label="Manuaalisen testin esikatselu, ei kamerakuvaa">
        <div className="scene-grain" /><div className="paper-row">{state.digits.map((d, i) => <div className={`paper paper-${i}`} key={i}><span>{d ?? '?'}</span><small>{String(i + 1).padStart(2, '0')}</small></div>)}</div>
      </div> : <div className="camera-empty"><Camera size={32} strokeWidth={1.2} /><strong>{state.camera.status === 'starting' ? 'Kameraa avataan' : 'Kamera odottaa'}</strong><span>{state.camera.message}</span></div>}
      {(cameraOn || state.mode === 'manual') && regions.map((r, i) => <div key={i} className={`roi ${state.correct[i] ? 'correct' : ''} ${editing && active === i ? 'selected' : ''}`} style={{ left: `${r.x * 100}%`, top: `${r.y * 100}%`, width: `${r.width * 100}%`, height: `${r.height * 100}%` }} onPointerDown={e => pointerDown(e, i, 'move')}>
        <span className="roi-label">{String(i + 1).padStart(2, '0')}{state.correct[i] && ' ✓'}</span><i className="corner tl" /><i className="corner tr" /><i className="corner bl" /><i className="corner br" />
        {editing && <><Move className="move-icon" size={18} /><button aria-label={`Muuta alueen ${i + 1} kokoa`} className="resize-handle" onPointerDown={e => pointerDown(e, i, 'resize')}><Maximize2 size={12} /></button></>}
      </div>)}
      <div className="frame-caption"><span><ScanLine size={12} />{cameraOn ? `${state.camera.width} × ${state.camera.height}` : 'MANUAALINEN ESIKATSELU'}</span><span>4 TUNNISTUSALUETTA</span></div>
    </div>
    <div className="camera-toolbar"><span className="muted"><span className={`small-dot ${cameraOn ? 'on' : ''}`} />{cameraOn ? 'Kamera yhdistetty' : 'Kamera ei ole käytössä'}</span><div><button className={`button subtle small ${editing ? 'active' : ''}`} onClick={() => setEditing(!editing)} disabled={locked}><SlidersHorizontal size={14} />Säädä alueita</button><button className="button small secondary" onClick={cameraToggle} disabled={disabled || busy}><Camera size={14} />{busy ? 'Odota…' : cameraOn || state.camera.status === 'starting' ? 'Sulje kamera' : 'Käynnistä kamera'}</button></div></div>
    {state.camera.status === 'error' && <p className="inline-error">{state.camera.message}</p>}
    {editing && <div className="calibration"><div className="calibration-top"><p>Vedä aluetta tai sen alakulmaa. Rajaa jokaiseen alueeseen yksi kokonainen numero.</p><button className="icon-button" title="Palauta tallennetut alueet" aria-label="Palauta tallennetut alueet" onClick={() => { setRegions(state.regions); setDirty(false); }}><RotateCcw size={15} /></button></div>
      <div className="calibration-fields"><label>Alue<select value={active} onChange={e => setActive(Number(e.target.value))}>{regions.map((_, i) => <option key={i} value={i}>0{i + 1}</option>)}</select></label>{(['x', 'y', 'width', 'height'] as const).map(key => <label key={key}>{({ x: 'X %', y: 'Y %', width: 'Leveys %', height: 'Korkeus %' })[key]}<input type="number" min={0} max={100} step={.1} value={Number((regions[active][key] * 100).toFixed(1))} onChange={e => update(key, Number(e.target.value))} /></label>)}</div>
      <div className="calibration-bottom"><label className="camera-index">Kameran numero <input aria-label="Kameran numero" type="number" min={0} max={9} value={index} onChange={e => setIndex(Number(e.target.value))} /></label><button className="button primary small" disabled={locked || !dirty} onClick={save}>Tallenna alueet</button></div>
    </div>}
    <div className="camera-footnote"><span>Mustat numerot · valkoinen paperi · tasainen valo</span><a href="/printables/numerolaput.html" target="_blank" rel="noreferrer"><FileDown size={12} />Tulosta laput</a></div>
  </section>;
}
