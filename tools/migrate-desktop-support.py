"""Copy local player data into recovery support once. Never change the source installation."""
from pathlib import Path
import argparse, os, shutil, re, json

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--destination',type=Path,required=True);a=parser.parse_args()
 source=Path(os.environ['APPDATA'])/'OpenRA';classic_source=Path(__file__).resolve().parents[2]/'OpenRA/Support';target=a.destination.resolve();target.mkdir(parents=True,exist_ok=True)
 marker=target/'recovery-migration.json'
 if marker.exists():return
 copied=[]
 for installation in [source,classic_source]:
  for rel in ['settings.yaml','maps','Replays','ExperiencePacks','ExperienceReview','GeneratedMissions','CapabilityPacks','ai-companion','Content/ra/v2']:
   old=installation/rel;new=target/rel
   if not old.exists():continue
   if old.is_dir():
    for p in old.rglob('*'):
     dest=new/p.relative_to(old)
     if p.is_file() and not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
   elif not new.exists():new.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(old,new)
   copied.append(str(old))
 settings=target/'settings.yaml'
 if settings.exists():
  text=settings.read_text(encoding='utf-8-sig')
  legacy=(classic_source/'settings.yaml').read_text(encoding='utf-8-sig') if (classic_source/'settings.yaml').exists() else text
  def section(document,key):
   return re.search(r'^'+re.escape(key)+r':[^\n]*(?:\n(?:\t[^\n]*|))*(?=\n[^\t\n]|\Z)',document,re.M)
  # Classic's new mod ID gets copies of its original profiles and key bindings.
  for prefix in ['Experience','Hotkeys','Skirmish','Player','Server']:
   old=prefix+'@ra';new=prefix+'@rtsai-classic-core'
   if re.search(r'^'+re.escape(new)+':',text,re.M):continue
   match=section(legacy,old) or section(text,old)
   if match:text+='\n'+match[0].replace(old+':',new+':',1)+'\n'
  if not section(text,'RTSAIGameplay@rtsai-classic-core'):
   game=section(legacy,'Game');graphics=section(legacy,'Graphics');fields=[]
   for field in ['MouseControlStyle','MouseScroll','UIScrollSpeed','ZoomSpeed','ViewportEdgeScroll','UseAlternateScrollButton','LockMouseWindow','StatusBars','TargetLines','UsePlayerStanceColors']:
    match=re.search(r'^\t'+field+r':[^\n]*',game[0] if game else '',re.M)
    if match:fields.append(match[0])
   camera=re.search(r'^\tViewportDistance:([^\n]*)',graphics[0] if graphics else '',re.M)
   if camera:fields.append('\tBattlefieldCamera:'+camera[1])
   if fields:text+='\nRTSAIGameplay@rtsai-classic-core:\n\tInitialized: true\n'+'\n'.join(fields)+'\n'
  settings.write_text(text,encoding='utf-8')
 # Retarget copied local pack manifests; originals remain intact under the old mod ID.
 for kind in ['CapabilityPacks','ExperiencePacks']:
  old=target/kind/'ra';new=target/kind/'rtsai-classic-core'
  if old.exists() and not new.exists():
   shutil.copytree(old,new)
   for p in new.rglob('pack.yaml'):
    text=p.read_text(encoding='utf-8-sig');text=re.sub(r'(?m)^(\s*(?:TargetMod|Mod): )ra\s*$',r'\1rtsai-classic-core',text);p.write_text(text,encoding='utf-8')
 marker.write_text(json.dumps({'sources':[str(source),str(classic_source)],'copied':copied,'originalsModified':False},indent=2),encoding='utf-8')
 print('Private recovery support prepared. Original player data preserved.')

if __name__=='__main__':main()
