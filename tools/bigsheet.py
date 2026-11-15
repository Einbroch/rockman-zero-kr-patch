import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from font import glyph
from PIL import Image, ImageDraw
def sh(rom,base,start,end,path,s=4,cols=16):
    rows=(end-start+cols-1)//cols
    img=Image.new('RGB',(40+cols*10*s,rows*18*s),(30,30,60)); d=ImageDraw.Draw(img)
    for c in range(start,end):
        g=glyph(rom,base,c); X=40+((c-start)%cols)*10*s; Y=((c-start)//cols)*18*s
        if (c-start)%cols==0: d.text((2,Y+20),f'{c:03x}',fill=(255,255,0))
        for y in range(16):
            for x in range(8):
                if g[y][x]: d.rectangle([X+x*s,Y+y*s,X+x*s+s-1,Y+y*s+s-1],fill=(255,255,255) if g[y][x]>2 else (150,150,150))
    img.save(path)
if __name__=='__main__':
    rom=open(sys.argv[1],'rb').read()
    sh(rom,int(sys.argv[2],16),int(sys.argv[3],16),int(sys.argv[4],16),sys.argv[5])
