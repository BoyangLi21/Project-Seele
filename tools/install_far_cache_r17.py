"""Install only a coherent reviewed LOD database; never migrate review terrain."""
from pathlib import Path
import argparse,datetime,hashlib,json,msvcrt,shutil,sqlite3

ROOT=Path(__file__).resolve().parents[1]
MAIN=ROOT/'run/saves/SEELE_TV_WORLD_PREVIEW_20260906'
SOURCE=ROOT/'run/saves/SEELE_FAR_REVIEW_R17'
REL=Path('dimensions/projectseele/geofront/data/DistantHorizons.sqlite')

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--review-dir',type=Path,required=True);ap.add_argument('--apply',action='store_true');a=ap.parse_args()
    measurements=json.loads((a.review_dir/'measurements.json').read_text())
    names={'city_far','geofront_pyramid','geofront_lake','command_interior','un_far'}
    assert {r['view'] for r in measurements}==names
    assert all(r['dh_loaded'] and r['embeddium_loaded'] and r['ferritecore_loaded'] for r in measurements)
    assert all((a.review_dir/(name+'.png')).is_file() for name in names)
    with (MAIN/'session.lock').open('r+b') as main_lock,(SOURCE/'session.lock').open('r+b') as source_lock:
        msvcrt.locking(main_lock.fileno(),msvcrt.LK_NBLCK,1);msvcrt.locking(source_lock.fileno(),msvcrt.LK_NBLCK,1)
        src=SOURCE/REL;wal=src.with_name(src.name+'-wal')
        assert not wal.exists() or wal.stat().st_size==0,'Source cache must be checkpointed and closed'
        with sqlite3.connect(src.resolve().as_uri()+'?mode=ro',uri=True) as db:
            assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
            rows=db.execute('select DetailLevel,count(*) from FullData group by DetailLevel').fetchall()
        receipt={'version':17,'distant_horizons':'3.2.0-b','source_world':SOURCE.name,
            'review_directory':str(a.review_dir.resolve()),'full_data_rows_by_detail':rows,
            'scope':'LOD cache only; main terrain, entities, fleet and player data are not copied from the review world',
            'databases':[{'path':REL.as_posix(),'sha256':digest(src),'bytes':src.stat().st_size}]}
        if a.apply:
            backup=ROOT/'artifacts/rendering_r17/cache_backups'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            backup.mkdir(parents=True);dst=MAIN/REL;dst.parent.mkdir(parents=True,exist_ok=True)
            for suffix in ('','-wal','-shm'):
                old=dst.with_name(dst.name+suffix)
                if old.exists():shutil.copy2(old,backup/old.name)
            marker=MAIN/'lod_cache_r17.json'
            if marker.exists():shutil.copy2(marker,backup/marker.name)
            temp=dst.with_suffix('.r17.tmp');shutil.copy2(src,temp);assert digest(temp)==receipt['databases'][0]['sha256'];temp.replace(dst)
            for suffix in ('-wal','-shm'):
                old=dst.with_name(dst.name+suffix)
                if old.exists():old.unlink()
            receipt['backup']=str(backup);marker.write_text(json.dumps(receipt,indent=2),encoding='utf8')
            (backup/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
        print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
