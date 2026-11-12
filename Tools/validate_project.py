"""Read-only file checks, Python 3.12+. Does not run or validate the Wwise application."""
from pathlib import Path
import wave,hashlib,xml.etree.ElementTree as ET,re,json,sys
ROOT=Path(__file__).resolve().parents[1];WW=ROOT/'Wwise/KinmenCoastalRoad'
errors=[];rows=[];durations={}
def check(ok,msg):
 if not ok:errors.append(msg)
def prop(node,name):
 p=node.find(f"PropertyList/Property[@Name='{name}']")
 return None if p is None else p.get('Value')
def wav(p):
 with wave.open(str(p),'rb') as w:
  fmt=(w.getframerate(),w.getsampwidth()*8,w.getnchannels());sec=w.getnframes()/w.getframerate();pcm=w.readframes(w.getnframes())
 return fmt,sec,hashlib.sha256(pcm).hexdigest()
files=sorted((ROOT/'Assets/Audio').glob('*.wav'));check(len(files)==7,'Expected seven final assets');hashes=set()
for p in files:
 fmt,sec,h=wav(p);check(fmt==(48000,24,2),'Wrong format: '+p.name)
 check(sec>30 if p.name.startswith('AMB_') else 0<sec<=12.01,'Wrong duration: '+p.name)
 check(h not in hashes,'Duplicate PCM: '+p.name);hashes.add(h);durations[p.stem]=sec
 original=WW/'Originals/SFX'/p.name
 check(original.exists() and p.read_bytes()==original.read_bytes(),'Wwise source mismatch: '+p.name)
 rows.append(dict(file=p.name,sample_rate=fmt[0],bits=fmt[1],channels=fmt[2],seconds=sec,pcm_sha256=h))
check(len(list((WW/'Originals/SFX').glob('*.wav')))==7,'Expected seven Wwise Originals')
provenance=json.loads((ROOT/'Source/render_provenance.json').read_text(encoding='utf8'))
for r in provenance:check(any(x['file']==r['file'] and x['pcm_sha256']==r['pcm_sha256'] for x in rows),'Rendered PCM changed: '+r['file'])
definitions={};unit_ids=set();docs=[]
for p in list(WW.rglob('*.wwu'))+list(WW.glob('*.wproj')):
 try:r=ET.parse(p).getroot()
 except ET.ParseError as e:errors.append(str(e));continue
 docs.append((p,r));check(r.get('SchemaVersion')=='133','Wrong schema: '+p.name)
 if p.suffix=='.wwu':unit_ids.add(r.get('ID'))
 else:check((r.get('WwiseVersion'),r.get('WwiseBuild'))==('v2025.1.11','9262'),'Wrong target version')
 for n in r.iter():
  if n.get('ID') and n.tag not in ('WwiseDocument','ObjectRef','ActiveSource','MediaID','DefaultConversion') and not n.tag.endswith('Ref'):
   check(n.get('ID') not in definitions,'Duplicate object GUID: '+n.get('ID'));definitions[n.get('ID')]=n
check(len(unit_ids)==22,'Expected 22 work units')
for p,r in docs:
 for n in r.findall('.//ObjectRef'):
  check(n.get('ID') in definitions,'Unresolved object: '+str(n.attrib))
  check(n.get('WorkUnitID') in unit_ids,'Unresolved work unit: '+str(n.attrib))
 for n in r.findall('.//ActiveSource'):check(n.get('ID') in definitions,'Unresolved active source')
 for n in r.findall('.//AudioFile'):check((WW/'Originals/SFX'/n.text).is_file(),'Missing audio: '+n.text)
byname={n.get('Name'):n for n in definitions.values() if n.get('Name')}
wind=byname['AMB_Kinmen_Roadside_Wind_Loop']
# Duplicate source and Sound names: select the Sound explicitly.
wind=next(n for n in definitions.values() if n.tag=='Sound' and n.get('Name')=='AMB_Kinmen_Roadside_Wind_Loop')
check(prop(wind,'IsLoopingEnabled')=='True' and prop(wind,'IsLoopingInfinite')=='True','Bed must loop infinitely')
for name,count,delay,spread in [('RC_Vehicle_Pass',4,25,7),('RC_Birds_Sparse',2,17,5)]:
 n=byname[name];check(len(n.findall('ChildrenList/Sound'))==count,'Wrong random children: '+name)
 for k,v in [('RandomOrSequence','1'),('RandomAvoidRepeating','True'),('RandomAvoidRepeatingCount','1'),('PlayMechanismStepOrContinuous','0'),('PlayMechanismLoop','True'),('PlayMechanismInfiniteOrNumberOfLoops','1'),('PlayMechanismSpecialTransitions','True'),('PlayMechanismSpecialTransitionsType','2'),('PlayMechanismSpecialTransitionsValue',str(delay))]:check(prop(n,k)==v,name+': unexpected '+k)
 mod=n.find("PropertyList/Property[@Name='PlayMechanismSpecialTransitionsValue']/ModifierList/ModifierInfo/Modifier")
 check(mod is not None and prop(mod,'Min')==str(-spread) and prop(mod,'Max')==str(spread),'Wrong delay randomization: '+name)
for n in definitions.values():
 if n.tag=='Sound' and n.get('Name','').startswith('SFX_Vehicle_'):
  check(prop(n,'3DPosition')=='1' and prop(n,'OverridePositioning')=='True' and prop(n,'EnableAttenuation')=='True','Missing positioning: '+n.get('Name'))
  paths=n.findall('PositioningInfo/Position/ChildrenList/Path2D');check(len(paths)==1,'Expected one matched path per vehicle')
  for path in paths:
   ts=[int(p.findtext('Time')) for p in path.findall('PointList/Point')]
   check(ts==sorted(ts) and ts[0]==0,'Invalid path times')
   check(abs(ts[-1]/1000-durations[n.get('Name')])<.001,'Path/audio duration mismatch')
   check(int(prop(path,'Duration'))==ts[-1],'Path duration mismatch')
for name in ['ATT_Vehicles_120m','ATT_Birds_40m']:
 n=byname[name]
 for usage in ['VolumeDryUsage','LowPassFilterUsage']:
  pts=n.findall(f'CurveUsageInfoList/{usage}/CurveUsageInfo/Curve/PointList/Point')
  xs=[float(p.findtext('XPos')) for p in pts];ys=[float(p.findtext('YPos')) for p in pts]
  check(len(pts)>=3 and xs==sorted(xs),'Bad attenuation points: '+name)
  check(ys==sorted(ys,reverse=usage=='VolumeDryUsage'),'Non-monotonic attenuation: '+name)
events={n.get('ID'):n for n in definitions.values() if n.tag=='Event'};check(len(events)==5,'Expected five events')
session=byname['SC_KinmenCoastalRoad'];refs=session.findall('ModuleList/Module/ObjectRef')
check({n.get('ID') for n in refs}==set(events),'Soundcaster events do not match')
for n in definitions.values():
 if n.tag=='Event':
  actions=n.findall('ChildrenList/Action');check(bool(actions),'Empty event')
  for a in actions:check(prop(a,'ActionType')==('2' if n.get('Name').startswith('Stop_') else '1'),'Wrong action type')
rpps=list((ROOT/'Reaper').rglob('*.rpp'));check(len(rpps)==8,'Expected eight REAPER projects')
for p in rpps:
 s=p.read_text(encoding='utf8')
 for src in re.findall(r'^\s+FILE "([^"]+)"',s,re.M):check((p.parent/src.replace('\\','/')).is_file(),'Missing REAPER source: '+src)
 check(not re.search(r'(?i)[A-Z]:[/\\]',s),'Absolute path in '+p.name)
fmt,sec,_=wav(ROOT/'Preview/KinmenCoastalRoad_120s.wav');check(fmt==(48000,24,2) and sec==120,'Preview format/duration mismatch')
photo=ROOT/'Assets/Images/Kinmen_Coastal_Road.jpg';pr=json.loads((ROOT/'Source/photo_provenance.json').read_text(encoding='utf8'))
check(hashlib.sha256(photo.read_bytes()).hexdigest()==pr['sha256'],'Photo differs from provided original')
html=(ROOT/'Preview/index.html').read_text(encoding='utf8')
for src in re.findall(r'(?:src|href)="([^"]+)"',html):
 if not src.startswith(('http:','https:','#')):check((ROOT/'Preview'/src).exists(),'Broken HTML link: '+src)
result=dict(file_checks_passed=not errors,wwise_runtime_validated=False,scope='Headers, unique PCM, references, settings, path timing, portable media links and photo hash; not application compatibility or listening quality.',assets=rows,work_units=len(unit_ids),reaper_projects=len(rpps),errors=errors)
print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(1 if errors else 0)
