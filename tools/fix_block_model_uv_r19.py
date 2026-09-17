"""Keep oversized furniture quads within their own atlas sprite."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def main():
    edited=[]
    for path in (ROOT/'src/main/resources/assets/projectseele/models/block').rglob('*.json'):
        data=json.loads(path.read_text());count=0
        for element in data.get('elements',[]):
            if not any(v<0 or v>16 for k in ('from','to') for v in element.get(k,[])):continue
            for face in element.get('faces',{}).values():
                if 'uv' not in face:face['uv']=[0,0,16,16];count+=1
        if count:
            path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf8');edited.append(dict(file=str(path.relative_to(ROOT)),faces=count))
    (ROOT/'artifacts/world_repair_r19/model_uv_repair.json').write_text(json.dumps(edited,indent=2))
    print('Oversized model UV correction',edited)

if __name__=='__main__':main()
