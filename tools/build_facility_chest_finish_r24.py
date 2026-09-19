"""Original SVG chest UV atlas; never edits inventories or copies vanilla artwork."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def main():
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 64 64">','<rect width="64" height="64" fill="#46534c"/>']
    def rect(x,y,w,h,colour):parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{colour}"/>')
    def panel(x,y,w,h,col):
        rect(x,y,w,h,'#26342d');rect(x+.25,y+.25,w-.5,h-.5,col);rect(x+.7,y+.6,w-1.4,.16,'#89968b');rect(x+.7,y+h-.8,w-1.4,.17,'#36453b')
        for xx in (x+1,x+w-1):
            for yy in (y+1,y+h-1):parts.append(f'<circle cx="{xx}" cy="{yy}" r=".20" fill="#aeb8aa"/>')
    for x,col in zip((0,14,28,42),('#526158','#5b6a60','#526158','#49584e')):
        panel(x,33,14,10,col);panel(x,14,14,5,col)
        rect(x+3,37,8,1.0,'#29382f');rect(x+3.6,37.25,6.8,.35,'#849387')
    for x in (14,28):panel(x,0,14,14,'#68766a');panel(x,19,14,14,'#4c5d50')
    rect(15,34.25,12,.35,'#c9b573')
    parts.append('<text x="21" y="36.7" text-anchor="middle" font-family="monospace" font-size="2.1" fill="#d4d6bc">NERV</text>')
    parts.append('<text x="21" y="41" text-anchor="middle" font-family="monospace" font-size="1.35" fill="#bac3b4">EQUIPMENT</text>')
    panel(0,0,6,6,'#a7afa1');rect(1,1,2,4,'#bac0b4');rect(1.55,2,.8,1.3,'#35443b')
    parts.append('</svg>');source=ROOT/'art_sources/nerv_equipment_chest_r24.svg';source.parent.mkdir(exist_ok=True);source.write_text('\n'.join(parts),encoding='utf8')
    atlas=ROOT/'src/main/resources/assets/minecraft/atlases/chests.json';atlas.parent.mkdir(parents=True,exist_ok=True)
    atlas.write_text(json.dumps({'sources':[{'type':'single','resource':'projectseele:entity/chest/nerv_equipment_r24','sprite':'projectseele:entity/chest/nerv_equipment_r24'}]},indent=2)+'\n',encoding='utf8')
    print(source)
if __name__=='__main__':main()
