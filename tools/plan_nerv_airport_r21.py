"""Native one-way airport circuits and a direct NERV / UN shuttle."""
from pathlib import Path
import copy,json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_repair_r21/airport';STAGE=ROOT/'.Codex/r21-transit'
def main():
 OUT.mkdir(parents=True,exist_ok=True);rails=[];opposite={'N':'S','S':'N','E':'W','W':'E'}
 def rail(name,a,b,ha,hb,kind='rail',speed=45):
  rails.append(dict(id='F2_'+name,**{'from':a,'to':b},from_angle=ha,to_angle=opposite[hb],kind=kind,mode='AIRPLANE',speed=speed,reverse_speed=0))
 def path(name,nodes,speed=45):
  for i,((a,ha),(b,hb)) in enumerate(zip(nodes,nodes[1:])):rail(name+str(i),a,b,ha,hb,speed=speed)
 rail('nerv_gate',[630,72,-10],[670,72,-10],'E','E','platform')
 path('nerv_depart', [([670,72,-10],'E'),([830,72,-10],'E'),([870,72,-50],'N'),([870,72,-105],'N'),([910,72,-145],'E')])
 rail('nerv_roll',[910,72,-145],[1160,72,-145],'E','E',speed=260)
 rail('nerv_takeoff',[1160,72,-145],[1480,185,-145],'E','E','runway',360)
 rail('nerv_land',[1480,185,-95],[1160,72,-95],'W','W','runway',260)
 path('nerv_rollin',[([1160,72,-95],'W'),([710,72,-95],'W')],200)
 path('nerv_arrive',[([710,72,-95],'W'),([580,72,-95],'W'),([540,72,-55],'S'),([540,72,-50],'S'),([580,72,-10],'E'),([630,72,-10],'E')])
 rail('depot',[410,72,-10],[500,72,-10],'E','E','siding')
 path('yard_link',[([500,72,-10],'E'),([580,72,-10],'E')])
 rail('un_gate',[6720,74,-6070],[6720,74,-6110],'N','N','platform')
 path('un_depart',[([6720,74,-6110],'N'),([6720,74,-6500],'N'),([6760,74,-6540],'E'),([6784,74,-6580],'N')])
 rail('un_roll',[6784,74,-6580],[6784,74,-6640],'N','N',speed=260)
 rail('un_takeoff',[6784,74,-6640],[6784,185,-6960],'N','N','runway',360)
 rail('un_land',[6832,185,-6960],[6832,74,-6600],'S','S','runway',260)
 rail('un_rollin',[6832,74,-6600],[6832,74,-6160],'S','S',speed=200)
 path('un_arrive',[([6832,74,-6160],'S'),([6832,74,-6060],'S'),([6792,74,-6020],'W'),([6760,74,-6020],'W'),([6720,74,-6060],'N'),([6720,74,-6070],'N')])
 stations=[dict(id='nerv_airport',name='NERV 航空基地',min=[370,64,-40],max=[690,94,35]),dict(id='un_airport',name='联合国总部机场',min=[6690,70,-6130],max=[6745,98,-6040])]
 lines=[dict(id='F2',name='NERV—联合国总部高速运输线',color=0x943B3B,mode='AIRPLANE',platforms=['F2_nerv_gate','F2_un_gate','F2_nerv_gate'],siding='F2_depot',cars=[dict(id='a320',length=30,width=2,bogie1=-14.25,bogie2=-2,padding1=0,padding2=0)],frequency=1,dwell=18000,repeat=True,cruise=260)]
 plan=dict(revision=21,rails=rails,stations=stations,lines=lines)
 (OUT/'native_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
 if not STAGE.exists():shutil.copytree(ROOT/'run/saves/SEELE_R21_REVIEW/mtr',STAGE)
 runtime=json.loads((ROOT/'artifacts/world_rebuild_r20/transit/runtime.json').read_text());java=Path(runtime['java']);cp=runtime['classpath'];classes=ROOT/'.Codex/r21-java';classes.mkdir(exist_ok=True)
 subprocess.run([str(java/'javac.exe'),'-encoding','UTF-8','-cp',cp,'-d',str(classes),str(ROOT/'tools/java/RegionalTransitAuthor.java')],check=True)
 subprocess.run([str(java/'java.exe'),'-cp',cp+';'+str(classes),'RegionalTransitAuthor',str(OUT/'native_plan.json'),str(STAGE),str(OUT/'native'),'--append'],check=True)
 print('F2 native network authored')
if __name__=='__main__':main()
