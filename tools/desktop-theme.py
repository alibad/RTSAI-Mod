"""Generate simple native panel geometry. Original UI pixels; no game artwork is modified."""
from pathlib import Path
import struct,zlib
ROOT=Path(__file__).resolve().parents[1]
def png(width,height,data):
 def chunk(name,data):return struct.pack('!I',len(data))+name+data+struct.pack('!I',zlib.crc32(name+data)&0xffffffff)
 raw=b''.join(b'\0'+data[y*width*4:(y+1)*width*4] for y in range(height))
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b'')
def main():
 fills=[(16,27,34,255),(27,43,53,255),(35,57,68,255),(22,38,46,255),(21,29,35,255)]
 rows=[]
 for y in range(16):
  for i in range(8):
   c=fills[min(i,len(fills)-1)]
   for x in range(16):rows.extend((47,65,77,255) if x in (0,15) or y in (0,15) else c)
 out=ROOT/'mods/rtsai/uibits/desktop-panels.png';out.write_bytes(png(128,16,bytes(rows)))
 chrome=''
 for id,i in [('desktop-scroll',0),('desktop-panel',1),('desktop-button',1),('desktop-button-hover',2),('desktop-button-pressed',3),('desktop-button-disabled',4)]:
  chrome+=f'{id}:\n\tImage: ra2|uibits/desktop-panels.png\n\tPanelRegion: {i*16}, 0, 1, 1, 14, 14, 1, 1\n\n'
 (ROOT/'mods/rtsai/desktop-theme.yaml').write_text(chrome,encoding='utf-8')
if __name__=='__main__':main()
