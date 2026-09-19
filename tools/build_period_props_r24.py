"""Original street/station details based on inspected 1990 public-domain references.

Geometry and colours are authored here; no photograph is used as a texture.
All coordinates are block metres and each fixture stays in its declared envelope.
"""
from pathlib import Path
import json,math
import numpy as np
import build_tv_machinery_r16 as mesh

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r24/props'
GREEN=0x547E69;PHONE=0x57933A;CREAM=0xD3CEB5;STEEL=0x9BA9A5;DARK=0x28332F;BLACK=0x1B2623;RED=0x934941;PAPER=0xE1DDC7;LIGHT=0xE8ECCF
box=mesh.box;housing=mesh.housing;cylinder=mesh.cylinder

def tube(a,b,r=.025,col=STEEL,segments=12):cylinder(a,b,r,col,segments)
def grille(x,y,z,w,h):
    housing(x,y,z,w,h,.025,.016,DARK)
    for Y in np.arange(y+.025,y+h-.015,.035):box(x+.018,Y,z+.026,w-.036,.008,.007,STEEL)

def public_phone():
    mesh.use('public_phone')
    # Slim metal booth, open front, with a rain hood and a supported phone shelf.
    for x in (.06,.94):
        for z in (.07,.86):housing(x-.025,0,z-.025,.05,2.22,.05,.008,STEEL)
    housing(.025,2.18,.025,.95,.11,.92,.03,GREEN)
    housing(.12,2.10,.22,.76,.055,.52,.01,CREAM)
    box(.18,2.085,.29,.64,.018,.30,LIGHT)
    box(.075,.58,.075,.85,.065,.72,CREAM)
    for x in (.095,.845):box(x,0,.095,.06,.58,.54,GREEN)
    housing(.21,.665,.135,.56,.73,.36,.07,PHONE)
    housing(.235,1.20,.503,.33,.12,.018,.018,BLACK)
    housing(.59,1.215,.505,.13,.065,.019,.012,DARK)
    box(.614,1.245,.526,.083,.006,.006,BLACK)
    for row in range(4):
        for col in range(3):housing(.30+col*.055,1.095-row*.052,.504,.04,.036,.025,.009,CREAM)
    housing(.535,.777,.505,.17,.065,.021,.012,DARK)
    housing(.549,.785,.529,.142,.008,.012,.003,BLACK)
    # Receiver with curved grip and two caps; coil hangs clear of the shelf.
    points=[(.185+.045*math.sin(t*math.pi),1.34-.46*t,.49+.012*math.sin(t*math.pi)) for t in np.linspace(0,1,14)]
    for a,b in zip(points,points[1:]):tube(a,b,.034,PHONE,16)
    for y in (.9,1.315):
        cylinder((.187,y,.482),(.187,y,.55),.062,PHONE,20)
        cylinder((.187,y,.55),(.187,y,.558),.041,DARK,16)
        for i in range(6):
            a=2*math.pi*i/6;cylinder((.187+.024*math.cos(a),y+.024*math.sin(a),.558),(.187+.024*math.cos(a),y+.024*math.sin(a),.561),.003,BLACK,6)
    points=[]
    for t in np.linspace(0,1,110):
        points.append((.20+.018*math.cos(t*math.pi*34),.88-.21*math.sin(t*math.pi),.56+.018*math.sin(t*math.pi*34)))
    for a,b in zip(points,points[1:]):tube(a,b,.005,BLACK,6)
    box(.08,1.91,.079,.84,.15,.022,GREEN)
    mesh.use('phone_glass')
    box(.065,.64,.085,.012,1.49,.77,0xB4CCC5)
    box(.923,.64,.085,.012,1.49,.77,0xB4CCC5)
    box(.077,.64,.073,.846,1.49,.012,0xB4CCC5)

def notice_board():
    mesh.use('notice_board')
    for x in (.14,.86):
        cylinder((x,.025,.45),(x,1.94,.45),.022,STEEL,12)
        cylinder((x,.006,.45),(x,.033,.45),.12,STEEL,16)
    housing(.055,.63,.415,.89,1.23,.09,.026,GREEN)
    box(.082,.662,.507,.836,1.164,.012,PAPER)
    box(.082,1.645,.52,.836,.181,.009,GREEN)
    for x in (.115,.865):
        for y in (.70,1.785):cylinder((x,y,.526),(x,y,.536),.012,STEEL,8)
    for y in (.895,1.115,1.335):box(.105,y,.524,.79,.004,.004,0xADAF9F)

def utility_box():
    mesh.use('utility_box')
    housing(.10,.08,.055,.8,.86,.24,.035,0xB6BEAE)
    grille(.15,.16,.298,.30,.27)
    housing(.51,.16,.305,.28,.65,.014,.009,CREAM)
    box(.738,.425,.322,.018,.085,.016,DARK)
    for x in (.19,.31,.73):
        tube((x,0,.17),(x,.12,.17),.028,STEEL)
        for y in (.045,.095):cylinder((x,y-.009,.17),(x,y+.009,.17),.034,DARK,12)
    for x in (.145,.855):
        for y in (.12,.9):cylinder((x,y,.298),(x,y,.312),.014,DARK,8)

def pipe_run():
    mesh.use('pipe_run')
    for x,r,c in [(.25,.055,STEEL),(.50,.043,GREEN),(.71,.027,0xA69472)]:
        tube((x,0,.16),(x,1,.16),r,c,16)
        for y in (.16,.83):
            cylinder((x,y-.035,.16),(x,y+.035,.16),r+.015,DARK,16)
    for y in (.16,.83):
        housing(.13,y-.018,.023,.67,.036,.07,.006,STEEL)
        for x in (.16,.77):cylinder((x,y,.095),(x,y,.126),.021,DARK,8)

def bollard():
    mesh.use('bollard')
    cylinder((.5,.015,.5),(.5,.08,.5),.16,DARK,20)
    cylinder((.5,.08,.5),(.5,.74,.5),.067,CREAM,20)
    cylinder((.5,.61,.5),(.5,.70,.5),.069,0xAE8B51,20)
    cylinder((.5,.74,.5),(.5,.78,.5),.067,STEEL,20)

def hydrant():
    mesh.use('hydrant')
    cylinder((.5,0,.5),(.5,.10,.5),.16,DARK,20)
    cylinder((.5,.10,.5),(.5,.66,.5),.095,RED,20)
    cylinder((.5,.62,.5),(.5,.68,.5),.13,RED,20)
    for y in (.12,.61):
        for i in range(6):
            a=i*math.pi/3;tube((.5+.115*math.cos(a),y,.5+.115*math.sin(a)),(.5+.115*math.cos(a),y+.02,.5+.115*math.sin(a)),.016,STEEL,6)
    cylinder((.29,.43,.5),(.71,.43,.5),.066,RED,20)
    for x in (.285,.695):
        cylinder((x,.43,.5),(x+.02,.43,.5),.082,RED,12)
    tube((.5,.68,.5),(.5,.725,.5),.025,STEEL,6)

def clock():
    mesh.use('wall_clock')
    cylinder((.5,.5,.055),(.5,.5,.15),.42,DARK,40)
    cylinder((.5,.5,.15),(.5,.5,.178),.388,CREAM,40)
    for i in range(60):
        a=i*math.pi/30;r0=.315 if i%5==0 else .346;r1=.366
        tube((.5+r0*math.sin(a),.5+r0*math.cos(a),.181),(.5+r1*math.sin(a),.5+r1*math.cos(a),.181),.006 if i%5==0 else .0025,DARK,6)
    # Hands are separate meshes, pivoted at the clock centre by the renderer.
    for name,length,width in [('clock_hour',.235,.024),('clock_minute',.32,.013)]:
        mesh.use(name);housing(-width/2,-.045,0,width,length+.045,.009,.004,DARK)
    mesh.use('wall_clock');cylinder((.5,.5,.182),(.5,.5,.198),.019,STEEL,16)

def drinking_fountain():
    mesh.use('drinking_fountain')
    housing(.17,0,.21,.66,.67,.56,.06,GREEN)
    housing(.14,.65,.17,.72,.075,.64,.025,STEEL)
    box(.22,.727,.23,.56,.008,.48,DARK)
    for z in np.arange(.25,.69,.045):box(.24,.737,float(z),.52,.009,.016,STEEL)
    tube((.7,.73,.3),(.7,.86,.3),.019,STEEL,16)
    tube((.7,.86,.3),(.63,.88,.36),.019,STEEL,16)
    cylinder((.625,.874,.359),(.619,.887,.368),.022,DARK,12)

def cafe_counter():
    mesh.use('cafe_counter')
    housing(.025,0,.08,.95,.84,.84,.035,GREEN)
    housing(.005,.84,.025,.99,.075,.95,.026,CREAM)
    for x in (.07,.53):
        housing(x,.14,.928,.4,.57,.022,.012,0x42604D)
        tube((x+.32,.40,.963),(x+.32,.52,.963),.012,STEEL)
    box(.09,.06,.93,.82,.025,.013,STEEL)

def cafe_table():
    mesh.use('cafe_table')
    cylinder((.5,.025,.5),(.5,.065,.5),.26,DARK,28)
    cylinder((.5,.065,.5),(.5,.71,.5),.038,STEEL,16)
    housing(.06,.70,.08,.88,.065,.84,.04,0x766148)
    # A small ceramic cup and a plain folded menu; no brand artwork.
    cylinder((.70,.77,.35),(.70,.779,.35),.073,CREAM,20)
    cylinder((.70,.779,.35),(.70,.867,.35),.043,CREAM,20)
    cylinder((.70,.868,.35),(.70,.87,.35),.033,0x443021,20)
    tube((.740,.806,.35),(.765,.818,.35),.011,CREAM)
    tube((.765,.818,.35),(.740,.852,.35),.011,CREAM)
    housing(.22,.77,.59,.19,.012,.23,.003,PAPER)
    for z in (.63,.66,.69,.72):box(.24,.783,z,.14,.001,.006,DARK)

def cafe_stool():
    mesh.use('cafe_stool')
    for x in (.30,.70):
        for z in (.30,.70):tube((x,.02,z),(.5+(x-.5)*.8,.44,.5+(z-.5)*.8),.018,STEEL)
    for a,b in [((.32,.18,.32),(.68,.18,.32)),((.32,.18,.68),(.68,.18,.68))]:tube(a,b,.012,STEEL)
    housing(.25,.43,.25,.5,.055,.5,.06,0x714A39)
    housing(.245,.479,.245,.51,.07,.51,.07,0x8F5F41)

def newspaper_rack():
    mesh.use('newspaper_rack')
    for x in (.10,.90):tube((x,.012,.16),(x,1.72,.34),.025,DARK);tube((x,.012,.84),(x,1.72,.34),.022,DARK)
    for y in (.20,.57,.94,1.31):
        housing(.12,y,.26,.76,.055,.52,.018,GREEN)
        for i in range(3):
            box(.16+i*.23,y+.056,.30,.205,.19,.37,PAPER if i!=1 else CREAM)
            for row in range(5):box(.176+i*.23,y+.082+row*.029,.678,.172,.011,.003,0x6E7161)
        tube((.12,y+.11,.78),(.88,y+.11,.78),.012,STEEL)
    housing(.08,1.60,.31,.84,.17,.09,.02,GREEN)

def coffee_machine():
    mesh.use('coffee_machine')
    housing(.06,0,.12,.88,.76,.74,.025,GREEN)
    housing(.03,.76,.075,.94,.055,.85,.028,STEEL)
    housing(.12,.83,.20,.70,.40,.38,.06,CREAM)
    box(.16,.955,.586,.62,.08,.012,DARK)
    for x in (.28,.60):
        cylinder((x,.995,.60),(x,.995,.622),.031,RED,12)
        tube((x,.955,.595),(x,.88,.69),.022,STEEL)
    box(.17,.818,.59,.62,.018,.23,DARK)
    for x in np.arange(.20,.76,.055):box(float(x),.837,.61,.016,.007,.18,STEEL)
    for x in (.31,.61):
        cylinder((x,1.231,.32),(x,1.28,.32),.055,CREAM,16)

def shop_sign():
    mesh.use('shop_sign')
    housing(-.94,.035,.045,2.88,.76,.07,.045,GREEN)
    housing(-.905,.071,.116,2.81,.69,.019,.025,CREAM)
    box(-.82,.245,.137,2.64,.009,.005,GREEN)
    for x in (-.855,1.855):
        for y in (.125,.71):cylinder((x,y,.138),(x,y,.147),.013,STEEL,10)

def document_cart():
    mesh.use('document_cart')
    for x in (.17,.83):
        for z in (.17,.83):
            cylinder((x-.025,.075,z),(x+.025,.075,z),.055,DARK,16)
            tube((x,.13,z),(x,.88,z),.014,STEEL)
    for y in (.23,.57,.80):
        housing(.10,y,.10,.80,.035,.80,.016,GREEN)
        for x in (.10,.89):box(x,y+.035,.10,.012,.085,.80,STEEL)
        box(.10,y+.035,.10,.80,.085,.012,STEEL)
    for i in range(6):
        x=.18+i*.10;housing(x,.605,.18,.073,.19,.55,.006,CREAM if i%2 else PAPER)
        box(x+.025,.63,.735,.027,.095,.005,DARK)
    for i in range(3):housing(.28+i*.006,.835+i*.012,.30,.40,.010,.45,.006,PAPER)
    tube((.17,.91,.17),(.83,.91,.17),.022,DARK)

def tech_bench():
    mesh.use('tech_bench')
    for x in (.09,.91):
        for z in (.12,.86):
            cylinder((x,0,z),(x,.785,z),.026,STEEL,12)
            cylinder((x,0,z),(x,.045,z),.032,DARK,12)
    housing(.025,.77,.055,.95,.06,.89,.025,CREAM)
    housing(.16,.83,.18,.67,.48,.50,.055,GREEN)
    housing(.195,.94,.681,.41,.285,.018,.025,DARK)
    mesh.use('tech_glow')
    box(.22,.964,.704,.36,.23,.003,0x173C30)
    for x in np.arange(.24,.58,.055):box(float(x),.976,.708,.0015,.20,.002,0x37634A)
    for y in np.arange(.99,1.18,.038):box(.23,float(y),.708,.33,.0015,.002,0x37634A)
    points=[]
    for t in np.linspace(0,1,38):
        bump=.074*math.exp(-((t-.55)/.06)**2)-.037*math.exp(-((t-.63)/.04)**2)
        points.append((.23+.34*t,1.06+.012*math.sin(t*math.pi*5)+bump,.713))
    for a,b in zip(points,points[1:]):tube(a,b,.0025,0x9DC983,6)
    mesh.use('tech_bench')
    for x,y,r in [(.71,1.18,.043),(.69,1.045,.027),(.76,1.045,.027)]:
        cylinder((x,y,.682),(x,y,.718),r,DARK,16);tube((x,y,.719),(x,y+r*.55,.719),.003,CREAM,6)
    box(.24,.876,.681,.32,.035,.020,DARK)
    for i in range(5):housing(.25+i*.057,.885,.704,.034,.012,.014,.003,CREAM)
    housing(.64,.84,.79,.20,.025,.13,.008,DARK)

def parked_bicycle():
    mesh.use('parked_bicycle');paint=0x65796D
    rear=(-.10,.355,.5);front=(1.08,.355,.5)
    for centre in (rear,front):
        x,y,z=centre
        for radius,thickness,col in ((.325,.023,DARK),(.292,.008,STEEL)):
            points=[(x+radius*math.cos(a),y+radius*math.sin(a),z) for a in np.linspace(0,math.pi*2,37)]
            for a,b in zip(points,points[1:]):tube(a,b,thickness,col,8)
        cylinder((x,y,z-.035),(x,y,z+.035),.029,STEEL,12)
        for a in np.linspace(0,math.pi*2,20,endpoint=False):tube((x,y,z),(x+.290*math.cos(a),y+.290*math.sin(a),z),.0025,STEEL,5)
        # Full curved metal mudguards, independent of the tyres.
        points=[(x+.363*math.cos(a),y+.363*math.sin(a),z) for a in np.linspace(.06,math.pi-.06,27)]
        for a,b in zip(points,points[1:]):
            aa=(a[0],a[1],z-.033);bb=(b[0],b[1],z-.033);cc=(b[0],b[1],z+.033);dd=(a[0],a[1],z+.033);mesh.quad(aa,bb,cc,dd,paint)
    pedal=(.38,.34,.5);seat=(.28,.83,.5);head=(.82,.84,.5)
    for a,b in [(rear,pedal),(rear,seat),(pedal,seat),(pedal,head),(head,(.52,.50,.5)),((.52,.50,.5),(.31,.57,.5)),(head,front)]:tube(a,b,.017,paint,12)
    tube(seat,(.27,.91,.5),.012,STEEL);housing(.13,.90,.42,.28,.05,.16,.026,DARK)
    cylinder((.38,.34,.455),(.38,.34,.475),.095,STEEL,24)
    for sign in (-1,1):
        tube((.38,.34,.5+sign*.03),(.38+sign*.085,.28,.5+sign*.08),.009,STEEL)
        housing(.38+sign*.085-.045,.268,.5+sign*.085-.04,.09,.025,.08,.008,DARK)
    tube(head,(.83,1.04,.5),.012,STEEL)
    for side in (-1,1):
        tube((.83,1.04,.5),(.75,1.01,.5+side*.22),.012,STEEL)
        tube((.75,1.01,.5+side*.22),(.64,.985,.5+side*.22),.018,DARK)
    for z in (.40,.60):
        tube((-.28,.76,z),(.20,.76,z),.010,STEEL)
        tube((-.10,.355,.5),(-.20,.76,z),.008,STEEL)
    for x in np.linspace(-.27,.19,6):tube((float(x),.76,.40),(float(x),.76,.60),.006,STEEL)
    # Wire basket and a discreet rear reflector.
    for y in (.88,1.08):
        for a,b in [((.90,y,.34),(1.17,y,.34)),((1.17,y,.34),(1.17,y,.66)),((1.17,y,.66),(.90,y,.66)),((.90,y,.66),(.90,y,.34))]:tube(a,b,.006,STEEL,6)
    for z in np.linspace(.35,.65,6):tube((1.17,.88,float(z)),(1.17,1.08,float(z)),.0035,STEEL,5)
    housing(-.285,.738,.465,.012,.041,.07,.005,RED)
    tube((.29,.36,.48),(.15,.012,.31),.009,DARK,8)

def vending_machine():
    mesh.use('vending_machine')
    for x in (.14,.78):housing(x,.0,.16,.09,.08,.60,.016,DARK)
    housing(.045,.08,.06,.91,1.86,.88,.045,CREAM)
    housing(.072,.115,.945,.856,1.79,.024,.025,0xD6D6C8)
    housing(.105,.80,.972,.615,1.00,.016,.028,DARK)
    mesh.use('vending_glow')
    box(.128,.83,.99,.57,.94,.005,0xB8C2B2)
    for row in range(3):
        y=.91+row*.275
        box(.134,y-.065,.995,.56,.013,.015,STEEL)
        for i,col in enumerate((0x8D423A,0x617E51,0xBAB9A3,0x516D81,0xAD8C53)):
            x=.181+i*.105
            cylinder((x,y,1.015),(x,y+.145,1.015),.032,col,12)
            cylinder((x,y+.143,1.015),(x,y+.151,1.015),.030,STEEL,12)
            box(x-.029,y+.056,1.045,.058,.031,.004,PAPER)
            housing(x-.034,y-.044,1.013,.068,.026,.015,.008,GREEN)
    mesh.use('vending_machine')
    housing(.738,1.21,.98,.15,.18,.032,.012,DARK)
    box(.755,1.32,1.014,.108,.004,.006,BLACK)
    cylinder((.81,1.18,.987),(.81,1.18,1.027),.027,STEEL,12)
    housing(.754,.96,.98,.113,.075,.029,.011,DARK)
    housing(.132,.31,.975,.555,.27,.025,.035,DARK)
    housing(.15,.34,1.001,.52,.205,.016,.025,0x7F8B82)
    box(.155,.49,1.019,.50,.013,.006,STEEL)
    grille(.737,.20,.98,.145,.36)
    housing(.115,1.81,.975,.77,.082,.019,.012,RED)

def letter_box():
    mesh.use('letter_box')
    cylinder((.5,.014,.5),(.5,.045,.5),.22,DARK,24)
    housing(.39,.045,.40,.22,.52,.20,.025,0x7C8A82)
    housing(.19,.49,.25,.62,.72,.5,.058,0xA3443B)
    housing(.21,1.19,.235,.58,.08,.53,.04,0xA84A40)
    box(.245,1.058,.756,.51,.035,.016,DARK)
    housing(.24,.73,.758,.28,.22,.014,.015,PAPER)
    for y in (.78,.825,.87):box(.264,y,.775,.231,.005,.004,0x8D8473)
    box(.587,.775,.756,.125,.095,.007,PAPER)
    tube((.612,.824,.767),(.685,.824,.767),.006,RED,6)
    tube((.648,.79,.767),(.648,.855,.767),.006,RED,6)

def main():
    OUT.mkdir(parents=True,exist_ok=True);mesh.PARTS.clear()
    for fn in [public_phone,notice_board,utility_box,pipe_run,bollard,hydrant,clock,drinking_fountain,cafe_counter,cafe_table,cafe_stool,newspaper_rack,coffee_machine,shop_sign,document_cart,tech_bench,parked_bicycle,vending_machine,letter_box]:fn()
    data={'stride':6,'parts':mesh.PARTS,'opacity':{'phone_glass':.20},'authorship':'Original procedural geometry; see tools/build_period_props_r24.py'}
    dest=ROOT/'src/main/resources/assets/projectseele/mesh/period_details_r24.json'
    rows=[]
    for name,vertices in mesh.PARTS.items():
        a=np.array(vertices).reshape(-1,6);assert np.isfinite(a).all()
        if name=='shop_sign':
            assert a[:,0].min()>=-1 and a[:,0].max()<=2 and a[:,1].min()>=0 and a[:,1].max()<1 and a[:,2].min()>=0 and a[:,2].max()<1
        elif name=='parked_bicycle':
            assert a[:,0].min()>=-.5 and a[:,0].max()<=1.5 and a[:,1].min()>=-.001 and a[:,1].max()<1.2 and a[:,2].min()>=0 and a[:,2].max()<=1,name
        elif name in ('vending_machine','vending_glow'):
            assert a[:,:3].min()>=-.001 and a[:,0].max()<=1 and a[:,2].max()<1.06 and a[:,1].max()<2,name
        elif not name.startswith('clock_'):
            assert a[:,:3].min()>=-.001 and a[:,0].max()<=1 and a[:,2].max()<=1 and a[:,1].max()<2.5,name
        rows.append(dict(name=name,triangles=len(a)//3,lo=a[:,:3].min(0).tolist(),hi=a[:,:3].max(0).tolist()))
    dest.write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
    (OUT/'geometry.json').write_text(json.dumps(rows,indent=2));print('Original period fixtures:',rows)
if __name__=='__main__':main()
