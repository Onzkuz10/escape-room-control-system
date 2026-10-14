import asyncio
from contextlib import asynccontextmanager
import json
import logging
import os
from pathlib import Path
import shutil
import time

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from .audio import AudioManager
from .camera import CameraService
from .events import EventBus
from .models import Config, Command
from .recognition import DigitRecognizer, Stabilizer
from .state import GameState

ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = Path(os.environ.get('ESCAPE_CONFIG', ROOT / 'runtime' / 'config.json'))


def load_config():
    if CONFIG_FILE.exists():
        try:
            return Config.model_validate_json(CONFIG_FILE.read_text())
        except (ValueError, OSError):
            logging.exception('Invalid config; using safe defaults')
    return Config()


bus = EventBus()
audio = AudioManager(bus)
game = GameState(load_config(), bus)
camera = CameraService()
clients: dict[WebSocket, bool] = {}


def save_config(config):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_FILE.with_suffix('.tmp')
    tmp.write_text(config.model_dump_json(indent=2))
    tmp.replace(CONFIG_FILE)


async def broadcast_loop():
    while True:
        game.tick()
        info = camera.info()
        if info != game.camera:
            previous = game.camera['status']
            game.camera = info
            if previous != info['status']:
                bus.emit('camera.status', **info)
        if game.mode == 'camera' and info['status'] != 'on' and any(d is not None for d in game.digits) and game.phase not in ('solved', 'expired'):
            game.set_digits([None] * 4)
        async def send(ws, player):
            try:
                await asyncio.wait_for(ws.send_json({'type': 'state', 'state': game.snapshot(player)}), timeout=1)
            except Exception:
                clients.pop(ws, None)
                try:
                    await ws.close()
                except Exception:
                    pass
        await asyncio.gather(*(send(ws, role) for ws, role in list(clients.items())))
        await asyncio.sleep(.1)


async def recognition_loop():
    recognizer = DigitRecognizer()
    stabilizers = [Stabilizer() for _ in range(4)]
    generation, last_frame = -1, 0.
    while True:
        if game.generation != generation:
            stabilizers = [Stabilizer() for _ in range(4)]
            generation = game.generation
        if game.mode == 'camera' and game.phase not in ('solved', 'expired'):
            frame, timestamp = camera.latest()
            if frame is not None and timestamp != last_frame:
                regions = list(game.config.regions)
                started_generation = game.generation
                last_frame = timestamp
                def analyze():
                    height, width = frame.shape[:2]
                    return [recognizer.recognize(frame[int(r.y*height):int((r.y+r.height)*height), int(r.x*width):int((r.x+r.width)*width)]) for r in regions]
                observations = await asyncio.to_thread(analyze)
                # Drop in-flight OCR after a reset, calibration, mode switch or camera failure.
                if started_generation == game.generation and game.mode == 'camera' and camera.info()['status'] == 'on' and time.monotonic() - timestamp < 2:
                    now = time.monotonic()
                    stable = [s.update(o, now) for s, o in zip(stabilizers, observations)]
                    fresh = all(o.digit is not None and o.digit == stabilized.digit for o, stabilized in zip(observations, stable))
                    game.set_digits([o.digit for o in stable], [o.confidence for o in stable], allow_solve=fresh)
            elif frame is None and game.phase not in ('solved', 'expired'):
                stabilizers = [Stabilizer() for _ in range(4)]
        await asyncio.sleep(.18)


@asynccontextmanager
async def lifespan(app):
    tasks = [asyncio.create_task(broadcast_loop()), asyncio.create_task(recognition_loop())]
    yield
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await asyncio.to_thread(camera.stop)


app = FastAPI(title='Escape Room Control — V1', lifespan=lifespan)


@app.get('/api/health')
async def health():
    return {'ok': True, 'ocr_available': bool(shutil.which('tesseract')), 'version': '1.0.0'}


@app.get('/api/state')
async def state():
    game.tick()
    return game.snapshot()


@app.post('/api/command')
async def command(cmd: Command):
    try:
        action, value = cmd.action, cmd.value
        if action == 'start':
            game.start()
        elif action == 'pause':
            game.pause()
        elif action == 'reset':
            game.reset()
        elif action in ('mode', 'code', 'duration', 'regions', 'digits', 'digit', 'simulate') and game.phase in ('solved', 'expired'):
            raise ValueError('Nollaa huone ennen asetusten tai numeroiden muuttamista.')
        elif action == 'mode':
            if value not in ('manual', 'camera'):
                raise ValueError('Tuntematon tunnistustila.')
            if value != game.mode:
                game.mode = value
                game.clear_detection()
                bus.emit('mode.changed', mode=value)
        elif action == 'digit':
            if game.mode != 'manual':
                raise ValueError('Numerotesti vaatii manuaalisen tilan.')
            if not isinstance(value, dict) or type(value.get('index')) is not int or not 0 <= value['index'] <= 3 or (value.get('digit') is not None and (type(value['digit']) is not int or not 0 <= value['digit'] <= 9)):
                raise ValueError('Virheellinen numero tai paikka.')
            digits = list(game.digits)
            digits[value['index']] = value.get('digit')
            game.set_digits(digits)
        elif action == 'digits':
            if game.mode != 'manual':
                raise ValueError('Numerotesti on käytettävissä vain manuaalisessa tilassa.')
            if not isinstance(value, list) or len(value) != 4 or any(d is not None and (type(d) is not int or not 0 <= d <= 9) for d in value):
                raise ValueError('Anna neljä numeroa 0–9 tai tyhjää arvoa.')
            game.set_digits(value)
        elif action == 'simulate':
            game.mode = 'manual'
            game.clear_detection()
            bus.emit('game.simulated')
            game.set_digits([int(d) for d in game.config.code])
        elif action in ('code', 'duration', 'regions'):
            if action in ('code', 'duration') and game.running:
                raise ValueError('Pysäytä ajastin ennen peliasetusten muuttamista.')
            update = {'code': {'code': value}, 'duration': {'duration_seconds': value}, 'regions': {'regions': value}}[action]
            config = Config.model_validate({**game.config.model_dump(), **update})
            save_config(config)  # Persist before mutating live state.
            game.config = config
            if action == 'duration':
                game.reset()
            else:
                game.clear_detection()
            bus.emit('config.changed', field=action)
        elif action == 'camera_start':
            if not shutil.which('tesseract'):
                raise ValueError('Tesseract puuttuu. Asenna macOS:ssä: brew install tesseract')
            index = game.config.camera_index if value is None else value
            if type(index) is not int or not 0 <= index <= 9:
                raise ValueError('Kameran numero on 0–9.')
            config = Config.model_validate({**game.config.model_dump(), 'camera_index': index})
            save_config(config)
            camera.start(index)
            game.config = config
            if game.phase not in ('solved', 'expired'):
                game.clear_detection()
        elif action == 'camera_stop':
            await asyncio.to_thread(camera.stop)
            if game.mode == 'camera' and game.phase not in ('solved', 'expired'):
                game.clear_detection()
        game.tick()
        return game.snapshot()
    except (ValueError, ValidationError) as exc:
        raise HTTPException(400, str(exc)) from exc
    except OSError as exc:
        raise HTTPException(500, 'Asetusten tallennus epäonnistui. Tarkista runtime-kansion kirjoitusoikeus.') from exc


@app.websocket('/ws')
async def websocket(ws: WebSocket):
    player = ws.query_params.get('role') == 'player'
    await ws.accept()
    try:
        await ws.send_json({'type': 'state', 'state': game.snapshot(player)})
        clients[ws] = player
        while True:
            await ws.receive_text()  # Read-only socket. Commands use the validated API.
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        clients.pop(ws, None)


@app.get('/api/camera/stream')
async def camera_stream():
    async def frames():
        last = None
        while camera.info()['status'] in ('on', 'starting'):
            jpeg = camera.image()
            if jpeg and jpeg is not last:
                last = jpeg
                yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n'
            await asyncio.sleep(.06)
    return StreamingResponse(frames(), media_type='multipart/x-mixed-replace; boundary=frame', headers={'Cache-Control':'no-store'})


app.mount('/printables', StaticFiles(directory=ROOT / 'printables'), name='printables')
DIST = ROOT / 'frontend' / 'dist'
if DIST.exists():
    app.mount('/assets', StaticFiles(directory=DIST / 'assets'), name='assets')


@app.get('/')
@app.get('/player')
async def frontend():
    if not (DIST / 'index.html').exists():
        raise HTTPException(503, 'Käyttöliittymä puuttuu. Suorita frontend-kansiossa npm run build.')
    return FileResponse(DIST / 'index.html', headers={'Cache-Control': 'no-cache'})
