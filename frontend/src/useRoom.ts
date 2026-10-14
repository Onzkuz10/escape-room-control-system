import { useEffect, useState, useCallback } from 'react';
import type { RoomState } from './types';

export function useRoom(player: boolean) {
  const [state, setState] = useState<RoomState | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    let socket: WebSocket;
    let disposed = false;
    let retry: ReturnType<typeof setTimeout>;
    let delay = 500;
    let lastMessage = performance.now();
    const connect = () => {
      socket = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws?role=${player ? 'player' : 'dashboard'}`);
      socket.onopen = () => { if (!disposed) { setConnected(true); delay = 500; lastMessage = performance.now(); } };
      socket.onmessage = (message) => {
        if (disposed) return;
        lastMessage = performance.now();
        try {
          const data = JSON.parse(message.data);
          if (data.type === 'state') setState(data.state);
        } catch { setError('Palvelimen viestiä ei voitu lukea.'); }
      };
      socket.onclose = () => {
        if (!disposed) { setConnected(false); retry = setTimeout(connect, delay); delay = Math.min(delay * 2, 5000); }
      };
      socket.onerror = () => socket.close();
    };
    connect();
    const watchdog = setInterval(() => { if (socket?.readyState === WebSocket.OPEN && performance.now() - lastMessage > 3500) socket.close(); }, 1000);
    return () => { disposed = true; clearTimeout(retry); clearInterval(watchdog); socket?.close(); };
  }, [player]);
  const command = useCallback(async (action: string, value?: unknown) => {
    if (!connected) { setError('Yhteys palvelimeen puuttuu. Yritetään yhdistää uudelleen.'); return false; }
    try {
      const response = await fetch('/api/command', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, value: value ?? null }), signal: AbortSignal.timeout(12000),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'Tarkista syötetyt arvot.');
      setError('');
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Toiminto epäonnistui.');
      return false;
    }
  }, [connected]);
  return { state, connected, command, error, clearError: () => setError('') };
}
