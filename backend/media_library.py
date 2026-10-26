"""Discover project media and import stable, portable copies into the media cache."""
import hashlib
import os
from pathlib import Path
import tempfile
import threading
import wave


AUDIO_SUFFIXES = {'.mp3', '.wav', '.ogg', '.m4a'}
CATEGORIES = {'music': AUDIO_SUFFIXES, 'videos': {'.mp4', '.webm'}, 'sound-effects': AUDIO_SUFFIXES}
MAX_FILE_SIZE = 80 * 1024 * 1024


class MediaLibrary:
    def __init__(self):
        self._lock = threading.Lock()
        self._known = {}

    def scan(self, root: Path, cache: Path):
        with self._lock:
            entries, errors, seen = [], [], set()
            root, cache = root.resolve(), cache.resolve()
            for category, suffixes in CATEGORIES.items():
                directory = root / category
                if not directory.is_dir() or not directory.resolve().is_relative_to(root):
                    continue
                for source in sorted(directory.rglob('*'), key=lambda p: p.as_posix().casefold()):
                    relative = source.relative_to(root)
                    if any(part.startswith('.') for part in relative.parts) or source.suffix.lower() not in suffixes:
                        continue
                    if not source.is_file() or not source.resolve().is_relative_to(root):
                        continue
                    key = (str(root), str(cache), str(relative))
                    seen.add(key)
                    try:
                        stat = source.stat()
                        fingerprint = (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
                        previous = self._known.get(key)
                        if previous and previous[0] == fingerprint and (cache / Path(previous[1]['url']).name).is_file():
                            entry = previous[1]
                        else:
                            if not 0 < stat.st_size <= MAX_FILE_SIZE:
                                raise ValueError('Tiedoston pitää olla 1 tavu – 80 Mt.')
                            filename = self._import(source, cache, fingerprint)
                            duration = None
                            if category == 'sound-effects' and source.suffix.lower() == '.wav':
                                try:
                                    with wave.open(str(cache / filename)) as audio:
                                        value = audio.getnframes() / audio.getframerate()
                                        if .1 <= value <= 30:
                                            duration = value
                                except (wave.Error, EOFError):
                                    pass
                            entry = {'category': category, 'name': source.relative_to(directory).as_posix(),
                                     'path': relative.as_posix(), 'url': f'/media/{filename}',
                                     'duration_seconds': duration}
                            self._known[key] = (fingerprint, entry)
                        entries.append(dict(entry))
                    except (OSError, ValueError) as exc:
                        errors.append(f'{relative.as_posix()}: {exc}')
            self._known = {key: value for key, value in self._known.items() if key in seen}
            return {'directory': 'media/', 'files': entries, 'errors': errors}

    @staticmethod
    def _import(source, cache, fingerprint):
        cache.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix='.library-', suffix='.tmp', dir=cache)
        temporary = Path(temporary)
        try:
            digest, size = hashlib.sha256(), 0
            with os.fdopen(descriptor, 'wb') as outgoing, source.open('rb') as incoming:
                while chunk := incoming.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_FILE_SIZE:
                        raise ValueError('Tiedoston enimmäiskoko on 80 Mt.')
                    digest.update(chunk)
                    outgoing.write(chunk)
            stat = source.stat()
            if (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns) != fingerprint:
                raise ValueError('Tiedoston siirto on vielä kesken; yritetään uudelleen automaattisesti.')
            checksum = digest.hexdigest()
            suffix = source.suffix.lower()
            target = cache / (checksum[:32] + suffix)
            if target.is_file():
                return target.name
            # Reuse older browser uploads, preserving existing selections and URLs.
            for candidate in cache.glob('*' + suffix):
                if candidate.stat().st_size == size:
                    with candidate.open('rb') as stream:
                        if hashlib.file_digest(stream, 'sha256').hexdigest() == checksum:
                            return candidate.name
            temporary.replace(target)
            return target.name
        finally:
            temporary.unlink(missing_ok=True)
