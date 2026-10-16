import math
import numpy as np
import pytest
from backend.models import Region
from backend.regions import crop_region, region_bounds


@pytest.mark.parametrize('width,height', [(1280,720),(1920,1080),(640,480)])
def test_crop_matches_normalized_overlay_in_original_pixels(width, height):
    region = Region(x=.1685716, y=.3001106, width=.0429669, height=.1395553)
    # Each pixel records its original coordinate, exposing any offset or scaling.
    ys, xs = np.indices((height,width))
    frame = np.stack((xs,ys),axis=-1)
    crop = crop_region(frame,region)
    left,top,right,bottom = region_bounds(region,width,height)
    assert crop[0,0].tolist() == [math.floor(region.x*width),math.floor(region.y*height)]
    assert crop[-1,-1].tolist() == [math.ceil((region.x+region.width)*width)-1,
                                   math.ceil((region.y+region.height)*height)-1]
    assert crop.shape[:2] == (bottom-top,right-left)


def test_crop_at_frame_edge_does_not_lose_last_pixel():
    region = Region(x=.9,y=.9,width=.1,height=.1)
    frame = np.arange(10000).reshape(100,100)
    crop = crop_region(frame,region)
    assert crop.shape == (10,10)
    assert crop[-1,-1] == frame[-1,-1]
