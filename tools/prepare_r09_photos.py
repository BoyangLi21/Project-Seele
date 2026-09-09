"""R09 acceptance views with visible-section readiness guards."""
import argparse,json,msvcrt
import prepare_r08_photos as m
OUT=m.ROOT/'artifacts/world_refinement_r09'
def main(overview_only=False):
    m.photos=[]
    specs=[
        ('final_pyramid_logo',[150.5,-418,527.5],[30,-405,327],480,[[30,-304,334],[30,-375,384],[137,-458,433],[-76,-458,439]]),
        ('final_external_glass',[70.5,-323,327.5],[40,-324,327.5],320,[[53,-327,327]]),
        ('final_glass_corner',[64.5,-308,348.5],[45,-321,340],320,[[47,-319,344]]),
        ('final_inside_view',[47.5,-329,316.5],[130.5,-315,273.5],500,[[126,-316,275]]),
        ('final_dogma_gallery',[64.5,-560,310.5],[74,-568,271],340,[[72,-567,280]]),
        ('final_dogma_lilith',[30.5,-566,300.5],[30.5,-568,355.5],340,[[30,-563,360]])]
    for name,pos,target,warmup,required in specs:
        m.shot(name,pos,target,warmup);m.photos[-1]['file']=m.photos[-1]['file'].replace('r08_','r09_');m.photos[-1]['requiredSections']=required
    with (m.WORLD/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        (OUT/'final_photo_views.json').write_text(json.dumps(m.photos,indent=2),encoding='utf8')
        if overview_only:
            warmup=dict(m.photos[1]);warmup['file']='r09_overview_warmup.png';warmup['warmupTicks']=500
            selected=[warmup,m.photos[0]]
        else:selected=m.photos
        (m.WORLD/'r07_photo_views.json').write_text(json.dumps(selected,indent=2),encoding='utf8')
    print('Prepared',len(selected),'guarded native views')
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--overview-only',action='store_true');main(ap.parse_args().overview_only)
