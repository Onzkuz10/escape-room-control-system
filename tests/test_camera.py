from types import SimpleNamespace
from unittest.mock import Mock

import cv2
import numpy as np
import pytest

from backend import camera_devices as devices
from backend.camera import CameraService


@pytest.mark.parametrize('system,backend', [('Darwin', cv2.CAP_AVFOUNDATION),
    ('Windows', cv2.CAP_MSMF), ('Linux', cv2.CAP_V4L2)])
def test_discovery_uses_capture_backend_without_probing(monkeypatch, system, backend):
    monkeypatch.setattr(devices.platform, 'system', lambda: system)
    enumerate_devices = Mock(return_value=[SimpleNamespace(index=0, name='Built-in'),
                                         SimpleNamespace(index=12, name='USB Camera')])
    monkeypatch.setattr(devices, 'enumerate_cameras', enumerate_devices)
    assert devices.camera_devices() == [{'index': 0, 'name': 'Built-in'}, {'index': 12, 'name': 'USB Camera'}]
    enumerate_devices.assert_called_once_with(backend)


def test_capture_on_mac_uses_same_backend_and_releases_camera(monkeypatch):
    monkeypatch.setattr(devices.platform, 'system', lambda: 'Darwin')
    service = CameraService()
    capture = Mock()
    def read():
        service.stop_event.set()
        return True, np.zeros((20, 30, 3), dtype=np.uint8)
    capture.read.side_effect = read
    constructor = Mock(return_value=capture)
    monkeypatch.setattr(cv2, 'VideoCapture', constructor)
    service._capture(12)
    constructor.assert_called_once_with(12, cv2.CAP_AVFOUNDATION)
    capture.release.assert_called_once()


def test_camera_constructor_failure_becomes_visible_error(monkeypatch):
    monkeypatch.setattr(cv2, 'VideoCapture', Mock(side_effect=RuntimeError('unavailable')))
    service = CameraService()
    service._capture(0)
    assert service.info()['status'] == 'error'
