"""Audit actual post-skin draw vertices. Run with Blender's Python and -- batch_path."""
from pathlib import Path
import gzip
import json
import sys

import numpy as np
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'run/resourcepacks/eva_real_model/assets/projectseele'


def tree(vertices):
    return BVHTree.FromPolygons(vertices.tolist(),
                               np.arange(len(vertices)).reshape(-1, 3).tolist(),
                               all_triangles=True)


def seam_pairs(variant):
    mesh = json.loads((PACK / f'mesh/eva_unit0{variant}.mesh.json').read_text(encoding='utf-8'))
    pairs = {}
    for side in ('l', 'r'):
        a, b = (mesh['parts'][name + side] for name in ('arm_', 'forearm_'))
        x = np.array(a['vertices']).reshape(-1, mesh['stride'])[:, :3] + a['pivot']
        y = np.array(b['vertices']).reshape(-1, mesh['stride'])[:, :3] + b['pivot']
        matches = []
        for i, point in enumerate(x):
            distance = np.linalg.norm(y - point, axis=1)
            j = int(np.argmin(distance))
            if distance[j] < .0001:
                matches.append((i, j))
        if not matches:
            raise ValueError(f'No anatomical seam for Unit-{variant}, {side}')
        pairs[side] = matches
    return pairs


def audit(batch):
    seams = {v: seam_pairs(v) for v in range(3)}
    poses = [json.loads(line) for line in (batch / 'poses.jsonl').read_text(encoding='utf-8').splitlines()]
    contact = np.array(json.loads((ROOT / 'src/main/resources/assets/projectseele/motion/eva_heavy_contact_r05.json').read_text())['points_blocks'])
    model = json.loads((PACK / 'mesh/eva_unit01.mesh.json').read_text(encoding='utf-8'))
    hand = model['parts']['hand_r']
    hand_rest = (np.array(hand['vertices']).reshape(-1, 8)[:, :3] + hand['pivot']) * [-1/16, 1/16, 1/16]
    rig = json.loads((PACK / 'geo/eva_unit01.geo.json').read_text(encoding='utf-8'))['minecraft:geometry'][0]['bones']
    knuckle = np.array(next(b['pivot'] for b in rig if b['name'] == 'finger_middle_r')) * [-1/16, 1/16, 1/16]
    frames = []
    for file in sorted((batch / 'geometry').glob('*.json.gz')):
        with gzip.open(file, 'rt', encoding='utf-8') as stream:
            capture = json.load(stream)
        variant = capture.get('variant', 1)
        parts = {k: np.array(v).reshape(-1, 3) for k, v in capture['parts'].items()}
        row = dict(tick=capture['tick'], variant=variant, seams={}, gun_body={})
        pose = min(poses, key=lambda p: abs(p['tick']-capture['tick']))
        if variant == 1 and pose.get('heavyActive') and .3 <= pose.get('heavyPhase', 0) <= .9:
            # Fit the rigid palm transform from vertices submitted by the renderer.
            # Compare its anatomical knuckle with the separate gameplay curve.
            transform = np.linalg.lstsq(np.c_[hand_rest, np.ones(len(hand_rest))], parts['hand_r'], rcond=None)[0]
            actual = np.r_[knuckle, 1] @ transform
            phase = pose['heavyPhase']*(len(contact)-1)
            a = int(phase)
            point = contact[a]*(1-phase+a) + contact[min(a+1, len(contact)-1)]*(phase-a)
            yaw = np.radians(pose['yaw'])
            world = np.array([point[0]*np.cos(yaw)-point[2]*np.sin(yaw), point[1],
                              point[0]*np.sin(yaw)+point[2]*np.cos(yaw)])
            expected = world + np.array(pose['renderPosition'])
            row['heavy_contact_error'] = float(np.linalg.norm(actual-expected))
        for side, pairs in seams[variant].items():
            a, b = parts['arm_' + side], parts['forearm_' + side]
            row['seams'][side] = float(max(np.linalg.norm(a[i] - b[j]) for i, j in pairs))
        if 'floor' in capture:
            row['support_above_floor'] = float(min(parts[n][:, 1].min() for n in
                ('foot_l', 'foot_r', 'torso_lower', 'torso_upper')) - capture['floor'])
        if 'rifle' in parts:
            rifle = tree(parts['rifle'])
            # Fingers intentionally touch the grip; arms, head and torso must clear it.
            for name in ('head', 'torso_upper', 'torso_lower', 'arm_l',
                         'forearm_l', 'arm_r', 'forearm_r'):
                row['gun_body'][name] = len(rifle.overlap(tree(parts[name])))
            if 'floor' in capture:
                row['rifle_above_floor'] = float(parts['rifle'][:, 1].min() - capture['floor'])
        frames.append(row)
    if not frames:
        raise ValueError('No native geometry captures')
    report = dict(batch=str(batch), frames=frames, pose_frames=len(poses),
                  maximum_seam_gap=max(max(f['seams'].values()) for f in frames),
                  gun_intersection_frames=[f['tick'] for f in frames if any(f['gun_body'].values())],
                  maximum_heavy_contact_error=max((f.get('heavy_contact_error', 0) for f in frames), default=0),
                  maximum_witness={name: max(p.get(name, 0) for p in poses) for name in
                      ('muzzleError', 'rightHandError', 'leftHandError')})
    target = ROOT / 'artifacts/motion_review_r05' / f'geometry_audit_{batch.name}.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'frames'}, indent=2))
    print('Report:', target)
    return report


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    audit(Path(args[0]).resolve())
