#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, io, json, math, sys, tempfile, zipfile
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from eva_runtime_kinematics import Rig
from surface_distance import TriangleSurfaceIndex
import make_tiger_unit01_pack as tiger

P = "animation.eva_unit01."
UNITS = ("00", "01", "02")
LIMB_BONES = {f"{name}_{side}" for side in "lr" for name in ("arm", "forearm", "hand")}
R03_LOCOMOTION = (
    "idle", "walk", "run", "crouch", "crouch_walk", "takeoff", "jump", "fall", "land",
    "prone", "crawl", "prone_aim", "prone_rifle_aim", "prone_rifle_fire", "prone_cannon_fire"
)
LONGINUS_NEW_TIMES = [0.0, .09, .12, .165, .18, .34, .52, .72, .96]
LONGINUS_OLD_TIMES = [0.0, .08, .106667, .146667, .16, .30, .42, .56, .72]
JAVA_EXPECTED = {
    "EvaUnit01Entity.java": "19f050bdfcdf8dfb03c1072874caacb265078c139eb5d0563d7f8484688b4ea6",
    "EvaUnit01Renderer.java": "2d40881489f3aa8b85dd2e9b688a6e453ed9c5bc7d5e43be7b3f00f51468c97b",
}

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def semantic_sha(obj) -> str:
    return sha256_bytes(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode())

def angle(a, b, c):
    u = np.asarray(a)-np.asarray(b); v = np.asarray(c)-np.asarray(b)
    return math.degrees(math.acos(float(np.clip(np.dot(u,v)/(np.linalg.norm(u)*np.linalg.norm(v)), -1, 1))))

def load_external_mesh(path: Path) -> np.ndarray:
    d = json.loads(path.read_text())
    out=[]
    for p in d["parts"].values():
        a=np.asarray(p["vertices"],float).reshape(-1,d["stride"])
        xyz=a[:,:3]+np.asarray(p["pivot"],float); xyz[:,0]*=-1
        out.append(xyz)
    return np.concatenate(out)

def transform_points(M, xyz):
    return (M @ np.column_stack((xyz,np.ones(len(xyz)))).T).T[:,:3]

def hand_points(parts, side):
    names=["hand_"+side]+[n for n in parts if n.startswith("finger_") and n.endswith("_"+side)]
    return np.concatenate([parts[n] for n in names])

def point_surface_min(points, triangle_vertices):
    idx=TriangleSurfaceIndex(np.asarray(triangle_vertices).reshape(-1,3,3))
    return float(idx.query(np.asarray(points),k=48)[0].min())

def mesh_surface_clearance(a,b):
    # Symmetric point-to-triangle gate. It is deterministic and catches the reported chest embedding.
    return min(point_surface_min(a,b), point_surface_min(b,a))

def has_limb_position(anim):
    bad=[]
    for b,channels in anim.get("bones",{}).items():
        if b in LIMB_BONES and "position" in channels:
            bad.append(b)
    return bad

def read_source_obj(outer_path: Path):
    with zipfile.ZipFile(outer_path) as outer:
        inner_name=next(n for n in outer.namelist() if n.lower().endswith(".zip"))
        with zipfile.ZipFile(io.BytesIO(outer.read(inner_name))) as inner:
            obj_name=next(n for n in inner.namelist() if n.lower().endswith(".obj"))
            return inner.read(obj_name).decode("utf-8",errors="ignore"), obj_name

def base_metrics(rig, name, t):
    ch=rig.sample_animation(P+name,t); parts,_=rig.posed_parts(ch); j=rig.joint_world(ch)
    return {
        "min_y":float(min(v[:,1].min() for v in parts.values())),
        "foot_l_min":float(parts["foot_l"][:,1].min()),
        "foot_r_min":float(parts["foot_r"][:,1].min()),
        "knee_l_deg":angle(j["leg_l"],j["shin_l"],j["foot_l"]),
        "knee_r_deg":angle(j["leg_r"],j["shin_r"],j["foot_r"]),
        "torso_lower_min":float(parts["torso_lower"][:,1].min()),
        "torso_upper_min":float(parts["torso_upper"][:,1].min()),
        "forearm_l_min":float(parts["forearm_l"][:,1].min()),
        "forearm_r_min":float(parts["forearm_r"][:,1].min()),
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,default=ROOT)
    ap.add_argument("--out",type=Path,default=ROOT/"reports/eva_r04_contract_report.json")
    args=ap.parse_args(); root=args.root
    failures=[]; warnings=[]; report={}

    # Three-unit catalogue and bind contract.
    rigs={}; units={}
    for u in UNITS:
        rig=Rig(root/f"runtime/geo/eva_unit{u}.geo.json",root/f"runtime/mesh/eva_unit{u}.mesh.json",root/f"runtime/animations/eva_unit{u}.animation.json")
        rigs[u]=rig
        units[u]={"animation_count":len(rig.animations),"semantic_sha256":semantic_sha(rig.animations),"file_sha256":sha256_bytes((root/f"runtime/animations/eva_unit{u}.animation.json").read_bytes())}
        if len(rig.animations)!=76: failures.append(f"EVA-{u}: expected 76 animations")
        # Pivot and chain checks.
        mesh=json.loads((root/f"runtime/mesh/eva_unit{u}.mesh.json").read_text())
        max_pivot=0.0
        for name,p in mesh["parts"].items():
            if name in rig.bones:
                max_pivot=max(max_pivot,float(np.max(np.abs(np.asarray(p["pivot"])-rig.bones[name].pivot_json))))
        units[u]["mesh_geo_pivot_max_px"]=max_pivot
        if max_pivot>1e-4: failures.append(f"EVA-{u}: mesh/geo pivot mismatch {max_pivot}")
        for side in "lr":
            for digit in ("thumb","index","middle","ring","little"):
                axis=f"finger_{digit}_axis_{side}"; mcp=f"finger_{digit}_{side}"; pip=f"finger_{digit}_tip_{side}"; dip=f"finger_{digit}_distal_{side}"
                expected={axis:"hand_"+side,mcp:axis,pip:mcp,dip:pip}
                for bone,parent in expected.items():
                    if bone not in rig.bones or rig.bones[bone].parent!=parent:
                        failures.append(f"EVA-{u}: bad finger chain {bone}->{parent}")
                if axis in rig.bones and mcp in rig.bones:
                    err=float(np.linalg.norm(rig.bones[axis].pivot_json-rig.bones[mcp].pivot_json))
                    if err>1e-5: failures.append(f"EVA-{u}: axis/MCP pivot gap {digit}_{side}={err}")
    if len({x["semantic_sha256"] for x in units.values()})!=1:
        failures.append("three EVA animation semantics differ")
    report["units"]=units
    rig=rigs["01"]

    # R03 locomotion must remain byte-semantically unchanged per clip, then re-run visible posture gates.
    baseline=json.loads((root/"baseline_r03/animations/eva_unit01.animation.json").read_text())["animations"]
    unchanged={}
    for n in R03_LOCOMOTION:
        key=P+n
        same=baseline[key]==rig.animations[key]
        unchanged[n]=same
        if not same: failures.append(f"R04 unexpectedly changed reviewed R03 locomotion clip: {n}")
    loco={
        "run_left_contact":base_metrics(rig,"run",0),
        "run_flight":base_metrics(rig,"run",.18),
        "run_right_contact":base_metrics(rig,"run",.31),
        "takeoff_load":base_metrics(rig,"takeoff",.08),
        "takeoff_extension":base_metrics(rig,"takeoff",.28),
        "landing_absorption":base_metrics(rig,"land",.20),
        "crouch":base_metrics(rig,"crouch",0),
        "crouch_walk":base_metrics(rig,"crouch_walk",.5),
        "prone":base_metrics(rig,"prone",0),
        "crawl":base_metrics(rig,"crawl",.7),
    }
    if abs(loco["run_left_contact"]["foot_l_min"])>.25 or loco["run_left_contact"]["foot_r_min"]<20: failures.append("run left-contact gate")
    if min(loco["run_flight"]["foot_l_min"],loco["run_flight"]["foot_r_min"])<2.5: failures.append("run flight gate")
    if abs(loco["run_right_contact"]["foot_r_min"])>.25 or loco["run_right_contact"]["foot_l_min"]<20: failures.append("run right-contact gate")
    if max(abs(loco["takeoff_load"]["foot_l_min"]),abs(loco["takeoff_load"]["foot_r_min"]))>.25: failures.append("takeoff loaded-feet gate")
    if min(loco["takeoff_extension"]["foot_l_min"],loco["takeoff_extension"]["foot_r_min"])<3.5: failures.append("takeoff flight-clearance gate")
    if min(loco["takeoff_extension"]["knee_l_deg"],loco["takeoff_extension"]["knee_r_deg"])<160: failures.append("takeoff extension gate")
    if loco["prone"]["torso_lower_min"]>6 or loco["prone"]["torso_upper_min"]>12: failures.append("prone body-height gate")
    if not all(0<=loco["prone"][k]<=6 for k in ("forearm_l_min","forearm_r_min")): failures.append("prone forearm-support gate")
    report["locomotion"]={"unchanged_from_R03":unchanged,"metrics":loco}

    # Actual weapon geometry.
    lance_xyz=load_external_mesh(root/"runtime/mesh/longinus_lance.mesh.json")
    knife_xyz=load_external_mesh(root/"runtime/mesh/progressive_knife.mesh.json")
    r03_rig=Rig(root/"runtime/geo/eva_unit01.geo.json",root/"runtime/mesh/eva_unit01.mesh.json",root/"baseline_r03/animations/eva_unit01.animation.json")

    # Longinus: preserve weapon world path, remove hand translations, maintain both contacts and clear chest.
    longi={"keyframes":[]}
    for n in ("lance_carry","lance_ready","lance_thrust"):
        bad=has_limb_position(rig.animations[P+n])
        if bad: failures.append(f"{n}: articulated limb position channels present: {bad}")
    weapon_path_err=0.0; min_hand={"l":1e9,"r":1e9}; min_forearm=1e9; elbow_min=180; elbow_max=0
    for nt,ot in zip(LONGINUS_NEW_TIMES,LONGINUS_OLD_TIMES):
        ch=rig.sample_animation(P+"lance_thrust",nt); mats=rig.matrices(ch); parts,_=rig.posed_parts(ch); j=rig.joint_world(ch)
        oldM=r03_rig.matrices(r03_rig.sample_animation(P+"lance_thrust",ot))["lance"]
        err=float(np.max(np.abs(mats["lance"]-oldM))); weapon_path_err=max(weapon_path_err,err)
        W=transform_points(mats["lance"],lance_xyz)
        contacts={}
        for side in "lr":
            d=point_surface_min(hand_points(parts,side),W); contacts[side]=d; min_hand[side]=min(min_hand[side],d)
            e=angle(j["arm_"+side],j["forearm_"+side],j["hand_"+side]); elbow_min=min(elbow_min,e);elbow_max=max(elbow_max,e)
        torso=np.concatenate([parts["torso_lower"],parts["torso_upper"]])
        clear=min(mesh_surface_clearance(parts["forearm_l"],torso),mesh_surface_clearance(parts["forearm_r"],torso))
        min_forearm=min(min_forearm,clear)
        longi["keyframes"].append({"new_time":nt,"source_time":ot,"weapon_world_matrix_error":err,"hand_surface_distance_px":contacts,"forearm_torso_clearance_px":clear})
    # Sample interpolated motion with a cheap vertex gate, so bad Euler arcs cannot hide between keys.
    interp_min=1e9; interp_t=None
    for t in np.linspace(0,.96,97):
        parts,_=rig.posed_parts(rig.sample_animation(P+"lance_thrust",float(t)))
        torso=np.concatenate([parts["torso_lower"],parts["torso_upper"]]); tree=cKDTree(torso)
        d=min(float(tree.query(parts["forearm_l"])[0].min()),float(tree.query(parts["forearm_r"])[0].min()))
        if d<interp_min:interp_min=d;interp_t=float(t)
    longi.update({"weapon_world_path_max_error":weapon_path_err,"minimum_hand_surface_distance_px":min_hand,
                  "minimum_exact_keyframe_forearm_torso_clearance_px":min_forearm,
                  "minimum_interpolated_vertex_clearance_px":interp_min,"minimum_interpolated_time":interp_t,
                  "elbow_angle_range_deg":[elbow_min,elbow_max]})
    if weapon_path_err>2e-5: failures.append(f"Longinus weapon path changed: {weapon_path_err}")
    if max(min_hand.values())>.05: failures.append(f"Longinus hand contact gate: {min_hand}")
    if min_forearm<2.0 or interp_min<2.0: failures.append(f"Longinus arm/chest clearance gate: exact={min_forearm}, interpolated={interp_min}")
    if elbow_min<45 or elbow_max>165: failures.append(f"Longinus elbow range gate: {elbow_min}..{elbow_max}")
    # Crouch/prone Longinus are re-solved on their real stance ancestors; no hand translation shortcut.
    stance_longinus={}
    for n in ("crouch_lance_thrust","prone_lance_thrust"):
        bad=has_limb_position(rig.animations[P+n])
        if bad: failures.append(f"{n}: articulated limb position channels present: {bad}")
        ch=rig.sample_animation(P+n,.52); mats=rig.matrices(ch); parts,_=rig.posed_parts(ch)
        W=transform_points(mats["lance"],lance_xyz)
        contacts={side:point_surface_min(hand_points(parts,side),W) for side in "lr"}
        stance_longinus[n]={"time":.52,"hand_surface_distance_px":contacts,
                            "minimum_body_y":float(min(v[:,1].min() for v in parts.values()))}
        if max(contacts.values())>.05: failures.append(f"{n}: two-hand contact gate {contacts}")
    longi["stance_variants"]=stance_longinus
    report["longinus"]=longi

    # Knife right-click: same reverse grip, long six-phase cross-body horizontal path.
    knife={"keyframes":[]}
    ka=rig.animations[P+"knife_heavy"]
    if float(ka.get("animation_length",0))<1.25: failures.append("knife_heavy duration gate")
    bad=has_limb_position(ka)
    if bad: failures.append(f"knife_heavy articulated limb position channels: {bad}")
    local_ref=None; local_err=0.0; centres=[]; right_contact=1e9
    for t in [0,.28,.50,.70,.92,1.30]:
        ch=rig.sample_animation(P+"knife_heavy",t); mats=rig.matrices(ch); parts,_=rig.posed_parts(ch)
        local=np.linalg.inv(mats["hand_r"])@mats["knife"]
        if local_ref is None: local_ref=local
        local_err=max(local_err,float(np.max(np.abs(local-local_ref))))
        W=transform_points(mats["knife"],knife_xyz); centre=W.mean(0);centres.append(centre)
        d=point_surface_min(hand_points(parts,"r"),W);right_contact=min(right_contact,d)
        knife["keyframes"].append({"time":t,"weapon_centroid":centre.tolist(),"right_hand_surface_distance_px":d})
    knife.update({"reverse_grip_local_matrix_max_error":local_err,"minimum_right_hand_surface_distance_px":right_contact,
                  "slash_delta_x_windup_to_contact":float(centres[3][0]-centres[1][0]),
                  "slash_delta_z_windup_to_contact":float(centres[3][2]-centres[1][2])})
    if local_err>2e-5: failures.append(f"knife reverse-grip attachment drift: {local_err}")
    if right_contact>.05: failures.append(f"knife hand-contact gate: {right_contact}")
    if centres[3][0]-centres[1][0]>-20: failures.append("knife horizontal cross-body X-travel gate")
    if centres[3][2]-centres[1][2]>-20: failures.append("knife forward contact Z-travel gate")
    # Crouch heavy uses the same six-phase grip through the crouch ancestor.
    ck=rig.sample_animation(P+"crouch_knife_heavy",.70); ckm=rig.matrices(ck); ckp,_=rig.posed_parts(ck)
    ckw=transform_points(ckm["knife"],knife_xyz); ckdist=point_surface_min(hand_points(ckp,"r"),ckw)
    knife["crouch_contact_surface_distance_px"]=ckdist
    if has_limb_position(rig.animations[P+"crouch_knife_heavy"]): failures.append("crouch_knife_heavy limb position gate")
    if ckdist>.05: failures.append(f"crouch_knife_heavy contact gate: {ckdist}")
    report["knife_heavy"]=knife

    # Barehand handedness and single-arm heavy.
    bare={}
    for name,t,active in (("melee",.36,"r"),("melee_left",.38,"l"),("smash",.68,"r")):
        anim=rig.animations[P+name]
        bad=has_limb_position(anim)
        if bad: failures.append(f"{name}: limb position channels: {bad}")
        ch=rig.sample_animation(P+name,t); j=rig.joint_world(ch)
        active_z=float(j["hand_"+active][2]); other="l" if active=="r" else "r"; other_z=float(j["hand_"+other][2])
        ea=angle(j["arm_"+active],j["forearm_"+active],j["hand_"+active])
        eo=angle(j["arm_"+other],j["forearm_"+other],j["hand_"+other])
        bare[name]={"time":t,"active_side":active,"active_hand_z":active_z,"guard_hand_z":other_z,"active_elbow_deg":ea,"guard_elbow_deg":eo}
        if active_z>=other_z-8: failures.append(f"{name}: active hand does not lead guard hand")
    # The heavy must not be a mirrored two-arm golem strike.
    sm=rig.sample_animation(P+"smash",.68)
    ar=np.asarray(sm.get("arm_r",{}).get("rotation",[0,0,0])); al=np.asarray(sm.get("arm_l",{}).get("rotation",[0,0,0]))
    bare["smash_arm_rotation_difference_norm"]=float(np.linalg.norm(ar-al))
    if np.linalg.norm(ar-al)<25: failures.append("smash bilateral-symmetry/golem gate")
    report["barehand"]=bare

    # Native thumb vs clean-room chain, using the actual OBJ inside each nested source archive.
    thumbs={}
    for u in UNITS:
        obj_text,obj_name=read_source_obj(root/f"source_archives/evangelion-unit-{u}.zip")
        positions,texcoords,normals,triangles=tiger.parse_obj(obj_text)
        face_bones,finger_pivots,finger_frames=tiger.discover_finger_rig(positions,triangles)
        native={s:sum(1 for owner in face_bones.values() if owner==f"finger_thumb_{s}") for s in "lr"}
        runtime_mesh=json.loads((root/f"runtime/mesh/eva_unit{u}.mesh.json").read_text())
        pivots={n:p["pivot"] for n,p in runtime_mesh["parts"].items()}
        minimum_y=min(p[1] for p in positions); height=max(p[1] for p in positions)-minimum_y; scale=tiger.MODEL_HEIGHT/height
        rebuilt,counts=tiger.build_mesh(positions,texcoords,normals,triangles,pivots,scale,minimum_y,face_bones)
        runtime_counts={s:{n:int(len(runtime_mesh["parts"][n]["vertices"])//runtime_mesh["stride"]//3) for n in (f"finger_thumb_{s}",f"finger_thumb_tip_{s}",f"finger_thumb_distal_{s}")} for s in "lr"}
        thumbs[u]={"obj":obj_name,"native_thumb_source_faces":native,"rebuilt_generated_triangle_counts":{s:{n:counts[n] for n in (f"finger_thumb_{s}",f"finger_thumb_tip_{s}",f"finger_thumb_distal_{s}")} for s in "lr"},"runtime_triangle_counts":runtime_counts}
        for s in "lr":
            if native[s]<=0: failures.append(f"EVA-{u}: no native thumb source faces found")
            if any(v!=92 for v in runtime_counts[s].values()): failures.append(f"EVA-{u}: runtime thumb duplicate/missing segment {s}: {runtime_counts[s]}")
    report["thumb_exclusivity"]=thumbs

    # Java is reference-only and must remain byte-identical to input.
    java={}
    for name,expected in JAVA_EXPECTED.items():
        p=root/"java_reference"/name; actual=sha256_bytes(p.read_bytes());java[name]={"sha256":actual,"unchanged":actual==expected}
        if actual!=expected: failures.append(f"Java file changed unexpectedly: {name}")
    entity=(root/"java_reference/EvaUnit01Entity.java").read_text(errors="ignore")
    for token in ("melee_left","knife_heavy","lance_thrust","crouch_knife_heavy","prone_knife_heavy"):
        if token not in entity: failures.append(f"Java animation mapping missing: {token}")
    report["java_reference"]=java

    report["target_animation_semantic_sha256"]=next(iter(units.values()))["semantic_sha256"]
    report["passed"]=not failures; report["failure_count"]=len(failures);report["failures"]=failures;report["warnings"]=warnings
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"passed":report["passed"],"failure_count":len(failures),"out":str(args.out)},ensure_ascii=False,indent=2))
    if failures:
        for f in failures: print("FAIL:",f,file=sys.stderr)
    raise SystemExit(0 if not failures else 1)

if __name__=="__main__": main()
