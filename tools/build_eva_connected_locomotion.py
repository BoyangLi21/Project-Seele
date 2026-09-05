#!/usr/bin/env python3
"""Bake the accepted gait channels and a supported low stance into one runtime database.

The local Tiger mesh is read only to solve foot support; no mesh or texture is
copied into the output. Existing animation files are never rewritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from render_unit01_rig_preview import bone_matrix, load_skeleton, sample_channel


def read_bvh(path, first=0, last=None):
    """Read native BVH channel order; preserve its Y-up source coordinates."""
    hierarchy, motion = path.read_text(encoding='utf-8-sig').split('MOTION', 1)
    tokens = re.findall(r'[{}]|[^\s{}]+', hierarchy)
    cursor, channel_cursor, joints = 1, 0, []

    def joint(parent):
        nonlocal cursor, channel_cursor
        kind = tokens[cursor]; cursor += 1
        name = tokens[cursor]; cursor += 1
        if kind == 'End': name = joints[parent]['name'] + '_end'
        assert tokens[cursor] == '{'
        cursor += 1
        index = len(joints)
        record = {'name': name, 'parent': parent, 'offset': [0,0,0], 'channels': [], 'start': channel_cursor}
        joints.append(record)
        while tokens[cursor] != '}':
            token = tokens[cursor]
            if token == 'OFFSET':
                record['offset'] = list(map(float, tokens[cursor+1:cursor+4])); cursor += 4
            elif token == 'CHANNELS':
                n = int(tokens[cursor+1]); record['channels'] = tokens[cursor+2:cursor+2+n]
                record['start'] = channel_cursor; channel_cursor += n; cursor += n+2
            else:
                joint(index)
        cursor += 1
    joint(-1)
    lines = motion.strip().splitlines()
    dt = float(lines[1].split(':')[1])
    data = np.loadtxt(lines[2:])[first:last:2]
    matrices, points = [], {}
    for j in joints:
        local = np.tile(np.eye(4), (len(data),1,1))
        local[:,:3,3] = j['offset']
        axes, values = [], []
        for i,c in enumerate(j['channels']):
            value = data[:,j['start']+i]
            if c.endswith('position'): local[:,'XYZ'.index(c[0]),3] += value
            else: axes.append(c[0]); values.append(value)
        if axes: local[:,:3,:3] = Rotation.from_euler(''.join(axes), np.array(values).T, degrees=True).as_matrix()
        world = local if j['parent'] < 0 else matrices[j['parent']] @ local
        matrices.append(world); points[j['name']] = world[:,:3,3]
    pelvis = points['Hips']
    left = np.mean(points['LeftUpLeg'] - points['RightUpLeg'],axis=0); left[1]=0; left/=np.linalg.norm(left)
    forward = np.cross(left, [0,1,0])
    toe_name = next(n for n in ('LeftToeBase','LeftToe','LeftFoot_end') if n in points)
    toe = np.mean(points[toe_name]-points['LeftFoot'],axis=0)
    if forward @ toe < 0: forward *= -1
    relative = {n: np.stack(((p-pelvis)@forward, (p-pelvis)@left, (p-pelvis)[:,1]),axis=1)
                for n,p in points.items()}
    return relative, pelvis[:,1], dt*2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack', type=Path, default=Path('run/resourcepacks/eva_real_model/assets/projectseele'))
    parser.add_argument('--output', type=Path, default=Path('src/main/resources/assets/projectseele/motion/eva_connected_locomotion_v1.json'))
    parser.add_argument('--review', type=Path, default=Path('.Codex/action-continuity/locomotion-review.animation.json'))
    args = parser.parse_args()
    animation_path = args.pack / 'animations/eva_unit01.animation.json'
    geo_path = args.pack / 'geo/eva_unit01.geo.json'
    mesh = json.loads((args.pack / 'mesh/eva_unit01.mesh.json').read_text(encoding='utf-8'))
    animations = json.loads(animation_path.read_text(encoding='utf-8'))['animations']
    pivots, parents, bind = load_skeleton(mesh, geo_path)
    bones = sorted(set().union(*(set(animations['animation.eva_unit01.' + n]['bones'])
                               for n in ('idle', 'walk', 'run', 'crouch'))))
    bones = sorted(set(bones) | {'head', 'neck', 'torso_lower', 'ankle_l', 'ankle_r'})
    clips, review = {}, {}
    accad = Path('external-assets/incoming/mocap/accad-eva-seed-r01/third_party_normalized/source_extract/male2_bvh')
    down_path = accad / 'Male2_A7_Crouch.bvh'
    up_path = accad / 'Male2_D13_CrouchToReady.bvh'
    walk_path = Path('external-assets/incoming/mocap/eva-real-motion-shortlist-r01/136_09.bvh')
    down_source, down_height, down_dt = read_bvh(down_path, 140, 402)
    up_all, up_height, up_dt = read_bvh(up_path)
    up_progress = (up_height-up_height.min()) / np.ptp(up_height)
    up_begin = max(0, int(np.argmax(up_progress > .03))-3)
    up_end = min(len(up_height), int(np.argmax(up_progress > .98))+4)
    up_source = {n:p[up_begin:up_end] for n,p in up_all.items()}
    up_height = up_height[up_begin:up_end]
    walk_source, _, walk_dt = read_bvh(walk_path, 911, 1057)
    walking_duration = (len(walk_source['Hips'])-1)*walk_dt

    def at(values, phase):
        return np.array([np.interp(phase, np.linspace(0,1,len(values)), values[:,i])
                         for i in range(values.shape[1])])
    foot_vertices = {}
    for side in ('l', 'r'):
        name = 'foot_' + side
        values = np.asarray(mesh['parts'][name]['vertices']).reshape(-1, 8)[:, :3].copy()
        values[:, 0] *= -1
        values += np.asarray(pivots[name])
        foot_vertices[side] = np.c_[values, np.ones(len(values))]

    def matrix(name, rotations, positions):
        return np.asarray(bone_matrix(name, pivots, parents, rotations, positions, bind, {}))

    def foot_pivot(side, rotations, positions):
        return (matrix('foot_' + side, rotations, positions)
                @ np.r_[pivots['foot_' + side], 1])[:3]

    def knee_hinge(knee):
        # The Tiger shin pivot is below the visible knee socket. Translate
        # around the actual articulation without modifying the shared rig.
        offset = np.array([0., 11.4, 0.])
        delta = offset - Rotation.from_euler('x', -knee, degrees=True).apply(offset)
        delta[0] *= -1
        return delta.tolist()

    def low_pose():
        rotations = {b: sample_channel(v['rotation'], 0, b)
                     for b, v in animations['animation.eva_unit01.idle']['bones'].items()
                     if 'rotation' in v}
        rotations.update(root=(0, 0, 0), torso_lower=(22, 0, 0),
                         torso_upper=(-8, 0, 0), aim_pitch=(0, 0, 0),
                         neck=(-5, 0, 0), head=(0, 0, 0))
        for side, sign in (('l', -1), ('r', 1)):
            rotations.update({f'leg_{side}': (-94.8149676, 0, sign * 4),
                              f'shin_{side}': (135.56941281, 0, 0),
                              f'foot_{side}': (-62.75444521, 0, -sign * 4),
                              f'arm_{side}': (-12, 0, sign * 12),
                              f'forearm_{side}': (-50, 0, -sign * 4)})
        positions = {'root': [0., 0., 0.], 'shin_l': knee_hinge(135.56941281),
                     'shin_r': knee_hinge(135.56941281)}
        minimum = min((foot_vertices[s] @ matrix('foot_' + s, rotations, positions).T)[:, 1].min()
                      for s in ('l', 'r'))
        positions['root'][1] = -float(minimum)
        # Centre the support under the body instead of leaving both feet in front.
        positions['root'][2] = -float(np.mean([foot_pivot(s, rotations, positions)[2] for s in ('l', 'r')]))
        return rotations, positions

    low_rotations, low_positions = low_pose()
    foot_origins = {s: foot_pivot(s, low_rotations, low_positions) for s in ('l', 'r')}
    support_errors = []
    stance = .64
    excursion = 10.0
    source_forward = np.stack([walk_source[n][:,0] for n in ('LeftFoot','RightFoot')],axis=1)
    source_forward -= np.linspace(0,1,len(source_forward))[:,None] * (source_forward[-1]-source_forward[0])
    source_forward -= source_forward.mean(axis=0)
    forward_scale = excursion / np.ptp(source_forward,axis=0).max()
    source_lift = np.stack([walk_source[n][:,2] for n in ('LeftFoot','RightFoot')],axis=1)
    source_lift -= source_lift.min(axis=1)[:,None]
    source_lift *= 2.2 / max(1e-6, source_lift.max())

    def crouch_sample(phase, moving):
        rotations = dict(low_rotations)
        positions = {b:list(p) for b,p in low_positions.items()}
        if not moving:
            return rotations, positions, [True, True]
        midpoint = (at(walk_source['LeftFoot'],phase)+at(walk_source['RightFoot'],phase))*.5
        lateral = np.mean((walk_source['LeftFoot'][:,1]+walk_source['RightFoot'][:,1])*.5)
        positions['root'][0] += float(np.clip((midpoint[1]-lateral)*forward_scale,-1,1))
        contacts = []
        for column, side in enumerate(('l','r')):
            travel = -float(at(source_forward,phase)[column])*forward_scale
            lift = float(at(source_lift,phase)[column])
            contact = lift < .25
            contacts.append(contact)
            if contact: lift = 0
            target = foot_origins[side][[1, 2]] + [lift, travel]

            def residual(angles):
                hip, knee = angles
                rotations['leg_' + side] = (hip, 0, -4 if side == 'l' else 4)
                rotations['shin_' + side] = (knee, 0, 0)
                rotations['foot_' + side] = (-22 - hip - knee, 0, 4 if side == 'l' else -4)
                positions['shin_' + side] = knee_hinge(knee)
                return foot_pivot(side, rotations, positions)[[1, 2]] - target

            solution = least_squares(residual, [-94.815, 135.57], bounds=([-120, 95], [-50, 155]),
                                     xtol=1e-10, ftol=1e-10, gtol=1e-10)
            error = float(np.linalg.norm(residual(solution.x)))
            support_errors.append(error)
            arm_name = 'LeftArm' if side == 'l' else 'RightArm'
            elbow_name = 'LeftForeArm' if side == 'l' else 'RightForeArm'
            direction = walk_source[elbow_name]-walk_source[arm_name]
            pitch = np.degrees(np.arctan2(-direction[:,0],-direction[:,2]))
            swing = float(np.interp(phase,np.linspace(0,1,len(pitch)),pitch)-np.mean(pitch))
            rotations['arm_' + side] = (-12 + swing, 0, -12 if side == 'l' else 12)
        return rotations, positions, contacts

    def transition_sample(phase, rising):
        source = up_source if rising else down_source
        height = up_height if rising else down_height
        progress = (height[0]-height)/(height[0]-height[-1])
        amount = float(np.clip(np.interp(phase,np.linspace(0,1,len(progress)),progress),0,1))
        if rising: amount = 1-amount
        idle = animations['animation.eva_unit01.idle']['bones']
        rotations = {}
        for b in bones:
            begin = np.array(sample_channel(idle[b]['rotation'],0,b)) if b in idle and 'rotation' in idle[b] else np.zeros(3)
            rotations[b] = ((1-amount)*begin+amount*np.array(low_rotations.get(b,[0,0,0]))).tolist()
        # Preserve the actor's forward hip hinge before descent and during recovery.
        torso = source['Neck']
        lean = np.degrees(np.arctan2(torso[:,0],torso[:,2]))
        residual = lean - np.linspace(lean[0],lean[-1],len(lean))
        rotations['torso_lower'][0] += float(np.clip(np.interp(phase,np.linspace(0,1,len(lean)),residual),-8,8))
        positions = {'root': [0,0,float(low_positions['root'][2]*amount)]}
        for s in ('l','r'):
            knee = rotations['shin_'+s][0]
            positions['shin_'+s] = (np.array(knee_hinge(knee))*amount).tolist()
        # Foot support follows the evaluated mesh during the captured descent.
        floor = min((foot_vertices[s] @ matrix('foot_'+s,rotations,positions).T)[:,1].min() for s in ('l','r'))
        positions['root'][1] = -float(floor)
        return rotations, positions, [True,True]

    for name, duration, distance in (('idle', 2.5, 0), ('walk', 1.01667, 25.8334),
                                     ('run', .8, 31.3944), ('crouch_idle', 2.0, 0),
                                     ('crouch_walk', walking_duration, excursion / stance * 5 / 16),
                                     ('stand_to_crouch', (len(down_height)-1)*down_dt/1.5, 0),
                                     ('crouch_to_stand', (len(up_height)-1)*up_dt/1.5, 0)):
        intervals = round(duration * 60)
        frames = []
        channels = {b: {'rotation': {}, 'position': {}} for b in bones}
        for i in range(intervals + 1):
            phase = i / intervals
            time = phase * duration
            transition = name in ('stand_to_crouch','crouch_to_stand')
            if transition:
                rotations,positions,contacts = transition_sample(phase,name=='crouch_to_stand')
            elif name.startswith('crouch'):
                rotations, positions, contacts = crouch_sample(phase, name == 'crouch_walk')
            else:
                source = animations['animation.eva_unit01.' + name]['bones']
                rotations = {b: sample_channel(v['rotation'], time, b) for b,v in source.items() if 'rotation' in v}
                positions = {b: sample_channel(v['position'], time, b) for b,v in source.items() if 'position' in v}
                contacts = [True, True]
                if name in ('idle','walk'):
                    floor = min((foot_vertices[s] @ matrix('foot_'+s,rotations,positions).T)[:,1].min()
                                for s in ('l','r'))
                    positions['root'] = list(positions.get('root',[0,0,0]))
                    positions['root'][1] -= float(floor)
            root = np.asarray(positions.get('root', [0, 0, 0]), dtype=float)
            values = []
            for b in bones:
                angles = np.asarray(rotations.get(b, [0,0,0])) + np.asarray(bind.get(b, [0,0,0]))
                q = Rotation.from_euler('xyz', angles, degrees=True).as_quat()
                values.append(np.r_[q[3], q[:3]].round(8).tolist())
                channels[b]['rotation'][f'{time:.6f}'] = list(map(float, rotations.get(b, [0,0,0])))
                if b in positions:
                    channels[b]['position'][f'{time:.6f}'] = list(map(float, positions[b]))
            frames.append({'root_m': (root / 112).round(8).tolist(),
                           'rotation_wxyz': values, 'foot_contact': contacts,
                           'bone_position_xyz': {b: list(map(float,p)) for b,p in positions.items() if b != 'root'}})
        if name.startswith('crouch') and not transition:
            frames[-1] = frames[0]
        clips[name] = {'duration_seconds': duration, 'loop': not transition, 'closed_endpoint': True,
                       'root_travel_m': [0,0,distance/35], 'frames': frames}
        review['animation.eva_unit01.' + name] = {'animation_length': duration, 'loop': not transition,
            'bones': {b: {k:v for k,v in channel.items() if v} for b,channel in channels.items()}}
    error = max(support_errors)
    if error > 1e-4:
        raise SystemExit(f'low-stance foot target unreachable: {error}')
    source_hashes = {n: hashlib.sha256(json.dumps(animations['animation.eva_unit01.'+n], sort_keys=True).encode()).hexdigest()
                     for n in ('idle','walk','run')}
    payload = {'schema': 2, 'sample_rate': 60, 'quaternion_order': 'wxyz',
               'bones': bones, 'clips': clips, 'provenance': {
                   'base': 'Existing accepted Tiger idle/walk/run joint channels at 60 Hz; idle/walk root height grounded against the real feet',
                   'base_sha256': source_hashes,
                   'low_stance': 'CMU crouch-step trajectories and ACCAD descent/rise timing and hip hinge, adapted to a 42-block EVA with knee-hinge correction and foot support',
                   'mocap': [{'file':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in (down_path,up_path,walk_path)],
                   'attribution': ['ACCAD / The Ohio State University, Open Motion Project, CC BY 3.0, https://accad.osu.edu/research/motion-lab/mocap-system-and-data', 'CMU Graphics Lab Motion Capture Database, subject 136 trial 09, https://mocap.cs.cmu.edu/'],
                   'max_crouch_ankle_target_error_model_units': error,
                   'visual_status': 'AWAITING_IN_GAME_REVIEW'}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, separators=(',',':'))+'\n', encoding='utf-8')
    args.review.parent.mkdir(parents=True, exist_ok=True)
    args.review.write_text(json.dumps({'format_version':'1.8.0','animations':review}, separators=(',',':'))+'\n', encoding='utf-8')
    print(json.dumps({'output': str(args.output), 'bones':len(bones), 'clips':len(clips),
                      'frames':sum(len(c['frames']) for c in clips.values()),
                      'max_ankle_error':error, 'low_root':low_positions['root']}))


if __name__ == '__main__':
    main()
