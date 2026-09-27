import io
import numpy as np
from PIL import Image
from bc7enc import encode_bc7_white_alpha4
from render import dds_bc7

rng=np.random.default_rng(609150)
for alpha in [np.zeros((64,64),dtype=np.uint8),np.full((64,64),255,dtype=np.uint8),rng.integers(0,256,(64,64),dtype=np.uint8)]:
    raw=encode_bc7_white_alpha4(alpha)
    decoded=np.asarray(Image.open(io.BytesIO(dds_bc7(raw,64,64))).convert('RGBA'))
    palette=np.array([0,84,171,255])
    expected=palette[np.abs(alpha.astype(np.int32)[:,:,None]-palette).argmin(axis=2)]
    assert np.all(decoded[:,:,:3]==255)
    assert np.array_equal(decoded[:,:,3],expected),np.max(np.abs(decoded[:,:,3].astype(int)-expected))
print('PASS: BC7 mode 5, white RGB and four alpha levels, both anchor orientations')
