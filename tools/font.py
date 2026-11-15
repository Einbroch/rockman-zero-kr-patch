"""록맨 제로 4bpp 8x16 폰트: 코드 c -> base + (c&~0xf)*64 + (c&0xf)*32 (위), +0x200 (아래)"""
from PIL import Image
def glyph(rom, base, c):
    o = base + (c & 0xfff0) * 64 + (c & 0xf) * 32
    px = [[0]*8 for _ in range(16)]
    for half, oo in ((0, o), (1, o + 0x200)):
        d = rom[oo:oo+32]
        for y in range(8):
            for x in range(8):
                px[half*8+y][x] = (d[y*4 + x//2] >> ((x & 1)*4)) & 15
    return px
def sheet(rom, base, n, path, scale=3):
    cols = 16
    img = Image.new('RGB', (cols*9*scale+20*scale, ((n+cols-1)//cols)*17*scale), (40,40,80))
    pal = [(0,0,0)] + [(255-i*12, 255-i*12, 255-i*12) for i in range(15)]
    for c in range(n):
        g = glyph(rom, base, c)
        X = (c % cols)*9*scale; Y = (c // cols)*17*scale
        for y in range(16):
            for x in range(8):
                v = g[y][x]
                if v:
                    for dy in range(scale):
                        for dx in range(scale):
                            img.putpixel((X+x*scale+dx, Y+y*scale+dy), pal[v])
    img.save(path)
if __name__ == '__main__':
    import sys
    rom = open(sys.argv[1], 'rb').read()
    sheet(rom, int(sys.argv[2], 16), int(sys.argv[3], 16), sys.argv[4])
