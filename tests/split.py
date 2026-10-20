import sys
from PIL import Image
src=sys.argv[1]; step=int(sys.argv[2]) if len(sys.argv)>2 else 1600; scale=float(sys.argv[3]) if len(sys.argv)>3 else .5
im=Image.open(src); W,H=im.size; n=0
for top in range(0,H,step):
    c=im.crop((0,top,W,min(H,top+step))); c=c.resize((int(W*scale), int((min(H,top+step)-top)*scale)))
    c.save(src.replace('.png',f'-p{n}.png')); n+=1
print(W,H,n)
