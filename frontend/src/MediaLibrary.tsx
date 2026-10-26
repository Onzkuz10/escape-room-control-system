import { useEffect, useState } from 'react';

export interface LibraryMedia {
  category: 'music' | 'videos' | 'sound-effects';
  name: string; path: string; url: string; duration_seconds: number | null;
}

export function useMediaLibrary() {
  const [files, setFiles] = useState<LibraryMedia[]>([]);
  const [errors, setErrors] = useState<string[]>([]);
  useEffect(() => {
    const abort = new AbortController();
    let loading = false;
    async function refresh() {
      if (loading) return;
      loading = true;
      try {
        const response = await fetch('/api/media-library', { signal: abort.signal });
        if (!response.ok) throw new Error('Mediakansiota ei voitu lukea. Yritetään uudelleen automaattisesti.');
        const data = await response.json();
        if (!abort.signal.aborted) { setFiles(data.files); setErrors(data.errors); }
      } catch (failure) {
        if (!abort.signal.aborted) setErrors([failure instanceof Error ? failure.message : 'Mediakansion luku epäonnistui.']);
      } finally { loading = false; }
    }
    void refresh();
    const timer = window.setInterval(() => void refresh(), 5000);
    const focus = () => void refresh();
    window.addEventListener('focus', focus);
    return () => { abort.abort(); clearInterval(timer); window.removeEventListener('focus', focus); };
  }, []);
  return { files, errors };
}

export function MediaSelect({ files, category, value, label, onChange }: {
  files: LibraryMedia[]; category: LibraryMedia['category']; value: string | null;
  label: string; onChange: (value: string | null) => void;
}) {
  const options = [...new Map(files.filter(file => file.category === category).map(file => [file.url, file])).values()];
  if (!options.length) return null;
  return <label className="library-media-choice"><span>Valitse mediakansiosta</span><select aria-label={label} value={value ?? ''} onChange={event => onChange(event.target.value || null)}>
    <option value="">Ei valintaa</option>
    {value && !options.some(file => file.url === value) && <option value={value}>Nykyinen ladattu tiedosto</option>}
    {options.map(file => <option value={file.url} key={file.url}>{file.name}</option>)}
  </select></label>;
}
