"""Local derivative of the pinned LCL-compatible shader for surveyed facilities."""
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/combat_facility_r38/shaders'
def main():
    source=ROOT/'run/shaderpacks/ComplementaryUnbound_r5.3_SEELE_LCL.zip';OUT.mkdir(parents=True,exist_ok=True)
    target=OUT/'ComplementaryUnbound_r5.3_SEELE_R38.zip';name='shaders/lib/lighting/mainLighting.glsl'
    with zipfile.ZipFile(source) as src,zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as dst:
        for info in src.infolist():
            data=src.read(info.filename)
            if info.filename==name:
                text=data.decode();anchor='    minLighting += nightVision * vec3(0.5, 0.5, 0.75);'
                if text.count(anchor)!=1:raise ValueError('Pinned lighting source changed')
                addition='''    // SEELE R38: indirect fill for the authored underground facility volumes.
    // Actual lamps and the command-room lever still control direct lighting.
    vec3 seeleWorld = playerPos + cameraPosition;
    vec3 seelePyramid = min(seeleWorld - vec3(-100.0, -480.0, 175.0),
        vec3(175.0, -315.0, 430.0) - seeleWorld);
    vec3 seeleTransfer = min(seeleWorld - vec3(-40.0, -455.0, -300.0),
        vec3(122.0, -350.0, -15.0) - seeleWorld);
    float seeleFill = max(smoothstep(-6.0, 4.0, min(seelePyramid.x, min(seelePyramid.y, seelePyramid.z))),
        smoothstep(-6.0, 4.0, min(seeleTransfer.x, min(seeleTransfer.y, seeleTransfer.z))));
    minLighting = max(minLighting, vec3(0.18, 0.20, 0.23) * seeleFill * (1.0 - lightmapYM));
    blockLighting *= mix(vec3(1.0), vec3(1.10, 1.25, 1.40), seeleFill);
'''
                data=text.replace(anchor,addition+'\n'+anchor).encode()
            dst.writestr(info,data)
    settings=ROOT/'run/shaderpacks/ComplementaryUnbound_r5.3_SEELE_LCL.zip.txt'
    if settings.exists():target.with_name(target.name+'.txt').write_bytes(settings.read_bytes())
    record=dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),output=str(target),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),scope='Pyramid and hangar-transfer facility volumes only; LCL patch retained; command lever direct lighting retained')
    (OUT/'manifest.json').write_text(json.dumps(record,indent=2));print(target)
if __name__=='__main__':main()
