"""Coordinate-true front and side vertex projections for source-rig landmark measurements."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'artifacts/facility_r30/model_inspection';out.mkdir(exist_ok=True)
fig,axes=plt.subplots(1,4,figsize=(17,13),layout='constrained')
for index,unit in enumerate(('00','01')):
    with np.load(ROOT/'artifacts/facility_r30/lux3d'/('un'+unit)/'geometry.npz') as d:
        verts=d['vertices'];tri=d['triangles'];colors=d['colors'].mean(1);normals=d['normals'].mean(1)
    points=verts[tri].mean(1);colors=np.where(colors<=.0031308,12.92*colors,1.055*np.maximum(colors,0)**(1/2.4)-.055).clip(0,1)
    for column,axis in enumerate((0,2)):
        ax=axes[index*2+column];mask=normals[:,2]<-.15 if column==0 else normals[:,0]>.15;ids=np.flatnonzero(mask)[::2]
        order=ids[np.argsort(points[ids,2 if column==0 else 0])[::-1 if column==0 else 1]]
        ax.set_facecolor('#777c83');ax.scatter(points[order,axis],points[order,1],c=colors[order],s=1.1,linewidths=0,rasterized=True)
        ax.set_ylim(0,200);ax.set_xlim((-56,56) if column==0 else (-30,30));ax.set_aspect('equal');ax.set_yticks(range(0,201,10));ax.set_xticks(range(-50 if column==0 else -30,56 if column==0 else 31,10));ax.grid(alpha=.3);ax.set_title('UN-'+unit+(' front X/Y' if column==0 else ' side Z/Y'));ax.set_xlabel('X' if column==0 else 'Z');ax.set_ylabel('Model Y')
fig.savefig(out/'measured_source_projections.png',dpi=160)
