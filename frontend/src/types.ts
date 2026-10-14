export interface Region { x: number; y: number; width: number; height: number }
export interface RoomEvent { id: number; type: string; at: string; payload: Record<string, unknown> }
export interface RoomState {
  mode: 'manual' | 'camera'; digits: (number | null)[]; correct: boolean[];
  remaining_seconds: number; duration_seconds: number; running: boolean;
  phase: 'ready' | 'running' | 'paused' | 'solved' | 'expired'; server_time: number;
  // Only dashboard sockets include the fields below.
  code: string; regions: Region[]; confidences: (number | null)[];
  camera: { status: 'off' | 'starting' | 'on' | 'error'; message: string; width: number; height: number };
  camera_index: number; events: RoomEvent[];
}
export type SendCommand = (action: string, value?: unknown) => Promise<boolean>;
export function formatTime(seconds: number) {
  const rounded = Math.max(0, Math.ceil(seconds));
  const minutes = Math.floor(rounded / 60);
  return `${String(minutes).padStart(2, '0')}:${String(rounded % 60).padStart(2, '0')}`;
}
