"""Keep pinned 5.3/LCL behavior; make indirect interior light survive material AO."""
from pathlib import Path
import hashlib,json,zipfile,shutil
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/transport_return_r39/shaders'

def main():
    source=ROOT/'run/shaderpacks/ComplementaryUnbound_r5.3_SEELE_R38.zip'
    OUT.mkdir(parents=True,exist_ok=True)
    target=OUT/'ComplementaryUnbound_r5.3_SEELE_R39.zip'
    with zipfile.ZipFile(source) as src,zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as dst:
        for info in src.infolist():
            data=src.read(info.filename)
            if info.filename=='shaders/lib/lighting/mainLighting.glsl':
                s=data.decode()
                s='#define SEELE_INTERIOR_LIGHT 140 // [80 100 120 140 160 180]\nuniform int seeleCommandLights;\n'+s
                anchor='    finalDiffuse = sqrt(max(finalDiffuse, vec3(0.0)));'
                assert s.count(anchor)==1
                addition='''    // R39: broad reflected light belongs after the material/AO calculation.
    // Local lamp light, shadows and the command-room switches remain independent.
    float seeleInterior = max(seeleFill, (1.0 - smoothstep(0.04, 0.45, lightmap.y)) * 0.65);
    float seeleBounce = (0.54 + 0.24 * lightmap.x) * (SEELE_INTERIOR_LIGHT * 0.01);
    vec3 seeleRoom = min(seeleWorld - vec3(-6.0, -460.0, 269.0), vec3(66.0, -379.0, 374.0) - seeleWorld);
    float seeleRoomMask = smoothstep(-3.0, 3.0, min(seeleRoom.x, min(seeleRoom.y, seeleRoom.z)));
    seeleBounce *= mix(1.0, mix(0.08, 1.0, float(seeleCommandLights)), seeleRoomMask);
    float seeleOcclusion = mix(0.72, 1.0, clamp(vanillaAO, 0.0, 1.0));
    finalDiffuse += vec3(0.86, 0.93, 1.0) * seeleInterior * seeleBounce * seeleOcclusion;
'''
                data=s.replace(anchor,addition+anchor).encode()
            if info.filename=='shaders/shaders.properties':
                s=data.decode();s=s.replace('screen=','screen=SEELE_INTERIOR_LIGHT ',1)
                s=s.replace('sliders=','sliders=SEELE_INTERIOR_LIGHT ',1);data=s.encode()
            if info.filename=='shaders/lang/en_US.lang':
                data+=b'\noption.SEELE_INTERIOR_LIGHT=SEELE Interior Light\noption.SEELE_INTERIOR_LIGHT.comment=Indirect interior fill. Local lamps and switches remain active.\n'
            if info.filename=='shaders/lang/zh_CN.lang':
                data+='\noption.SEELE_INTERIOR_LIGHT=SEELE 室内补光\noption.SEELE_INTERIOR_LIGHT.comment=室内间接光强度；保留灯具、开关与阴影。\n'.encode()
            dst.writestr(info,data)
        if "shaders/lang/zh_CN.lang" not in src.namelist():
            dst.writestr("shaders/lang/zh_CN.lang","option.SEELE_INTERIOR_LIGHT=SEELE 室内补光\noption.SEELE_INTERIOR_LIGHT.comment=室内间接光强度；保留灯具、开关与阴影。\n".encode())
    settings=source.with_name(source.name+'.txt').read_text(encoding='utf8')
    settings+='\nSEELE_INTERIOR_LIGHT=140\n'
    target.with_name(target.name+'.txt').write_text(settings,encoding='utf8')
    record=dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),output=str(target),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),default_fill=140)
    (OUT/'manifest.json').write_text(json.dumps(record,indent=2),encoding='utf8')
    for p in (target,target.with_name(target.name+'.txt')):shutil.copy2(p,ROOT/'run/shaderpacks'/p.name)
    print(target)
if __name__=='__main__':main()
