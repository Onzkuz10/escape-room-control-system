from io import BytesIO
from zipfile import ZipFile

import pytest
from backend.models import Config
from backend.settings_bundle import export_bundle, import_bundle


def test_bundle_rejects_path_traversal_and_leaves_media_untouched(tmp_path):
    data = BytesIO()
    with ZipFile(data, 'w') as archive:
        archive.writestr('config.json', Config().model_dump_json())
        archive.writestr('../config.json', 'bad')
    media = tmp_path / 'media'
    with pytest.raises(ValueError):
        import_bundle(data.getvalue(), media)
    assert not media.exists()


def test_bundle_requires_every_referenced_media_file(tmp_path):
    config = Config()
    config.presentation.game_music = '/media/' + 'a' * 32 + '.mp3'
    with pytest.raises(ValueError):
        export_bundle(config, tmp_path)
    data = BytesIO()
    with ZipFile(data, 'w') as archive:
        archive.writestr('config.json', config.model_dump_json())
    with pytest.raises(ValueError):
        import_bundle(data.getvalue(), tmp_path / 'media')
    assert not (tmp_path / 'media').exists()


def test_invalid_bundle_is_actionable(tmp_path):
    with pytest.raises(ValueError):
        import_bundle(b'not a zip', tmp_path)
