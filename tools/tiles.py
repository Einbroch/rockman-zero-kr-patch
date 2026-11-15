"""4bpp 타일 영역을 팔레트로 그리기"""
import struct
from PIL import Image, ImageDraw
def pal_from(pram, n):
    out = []
    for i in range(16):
        c = struct.unpack_from('<H', pram, (n * 16 + i) * 2)[0]
        out.append(((c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3))
    return out
def tile_px(data, off):
    return [[(data[off + y * 4 + x // 2] >> ((x & 1) * 4)) & 15 for x in range(8)] for y in range(8)]
def sheet(data, off, ntiles, pal, path, cols=16, scale=3, label_base=None):
    rows = (ntiles + cols - 1) // cols
    im = Image.new('RGB', (cols * 9 * scale + 50, rows * 9 * scale), (0, 0, 40))
    d = ImageDraw.Draw(im)
    for t in range(ntiles):
        px = tile_px(data, off + t * 32)
        X = 50 + (t % cols) * 9 * scale; Y = (t // cols) * 9 * scale
        if t % cols == 0 and label_base is not None:
            d.text((2, Y + 4), f'{label_base + t:03x}', fill=(255, 255, 0))
        for y in range(8):
            for x in range(8):
                if px[y][x]:
                    d.rectangle([X + x * scale, Y + y * scale, X + x * scale + scale - 1, Y + y * scale + scale - 1], fill=pal[px[y][x]])
    im.save(path)
