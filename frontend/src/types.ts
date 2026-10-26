export interface Region { x: number; y: number; width: number; height: number }
export interface RoomEvent { id: number; type: string; at: string; payload: Record<string, unknown> }
export interface Slide { title: string; body: string; animation: 'fade' | 'float' | 'pulse' | 'none'; layout?: 'text' | 'seating' | 'movement' | 'code'; locked?: boolean; media: string | null }
export interface SoundChoice { name: string; file: string; duration_seconds: number | null }
export type SlotIconName = 'math' | 'golf' | 'car' | 'shovel';
export interface Presentation { slides: Slide[]; pregame_music: string | null; game_music: string | null; victory_video: string | null; defeat_video: string | null; victory_sounds: SoundChoice[]; victory_sound: string | null; volume: number; muted: boolean }
export interface RecognitionDiagnostic {
  engine?: string; input_image?: string | null; roi_image?: string | null; alternatives?: { digit: number; score: number }[];
  ocr_text: string | null; ocr_confidence: number | null; ocr_threshold: number | null;
  shape_digit: number | null; shape_confidence: number | null; reason: string;
}
export interface RoomState {
  mode: 'manual' | 'camera'; digits: (number | null)[]; correct: boolean[];
  remaining_seconds: number; duration_seconds: number; running: boolean;
  phase: 'ready' | 'pregame' | 'running' | 'paused' | 'solved' | 'expired'; server_time: number;
  slide_index: number; game_view: 'timer' | 'lights_off' | 'digits'; result_video_playing: boolean; presentation: Presentation;
  result_at: number | null; game_started_at: number | null; solution_digits: number[] | null;
  slot_icons: (SlotIconName | null)[];
  // Only dashboard sockets include the fields below.
  code: string; regions: Region[]; confidences: (number | null)[];
  recognition_diagnostics: (RecognitionDiagnostic | null)[]; recognition_at: number | null;
  camera: { status: 'off' | 'starting' | 'on' | 'error'; message: string; width: number; height: number; ocr_available: boolean };
  camera_index: number; require_human_approval: boolean; events: RoomEvent[];
}
export type SendCommand = (action: string, value?: unknown) => Promise<boolean>;
export function formatTime(seconds: number) {
  const rounded = Math.max(0, Math.ceil(seconds));
  const minutes = Math.floor(rounded / 60);
  return `${String(minutes).padStart(2, '0')}:${String(rounded % 60).padStart(2, '0')}`;
}
