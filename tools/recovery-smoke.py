"""Rendered recovery acceptance. Dedicated support directory; never changes installed/user settings."""
from pathlib import Path
import argparse,subprocess,os,time,json,sys,contextlib,shutil
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--engine',type=Path,required=True);p.add_argument('--mod',default='rtsai');p.add_argument('--screen',default='home');p.add_argument('--seconds',type=int,default=25);p.add_argument('--map');p.add_argument('--bots',default='Multi0:normal:china,Multi1:normal:iran');p.add_argument('--content',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--art-tools',type=Path,required=True);p.add_argument('--leave-open',action='store_true');a=p.parse_args()
 data_root=a.engine if (a.engine/'recovery-build.json').exists() else ROOT
 a.out.mkdir(parents=True,exist_ok=True);support=a.out/'support';support.mkdir(exist_ok=True)
 if a.content and not (support/'Content').exists():shutil.copytree(a.content,support/'Content')
 sys.path.insert(0,str(a.art_tools));import route_lock
 env=dict(os.environ);env.update(OPENRA_AI_HOST='0',OPENRA_AI_COMPANION='0',OPENRA_AI_DISABLE_AUTOSTART='1',RTSAI_RECOVERY_SCREEN=a.screen)
 args=[str(a.engine/'bin/OpenRA.exe'),f'Engine.EngineDir={a.engine}',f'Engine.ModSearchPaths={data_root / "mods"},{a.engine / "mods"}',f'Engine.SupportDir={support}',f'Game.Mod={a.mod}','Game.FetchNews=false','Game.IntroductionPromptVersion=99','Debug.SystemInformationVersionPrompt=99','Graphics.Mode=Windowed','Graphics.WindowedSize=1440,900','Graphics.UIScale=1','Game.ViewportEdgeScroll=false','Sound.Mute=true']
 if a.map:
  source=next((p/a.map for p in [data_root/'mods'/a.mod/'maps',data_root/'mods'/a.mod/'standalone/maps',data_root/'mods'/a.mod/'campaigns/maps'] if (p/a.map).exists()),None)
  if source is None:raise ValueError('Map not found: '+a.map)
  manifest=(data_root/'mods'/a.mod/'mod.yaml').read_text(encoding='utf-8-sig')
  import re
  version=re.search(r'^\s*Version: (.+)$',manifest,re.M).group(1).strip()
  destination=support/'maps'/a.mod/version/'recovery-observe'
  if not destination.exists():
   shutil.copytree(source,destination)
   y=(destination/'map.yaml').read_text(encoding='utf-8-sig')
   y=re.sub(r'^RequiresMod:.*$', 'RequiresMod: '+a.mod,y,flags=re.M)
   if re.search(r'^Rules:',y,re.M):y=re.sub(r'^Rules:(.*)$',lambda m:'Rules: '+m.group(1).strip()+', recovery-observe.yaml',y,flags=re.M)
   else:y+='\nRules: recovery-observe.yaml\n'
   (destination/'map.yaml').write_text(y,encoding='utf-8')
   (destination/'recovery-observe.yaml').write_text('World:\n\tScriptTriggers:\n\tLuaScript:\n\t\tScripts: recovery-observe.lua\n',encoding='utf-8')
   shutil.copy2(ROOT/'tools/standalone-smoke/observe.lua',destination/'recovery-observe.lua')
  args.extend(['Launch.Map=recovery-observe',f'Launch.Bots={a.bots}'])
 with route_lock.lock('game-window',timeout=180,agent='desktop-recovery'):
  with (a.out/'stdout.log').open('w',encoding='utf-8') as log:
   proc=subprocess.Popen(args,cwd=a.engine,env=env,stdout=log,stderr=subprocess.STDOUT);start=time.time();grabs=[]
   for target in [8,16,a.seconds]:
    while proc.poll() is None and time.time()-start<target:time.sleep(.25)
    if proc.poll() is not None:break
    dest=a.out/f'window-{target:03}.png';subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(a.art_tools/'capture_window.ps1'),'-ProcessId',str(proc.pid),'-OutFile',str(dest)],capture_output=True,timeout=20)
    if dest.exists():grabs.append(str(dest))
   early=proc.poll() is not None;exit_code=proc.poll()
   if not early and not a.leave_open:proc.terminate();proc.wait(timeout=15)
   log.flush()
   output=(a.out/'stdout.log').read_text(encoding='utf-8',errors='replace')
   failed=early or 'Exception of type' in output or 'Unhandled exception' in output
   if not a.map and 'RTSAI_NATIVE_SCREEN|' not in output:failed=True
   if a.screen.startswith('switch-'):
    expected='rtsai-classic-core' if a.screen=='switch-classic' else 'rtsai'
    if 'RTSAI_NATIVE_MODE|'+expected not in output:failed=True
   census=[]
   if a.map:
    lua=support/'Logs/lua.log'
    census=[x for x in lua.read_text(encoding='utf-8',errors='replace').splitlines() if 'CENSUS|' in x] if lua.exists() else []
    if len(census)<2:failed=True
    requested={b.split(':')[0]:b.split(':')[2] for b in a.bots.split(',') if len(b.split(':'))==3}
    seen={line.split('|')[2]:line.split('|')[3] for line in census}
    if any(seen.get(player)!=faction for player,faction in requested.items()):failed=True
    if census and max(int(line.split('|')[1]) for line in census)<750:failed=True
    server=support/'Logs/server.log'
    if server.exists() and 'Rejected connection' in server.read_text(encoding='utf-8',errors='replace'):failed=True
   report={'mod':a.mod,'screen':a.screen,'pid':proc.pid,'exitedEarly':early,'exitCode':exit_code,'grabs':grabs,'args':args,'leftOpen':a.leave_open and not early,'passed':not failed}
   report['census']=census
   (a.out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
   if failed:sys.exit(1)
if __name__=='__main__':main()
