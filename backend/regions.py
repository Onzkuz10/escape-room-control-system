"""Map normalized overlay coordinates to the original camera pixels."""
import math


def region_bounds(region, width, height):
    left = max(0, min(width-1, math.floor(region.x * width)))
    top = max(0, min(height-1, math.floor(region.y * height)))
    right = max(left+1, min(width, math.ceil((region.x + region.width) * width)))
    bottom = max(top+1, min(height, math.ceil((region.y + region.height) * height)))
    return left, top, right, bottom


def crop_region(frame, region):
    left, top, right, bottom = region_bounds(region, frame.shape[1], frame.shape[0])
    return frame[top:bottom, left:right]
