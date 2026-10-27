import asyncio
from contextlib import asynccontextmanager
import json
import logging
import os
from pathlib import Path
import time
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from .audio import AudioManager
from .camera import CameraService
from .camera_devices import camera_devices
from .events import EventBus
from .models import Config, Command
from .digit_model import recognizer_available, MODEL_NAME
from .recognition import DigitRecognizer, Stabilizer
from .regions import crop_region
from .state import GameState
from .settings_bundle import export_bundle, import_bundle, media_paths, MAX_BUNDLE_SIZE
from .media_library import MediaLibrary
from .results import ResultStore

ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = Path(os.environ.get('ESCAPE_CONFIG', ROOT / 'runtime' / 'config.json'))
MEDIA_DIR = Path(os.environ.get('ESCAPE_MEDIA', ROOT / 'runtime' / 'media'))
LIBRARY_DIR = Path(os.environ.get('ESCAPE_LIBRARY', ROOT / 'media'))
BUNDLED_SETTINGS = ROOT / 'config' / 'default_settings.json'
media_library = MediaLibrary()
MEDIA_TYPES = {'.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.ogg': 'audio/ogg', '.m4a': 'audio/mp4',
               '.gif': 'image/gif', '.mp4': 'video/mp4', '.webm': 'video/webm',
               '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}
MAX_MEDIA_SIZE = 80 * 1024 * 1024


def load_bundled_settings(settings_file: Path, library_dir: Path, media_dir: Path):
    """Resolve portable media paths to this installation's local media URLs."""
    settings = json.loads(settings_file.read_text(encoding='utf-8'))
    presentation = settings['presentation']
    files = media_library.scan(library_dir, media_dir)['files']
    media_urls = {entry['path']: entry['url'] for entry in files}

    def resolve(path):
        if path is None:
            return None
        if path not in media_urls:
            raise ValueError(f'Oletusasetusten mediatiedosto puuttuu: {path}')
        return media_urls[path]

    for field in ('pregame_music', 'game_music', 'victory_music', 'victory_video', 'defeat_video', 'victory_sound'):
        presentation[field] = resolve(presentation.get(field))
    for choice in presentation.get('victory_sounds', []):
        choice['file'] = resolve(choice['file'])
    for slide in presentation.get('slides', []):
        slide['media'] = resolve(slide.get('media'))
    return Config.model_validate(settings)


def load_config():
    if CONFIG_FILE.exists():
        try:
            try:
                text = CONFIG_FILE.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                text = CONFIG_FILE.read_text(encoding='cp1252')  # Older Windows saves.
            return Config.model_validate_json(text)
        except (ValueError, OSError):
            logging.exception('Invalid config; using safe defaults')
            return Config()
    if CONFIG_FILE.resolve() == (ROOT / 'runtime' / 'config.json').resolve() and BUNDLED_SETTINGS.is_file():
        try:
            return load_bundled_settings(BUNDLED_SETTINGS, LIBRARY_DIR, MEDIA_DIR)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise RuntimeError(f'Valmiiden peliasetusten lataus epäonnistui: {exc}') from exc
    return Config()


bus = EventBus()
audio = AudioManager(bus)
def fixed_defeat_video():
    catalog = media_library.scan(LIBRARY_DIR, MEDIA_DIR)
    return next(item['url'] for item in catalog['files'] if item['path'] == 'videos/haviovideo-C334.mp4')


game = GameState(load_config(), bus, result_store=ResultStore(CONFIG_FILE.parent / 'game-results.json'))
game.fixed_defeat_video = fixed_defeat_video()
game.config.presentation.defeat_video = game.fixed_defeat_video
game.fixed_victory_sound = next(item['url'] for item in media_library.scan(LIBRARY_DIR, MEDIA_DIR)['files'] if item['path'] == 'sound-effects/lopetus-1.wav')
game.config.presentation.victory_sound = game.fixed_victory_sound
camera = CameraService()
clients: dict[WebSocket, bool] = {}


def save_config(config):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_FILE.with_suffix('.tmp')
    tmp.write_text(config.model_dump_json(indent=2), encoding='utf-8')
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
                observations = await asyncio.gather(*(
                    asyncio.to_thread(recognizer.recognize,
                                      crop_region(frame, r),
                                      diagnostics=True) for r in regions))
                # Drop in-flight OCR after a reset, calibration, mode switch or camera failure.
                if started_generation == game.generation and game.mode == 'camera' and camera.info()['status'] == 'on':
                    now = time.monotonic()
                    game.recognition_diagnostics = [o.diagnostic for o in observations]
                    game.recognition_at = time.time() - (now - timestamp)
                    if now - timestamp < 2:
                        stable = [s.update(o, now) for s, o in zip(stabilizers, observations)]
                        fresh = all(o.digit is not None and o.digit == stabilized.digit for o, stabilized in zip(observations, stable))
                        game.set_digits([o.digit for o in stable], [o.confidence for o in stable], allow_solve=fresh)
                    else:
                        game.set_digits([None] * 4, allow_solve=False)
                        stabilizers = [Stabilizer() for _ in range(4)]
            elif (frame is None or time.monotonic() - timestamp >= 2) and game.phase not in ('solved', 'expired'):
                stabilizers = [Stabilizer() for _ in range(4)]
                game.recognition_diagnostics, game.recognition_at = [None] * 4, None
                game.set_digits([None] * 4, allow_solve=False)
        await asyncio.sleep(.05)


@asynccontextmanager
async def lifespan(app):
    await asyncio.to_thread(media_library.scan, LIBRARY_DIR, MEDIA_DIR)
    tasks = [asyncio.create_task(broadcast_loop()), asyncio.create_task(recognition_loop())]
    yield
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await asyncio.to_thread(camera.stop)


app = FastAPI(title='Escape Room Control — V1', lifespan=lifespan)


@app.get('/api/health')
async def health():
    return {'ok': True, 'ocr_available': recognizer_available(), 'recognition_engine': MODEL_NAME, 'version': '1.0.0'}


@app.get('/api/state')
async def state():
    game.tick()
    return game.snapshot()


@app.get('/api/cameras')
def cameras():
    # A sync route runs native discovery in FastAPI's thread pool, not the game loop.
    try:
        return {'devices': camera_devices()}
    except Exception as exc:
        logging.exception('Camera discovery failed')
        raise HTTPException(503, 'Kameroiden haku epäonnistui. Tarkista asennus ja kameran käyttöoikeudet, ja yritä uudelleen.') from exc


@app.get('/api/media-library')
def media_catalog():
    return media_library.scan(LIBRARY_DIR, MEDIA_DIR)


@app.get('/api/settings/export')
async def export_settings():
    try:
        data = await asyncio.to_thread(export_bundle, game.config.model_copy(deep=True), MEDIA_DIR)
        return Response(data, media_type='application/zip', headers={
            'Content-Disposition': 'attachment; filename="pakohuone-asetukset.zip"', 'Cache-Control': 'no-store'})
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post('/api/settings/import')
async def import_settings(request: Request):
    if game.phase not in ('ready', 'pregame'):
        raise HTTPException(400, 'Tuo asetukset ennen pelin käynnistämistä.')
    payload = bytearray()
    async for chunk in request.stream():
        if len(payload) + len(chunk) > MAX_BUNDLE_SIZE:
            raise HTTPException(413, 'Asetuspaketin enimmäiskoko on 512 Mt.')
        payload.extend(chunk)
    created = []
    try:
        config, created = await asyncio.to_thread(import_bundle, bytes(payload), MEDIA_DIR)
        if getattr(game, 'fixed_defeat_video', None):
            config.presentation.defeat_video = game.fixed_defeat_video
        if getattr(game, 'fixed_victory_sound', None):
            config.presentation.victory_sound = game.fixed_victory_sound
        if any(slide.locked for slide in game.config.presentation.slides) and not any(slide.locked for slide in config.presentation.slides):
            raise ValueError('Asetuspaketin on sisällettävä lukittu pöytä- ja valonauhaohje.')
        if game.phase not in ('ready', 'pregame'):
            raise ValueError('Peli käynnistyi tuonnin aikana. Asetuksia ei muutettu.')
        await asyncio.to_thread(camera.stop)
        if game.phase not in ('ready', 'pregame'):
            raise ValueError('Peli käynnistyi tuonnin aikana. Asetuksia ei muutettu.')
        save_config(config)
        game.config = config
        game.reset()
        bus.emit('config.changed', field='import')
        return game.snapshot()
    except Exception as exc:
        for path in created:
            path.unlink(missing_ok=True)
        if isinstance(exc, (ValueError, ValidationError)):
            raise HTTPException(400, str(exc)) from exc
        if isinstance(exc, OSError):
            raise HTTPException(500, 'Asetusten tuonti epäonnistui. Tarkista runtime-kansion kirjoitusoikeus.') from exc
        raise


@app.post('/api/command')
async def command(cmd: Command):
    try:
        action, value = cmd.action, cmd.value
        if action == 'start':
            game.start()
        elif action == 'pregame':
            game.pregame()
        elif action in ('next_slide', 'previous_slide'):
            game.change_slide(1 if action == 'next_slide' else -1)
        elif action == 'next_view':
            game.next_view()
        elif action == 'previous_view':
            game.previous_view()
        elif action == 'audio_settings':
            if not isinstance(value, dict) or not value or set(value) - {'volume', 'muted'}:
                raise ValueError('Anna äänenvoimakkuus tai mykistys.')
            if ('volume' in value and type(value['volume']) not in (int, float)) or ('muted' in value and type(value['muted']) is not bool):
                raise ValueError('Virheellinen ääniasetus.')
            config = Config.model_validate({**game.config.model_dump(), 'presentation': {**game.config.presentation.model_dump(), **value}})
            save_config(config)
            game.config = config
        elif action == 'victory_sound':
            if getattr(game, 'fixed_victory_sound', None):
                raise ValueError('Voiton äänitehoste on kiinteä.')
            presentation = game.config.presentation.model_dump()
            if value and value not in [choice['file'] for choice in presentation['victory_sounds']]:
                catalog = await asyncio.to_thread(media_library.scan, LIBRARY_DIR, MEDIA_DIR)
                choice = next((item for item in catalog['files'] if item['category'] == 'sound-effects' and item['url'] == value), None)
                if not choice:
                    raise ValueError('Valitse lopetusääni tallennetuista vaihtoehdoista tai mediakansiosta.')
                # Scanning yields to other commands; retain live volume/settings edits.
                presentation = game.config.presentation.model_dump()
                if value not in [item['file'] for item in presentation['victory_sounds']]:
                    presentation['victory_sounds'].append({'name': Path(choice['name']).stem[:80], 'file': value,
                                                           'duration_seconds': choice['duration_seconds']})
            presentation['victory_sound'] = value
            config = Config.model_validate({**game.config.model_dump(), 'presentation': presentation})
            if value and not (MEDIA_DIR / Path(value).name).is_file():
                raise ValueError('Äänitiedosto puuttuu. Lisää ääni uudelleen.')
            save_config(config)
            game.config = config
        elif action == 'game_settings':
            if game.phase not in ('ready', 'pregame'):
                raise ValueError('Muuta peliasetuksia ennen pelin käynnistämistä.')
            if not isinstance(value, dict) or set(value) - {'code', 'duration_seconds', 'require_human_approval', 'slot_icons'}:
                raise ValueError('Tuntematon peliasetus.')
            config = Config.model_validate({**game.config.model_dump(), **value})
            save_config(config)
            game.config = config
            game.remaining = float(config.duration_seconds)
            game.clear_detection()
            bus.emit('config.changed', field='game_settings')
        elif action == 'presentation':
            if game.phase not in ('ready', 'pregame'):
                raise ValueError('Muokkaa esitystä ennen pelin käynnistämistä.')
            config = Config.model_validate({**game.config.model_dump(), 'presentation': value})
            if getattr(game, 'fixed_defeat_video', None):
                config.presentation.defeat_video = game.fixed_defeat_video
            if getattr(game, 'fixed_victory_sound', None):
                config.presentation.victory_sound = game.fixed_victory_sound
            if any(slide.locked for slide in game.config.presentation.slides) and not any(slide.locked for slide in config.presentation.slides):
                raise ValueError('Lukittua pöytä- ja valonauhaohjetta ei voi poistaa.')
            paths = media_paths(config)
            if any(path and not (MEDIA_DIR / Path(path).name).is_file() for path in paths):
                raise ValueError('Mediatiedosto puuttuu. Lataa tiedosto uudelleen.')
            save_config(config)
            game.config = config
            game.slide_index = min(game.slide_index, len(config.presentation.slides) - 1)
            bus.emit('config.changed', field='presentation')
        elif action == 'pause':
            game.pause()
        elif action == 'reset':
            game.reset()
        elif action == 'approve_solution':
            game.approve_solution()
        elif action == 'require_human_approval':
            if game.phase in ('solved', 'expired'):
                raise ValueError('Nollaa huone ennen tarkistustavan muuttamista.')
            if type(value) is not bool:
                raise ValueError('Tarkistusvalinnan pitää olla tosi tai epätosi.')
            config = Config.model_validate({**game.config.model_dump(), 'require_human_approval': value})
            save_config(config)
            game.config = config
            bus.emit('config.changed', field='require_human_approval')
            if not value and game.mode == 'manual':
                game.set_digits(game.digits)
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
            game.start()
            game.game_view = 'digits'
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
            index = game.config.camera_index if value is None else value
            if type(index) is not int or index < 0:
                raise ValueError('Valitse kamera luettelosta.')
            if index not in [device['index'] for device in await asyncio.to_thread(camera_devices)]:
                raise ValueError('Valittua kameraa ei enää löydy. Päivitä kameralista ja valitse kamera uudelleen.')
            config = Config.model_validate({**game.config.model_dump(), 'camera_index': index})
            if camera.info()['status'] in ('on', 'starting') and index != game.config.camera_index:
                raise ValueError('Sulje nykyinen kamera ennen kameran vaihtamista.')
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


@app.post('/api/media')
async def upload_media(request: Request, filename: str):
    suffix = Path(filename).suffix.lower()
    if suffix not in MEDIA_TYPES:
        raise HTTPException(400, 'Valitse MP3, WAV, OGG, M4A, GIF, MP4, WebM tai kuvatiedosto.')
    if game.phase not in ('ready', 'pregame'):
        raise HTTPException(400, 'Lataa media ennen pelin käynnistämistä.')
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    name = uuid4().hex + suffix
    target = MEDIA_DIR / name
    size = 0
    try:
        with target.open('wb') as stream:
            async for chunk in request.stream():
                size += len(chunk)
                if size > MAX_MEDIA_SIZE:
                    raise HTTPException(413, 'Tiedoston enimmäiskoko on 80 Mt.')
                stream.write(chunk)
        if size == 0:
            raise HTTPException(400, 'Tiedosto on tyhjä.')
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return {'url': f'/media/{name}'}


@app.post('/api/victory-sounds')
async def upload_victory_sound(request: Request, filename: str, duration_seconds: float = Query(default=4, ge=.1, le=30)):
    suffix = Path(filename).suffix.lower()
    if suffix not in ('.mp3', '.wav', '.ogg', '.m4a'):
        raise HTTPException(400, 'Valitse MP3-, WAV-, OGG- tai M4A-äänitiedosto.')
    if len(game.config.presentation.victory_sounds) >= 4:
        raise HTTPException(400, 'Neljä äänivaihtoehtoa on jo lisätty.')
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    name = uuid4().hex + suffix
    target = MEDIA_DIR / name
    size = 0
    try:
        with target.open('wb') as stream:
            async for chunk in request.stream():
                size += len(chunk)
                if size > MAX_MEDIA_SIZE:
                    raise HTTPException(413, 'Äänitiedoston enimmäiskoko on 80 Mt.')
                stream.write(chunk)
        if not size:
            raise HTTPException(400, 'Äänitiedosto on tyhjä.')
        presentation = game.config.presentation.model_dump()
        presentation['victory_sounds'].append({'name': f'Vaihtoehto {len(presentation["victory_sounds"]) + 1}', 'file': f'/media/{name}', 'duration_seconds': duration_seconds})
        config = Config.model_validate({**game.config.model_dump(), 'presentation': presentation})
        save_config(config)
        game.config = config
        return game.snapshot()
    except BaseException as exc:
        target.unlink(missing_ok=True)
        if isinstance(exc, ValueError):
            raise HTTPException(400, str(exc)) from exc
        if isinstance(exc, OSError):
            raise HTTPException(500, 'Äänen tallennus epäonnistui. Tarkista runtime-kansion kirjoitusoikeus.') from exc
        raise


@app.get('/media/{filename}')
async def media(filename: str):
    import re
    if not re.fullmatch(r'[a-f0-9]{32}\.[a-z0-9]+', filename):
        raise HTTPException(404, 'Tiedostoa ei löydy.')
    target = MEDIA_DIR / filename
    if target.suffix not in MEDIA_TYPES or not target.is_file():
        raise HTTPException(404, 'Tiedostoa ei löydy.')
    return FileResponse(target, media_type=MEDIA_TYPES[target.suffix], headers={'X-Content-Type-Options': 'nosniff'})


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
