from pathlib import Path
import hashlib
import wave

import pytest
from backend.media_library import MediaLibrary


def put(root, name, content=b'audio'):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def test_discovers_nested_unicode_media_and_reloads_edits_without_duplicate_copies(tmp_path):
    root, cache = tmp_path / 'source', tmp_path / 'cache'
    source = put(root, 'music/Äänet/Odotus.MP3')
    put(root, 'videos/intro.webm', b'video')
    put(root, 'sound-effects/click.ogg', b'click')
    put(root, 'music/notes.txt')
    put(root, 'videos/.hidden.mp4')
    library = MediaLibrary()
    catalog = library.scan(root, cache)
    assert len(catalog['files']) == 3 and not catalog['errors']
    music = next(f for f in catalog['files'] if f['category'] == 'music')
    assert music['name'] == 'Äänet/Odotus.MP3'
    assert (cache / Path(music['url']).name).read_bytes() == b'audio'
    assert library.scan(root, cache) == catalog
    assert len(list(cache.iterdir())) == 3
    source.write_bytes(b'new audio')
    changed = library.scan(root, cache)
    assert next(f for f in changed['files'] if f['category'] == 'music')['url'] != music['url']
    source.unlink()
    assert len(library.scan(root, cache)['files']) == 2
    assert (cache / Path(music['url']).name).is_file()  # Existing selections survive.


def test_reuses_existing_browser_upload_instead_of_duplicating_sound_choices(tmp_path):
    root, cache = tmp_path / 'source', tmp_path / 'cache'
    put(root, 'sound-effects/Vaihtoehto 1.wav')
    original = put(cache, 'a' * 32 + '.wav')
    result = MediaLibrary().scan(root, cache)
    assert result['files'][0]['url'] == '/media/' + original.name
    assert len(list(cache.iterdir())) == 1


def test_wav_duration_and_rejected_empty_files(tmp_path):
    root, cache = tmp_path / 'source', tmp_path / 'cache'
    file = put(root, 'sound-effects/click.wav')
    with wave.open(str(file), 'wb') as output:
        output.setparams((1, 2, 8000, 1600, 'NONE', 'not compressed'))
        output.writeframes(b'\x00\x00' * 1600)
    put(root, 'music/empty.mp3', b'')
    result = MediaLibrary().scan(root, cache)
    assert result['files'][0]['duration_seconds'] == pytest.approx(.2)
    assert len(result['errors']) == 1 and 'empty.mp3' in result['errors'][0]
    assert not list(cache.glob('.library-*'))


def test_outside_symlink_is_not_imported(tmp_path):
    root, cache = tmp_path / 'source', tmp_path / 'cache'
    outside = put(tmp_path, 'private.mp3')
    target = root / 'music' / 'linked.mp3'
    target.parent.mkdir(parents=True)
    try:
        target.symlink_to(outside)
    except OSError:
        pytest.skip('Symlinks unavailable on this host')
    assert MediaLibrary().scan(root, cache)['files'] == []
    assert not cache.exists()
