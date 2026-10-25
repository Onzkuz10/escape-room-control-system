"""Enumerate native capture devices without opening or interrupting cameras."""
import platform

import cv2
from cv2_enumerate_cameras import enumerate_cameras


def capture_backend():
    return {'Darwin': cv2.CAP_AVFOUNDATION, 'Windows': cv2.CAP_MSMF,
            'Linux': cv2.CAP_V4L2}.get(platform.system(), cv2.CAP_ANY)


def camera_devices():
    # Use the same backend for discovery and capture: indices are backend-specific.
    return [{'index': device.index, 'name': device.name or f'Kamera {device.index + 1}'}
            for device in enumerate_cameras(capture_backend())]
