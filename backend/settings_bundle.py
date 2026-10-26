"""Portable settings archives. Only validated media names are ever written."""
from io import BytesIO
from pathlib import Path
import re
from uuid import uuid4
from zipfile import BadZipFile, ZipFile, ZIP_STORED

from .models import Config

MAX_BUNDLE_SIZE = 512 * 1024 * 1024
MAX_FILE_SIZE = 80 * 1024 * 1024


def media_paths(config):
    p = config.presentation
    return {path for path in [p.pregame_music, p.game_music, p.victory_video, p.defeat_video,
                             p.victory_sound, *(choice.file for choice in p.victory_sounds),
                             *(slide.media for slide in p.slides)] if path}


def export_bundle(config, media_dir):
    output = BytesIO()
    paths = [(path, media_dir / Path(path).name) for path in media_paths(config)]
    if any(not file.is_file() for _, file in paths):
        raise ValueError('Mediatiedosto puuttuu. Lataa puuttuva media uudelleen ennen vientiä.')
    if sum(file.stat().st_size for _, file in paths) > MAX_BUNDLE_SIZE:
        raise ValueError('Pelin mediat ylittävät vientipaketin 512 Mt rajan.')
    with ZipFile(output, 'w', compression=ZIP_STORED) as archive:
        archive.writestr('config.json', config.model_dump_json(indent=2))
        for path, file in paths:
            archive.write(file, f'media/{Path(path).name}')
    return output.getvalue()


def import_bundle(data, media_dir):
    created = []
    try:
        with ZipFile(BytesIO(data)) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if len(names) > 128 or len(names) != len(set(names)) or 'config.json' not in names:
                raise ValueError('Asetuspaketista puuttuu config.json tai tiedostonimet toistuvat.')
            if any(name != 'config.json' and not re.fullmatch(r'media/[a-f0-9]{32}\.(mp3|wav|ogg|m4a|mp4|webm|gif|png|jpg|jpeg|webp)', name) for name in names):
                raise ValueError('Asetuspaketissa on tuntemattomia tiedostoja.')
            if sum(entry.file_size for entry in entries) > MAX_BUNDLE_SIZE or any(entry.file_size > MAX_FILE_SIZE for entry in entries):
                raise ValueError('Asetuspaketti ylittää kokorajan: yhteensä 512 Mt, yksi media 80 Mt.')
            if archive.getinfo('config.json').file_size > 256 * 1024:
                raise ValueError('Asetustiedosto on liian suuri.')
            config = Config.model_validate_json(archive.read('config.json'))
            paths = media_paths(config)
            if any(f'media/{Path(path).name}' not in names for path in paths):
                raise ValueError('Asetuspaketista puuttuu esityksen mediatiedostoja.')
            media_dir.mkdir(parents=True, exist_ok=True)
            replacements = {}
            for path in paths:
                name = uuid4().hex + Path(path).suffix
                target = media_dir / name
                created.append(target)
                target.write_bytes(archive.read(f'media/{Path(path).name}'))
                replacements[path] = f'/media/{name}'
            presentation = config.presentation
            for field in ('pregame_music', 'game_music', 'victory_video', 'defeat_video', 'victory_sound'):
                old = getattr(presentation, field)
                if old:
                    setattr(presentation, field, replacements[old])
            for choice in presentation.victory_sounds:
                choice.file = replacements[choice.file]
            for slide in presentation.slides:
                if slide.media:
                    slide.media = replacements[slide.media]
            return config, created
    except Exception as exc:
        for path in created:
            path.unlink(missing_ok=True)
        if isinstance(exc, (BadZipFile, KeyError, UnicodeError, RuntimeError, NotImplementedError)):
            raise ValueError('Tiedosto ei ole kelvollinen pelin asetuspaketti.') from exc
        raise
