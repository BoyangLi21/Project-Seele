"""Acquire user-authorized private test inputs from their visible public download links.

These official-game extractions are never copied into public mod resources.
"""
import concurrent.futures,hashlib,json,re,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'external-assets/incoming/angels_r10'
BASE='https://models.spriters-resource.com'
PAGES={name:BASE+'/playstation_2/neongenesisevangelionbattleorchestra/asset/'+str(number)+'/' for name,number in [
    ('bardiel',545638),('gaghiel',545659),('israfel',550089),('leliel',545663),('ramiel',545665),
    ('sachiel',545666),('sahaquiel',545667),('shamshel',545668),('zeruel',545669)]}
def get(url,referer):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':referer})
    with urllib.request.urlopen(req,timeout=50) as r:return r.read()
def fetch(item):
    name,page=item;html=get(page,BASE+'/playstation_2/neongenesisevangelionbattleorchestra/').decode('utf8')
    from html import unescape
    links=[unescape(x) for x in re.findall(r'href=["\']([^"\']+)["\']',html) if '/media/assets/' in x and '.zip' in x]
    assert len(set(links))==1,(name,links)
    url=BASE+links[0] if links[0].startswith('/') else links[0];data=get(url,page);assert data[:2]==b'PK'
    path=OUT/(name+'_battle_orchestra.zip');path.write_bytes(data)
    with zipfile.ZipFile(path) as z:
        entries=[dict(path=x.filename,size=x.file_size) for x in z.infolist()]
        for x in z.infolist():
            dest=(OUT/name/x.filename).resolve();assert dest.is_relative_to((OUT/name).resolve())
            if x.is_dir():continue
            assert dest.suffix.lower() in ('.obj','.mtl','.png','.jpg','.jpeg','.bmp','.tga','.txt','.dae','.fbx'),dest
            dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(x))
    return dict(name=name,page=page,download=url,archive=str(path),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
                source_game='Neon Genesis Evangelion: Battle Orchestra (PS2)',redistribution='Not granted; local evaluation only',entries=entries)
def main():
    OUT.mkdir(exist_ok=True);results=[];failures=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        tasks={pool.submit(fetch,item):item[0] for item in PAGES.items()}
        for f in concurrent.futures.as_completed(tasks):
            try:r=f.result();results.append(r);print('DOWNLOADED',r['name'],r['bytes'],flush=True)
            except Exception as e:failures.append(dict(name=tasks[f],error=str(e)));print('FAILED',tasks[f],str(e),flush=True)
    (OUT/'manifest.json').write_text(json.dumps(dict(assets=sorted(results,key=lambda r:r['name']),failures=failures),indent=2),encoding='utf8')
    assert not failures,failures
if __name__=='__main__':main()
