import { useEffect, useState } from 'react';
import { ArrowLeft, Download, Save, Settings2, Upload } from 'lucide-react';
import { PresentationEditor } from './PresentationPanel';
import { VictorySoundPicker } from './VictorySoundPicker';
import type { RoomState, SendCommand } from './types';

export function SettingsPage({ state, command, disabled, onBack, onPreviewChange }: { state: RoomState; command: SendCommand; disabled: boolean; onBack: () => void; onPreviewChange: (value: boolean) => void }) {
  const [code, setCode] = useState(state.code);
  const [minutes, setMinutes] = useState(state.duration_seconds / 60);
  const [approval, setApproval] = useState(state.require_human_approval);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [failure, setFailure] = useState('');
  const [importFile, setImportFile] = useState<File | null>(null);
  const [transfer, setTransfer] = useState<'export' | 'import' | null>(null);
  const locked = disabled || busy || !['ready', 'pregame'].includes(state.phase);
  useEffect(() => { setCode(state.code); setMinutes(state.duration_seconds / 60); setApproval(state.require_human_approval); }, [state.code, state.duration_seconds, state.require_human_approval]);
  const dirty = code !== state.code || Math.round(minutes * 60) !== state.duration_seconds || approval !== state.require_human_approval;
  const valid = /^[0-9]{4}$/.test(code) && Number.isFinite(minutes) && Math.round(minutes * 60) >= 1 && minutes <= 240;
  async function save() {
    setBusy(true); setMessage('');
    try {
      if (await command('game_settings', { code, duration_seconds: Math.round(minutes * 60), require_human_approval: approval })) setMessage('Peliasetukset tallennettu.');
    } finally { setBusy(false); }
  }
  async function exportSettings() {
    setBusy(true); setTransfer('export'); setFailure(''); setMessage('');
    try {
      const response = await fetch('/api/settings/export');
      if (!response.ok) { const result = await response.json(); throw new Error(result.detail); }
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement('a');
      link.href = url; link.download = 'pakohuone-asetukset.zip'; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      setMessage('Tallennetut asetukset ja mediatiedostot viety ZIP-pakettiin.');
    } catch (error) { setFailure(error instanceof Error ? error.message : 'Vienti epäonnistui.'); }
    finally { setBusy(false); setTransfer(null); }
  }
  async function importSettings() {
    if (!importFile) return;
    setBusy(true); setTransfer('import'); setFailure(''); setMessage('');
    try {
      if (importFile.size > 512 * 1024 * 1024) throw new Error('Asetuspaketin enimmäiskoko on 512 Mt.');
      const response = await fetch('/api/settings/import', { method: 'POST', headers: { 'Content-Type': 'application/zip' }, body: importFile });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail);
      setImportFile(null); setMessage('Asetukset ja mediat tuotu. Peli on valmiustilassa.');
    } catch (error) { setFailure(error instanceof Error ? error.message : 'Tuonti epäonnistui.'); }
    finally { setBusy(false); setTransfer(null); }
  }
  const presentationKey = JSON.stringify({ ...state.presentation, volume: 0, muted: false, victory_sound: null, victory_sounds: [] });
  return <section className="settings-page" id="settings-page" aria-label="Peliasetukset">
    <div className="settings-page-heading"><p>Asetukset, diat ja mediat säilyvät seuraavia ryhmiä varten.</p><button className="button secondary" onClick={onBack}><ArrowLeft size={15} />Takaisin peliin</button></div>
    {locked && !busy && <p className="settings-notice">Pelin asetuksia voi muuttaa valmiustilassa tai alkuesityksen aikana. Äänenvoimakkuuden livesäätö toimii myös pelin aikana.</p>}
    <section className="panel general-settings"><div className="panel-heading"><div className="title-with-icon"><Settings2 size={17} /><h2>Pelin tiedot</h2></div></div>
      <fieldset disabled={locked}><div className="general-settings-fields"><label>Oikea koodi<input aria-label="Oikea koodi" inputMode="numeric" maxLength={4} value={code} onChange={event => { if (/^[0-9]{0,4}$/.test(event.target.value)) setCode(event.target.value); }} /><small>Neljä numeroa, myös alkunollat säilyvät.</small></label><label>Pelin kesto (min)<input aria-label="Pelin kesto min" type="number" min={1 / 60} max={240} step="any" value={minutes} onChange={event => setMinutes(Number(event.target.value))} /><small>Enintään 240 minuuttia.</small></label></div>
      <label className="settings-checkbox"><input type="checkbox" checked={approval} onChange={event => setApproval(event.target.checked)} />Vaadi ihmisen tarkistus ennen voittoa</label>
      <button className="button primary" disabled={!dirty || !valid} onClick={() => void save()}><Save size={15} />{busy ? 'Tallennetaan…' : 'Tallenna peliasetukset'}</button><span className="settings-save-note">{dirty ? 'Tallentamattomia muutoksia' : 'Peliasetukset tallennettu'}</span></fieldset>
    </section>
    <VictorySoundPicker state={state} command={command} disabled={disabled || busy} onPreviewChange={onPreviewChange} />
    <section className="panel settings-presentation" id="settings-presentation"><div className="panel-heading"><h2>Diat, musiikki ja lopetusvideot</h2></div><PresentationEditor key={presentationKey} presentation={state.presentation} command={command} disabled={locked} /></section>
    <section className="panel settings-transfer"><div className="panel-heading"><h2>Vienti ja tuonti</h2></div><div className="settings-transfer-body"><p>ZIP-paketti sisältää tallennetut peliasetukset, diat sekä niiden kuvat, videot ja musiikin. Sen voi siirtää myös toiselle tietokoneelle. Enimmäiskoko on 512 Mt.</p><button className="button secondary" disabled={disabled || busy || dirty} onClick={() => void exportSettings()}><Download size={15} />{transfer === 'export' ? 'Valmistellaan pakettia…' : 'Vie asetukset ja mediat'}</button>{dirty && <small>Tallenna peliasetukset ennen vientiä.</small>}
      <div className="settings-import"><label className="file-choice"><Upload size={14} />Valitse asetuspaketti<input type="file" accept=".zip" disabled={locked} onChange={event => { setImportFile(event.target.files?.[0] ?? null); event.target.value = ''; }} /></label>{importFile && <><span>{importFile.name}</span><p>Tuonti korvaa nykyiset asetukset ja palauttaa pelin valmiustilaan. Nykyiset mediat säilyvät palvelimella.</p><button className="button primary" disabled={locked} onClick={() => void importSettings()}>{transfer === 'import' ? 'Tuodaan asetuksia…' : 'Tuo asetukset'}</button></>}</div></div></section>
    {message && <p className="settings-success" role="status">{message}</p>}{failure && <p className="error-banner" role="alert">{failure}</p>}
  </section>;
}
