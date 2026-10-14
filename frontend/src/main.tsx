import { createRoot } from 'react-dom/client';
import { LockKeyhole } from 'lucide-react';
import { useRoom } from './useRoom';
import { Dashboard } from './Dashboard';
import { Player } from './Player';
import './styles.css';

function App() {
  const player = location.pathname.replace(/\/$/, '') === '/player';
  const room = useRoom(player);
  if (!room.state) return <div className="loading-screen"><div className="brand-icon"><LockKeyhole size={28} /></div><h1>LOCK /</h1><p>Yhdistetään huoneen ohjaukseen…</p><span className="loading-line" /><small>Jos yhteys ei avaudu, tarkista että Python-palvelin on käynnissä.</small></div>;
  return player ? <Player state={room.state} connected={room.connected} /> : <Dashboard {...room} state={room.state} />;
}
createRoot(document.getElementById('root')!).render(<App />);
