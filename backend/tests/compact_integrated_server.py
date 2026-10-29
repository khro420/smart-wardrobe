"""Disposable actual-service fixture; trusted loopback controls are TEST ONLY."""
import json,os,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['SMART_WARDROBE_CRITICAL_PATH_DIAGNOSTICS']='false'
os.environ['SMART_WARDROBE_CRITICAL_PATH_ALLOW_FAILURE']=os.getenv('SMART_WARDROBE_COMPACT_ALLOW_FAILURE','false')
from tests import assistant_critical_path_server as diagnostic
from app.application.recommendation.assistant_execution_selection import AssistantExecutionSelection,REFERENCE,COMPACT
from app.application.recommendation.assistant_scoring_selection import AssistantScoringSelection
from app.application.recommendation.compact_assistant_scorer import CompactAssistantScorer
from app.application.recommendation.outfit_assistant_service import OutfitAssistantService
from scripts.benchmark_compact_exhaustive import memory

fixture,app=diagnostic.fixture,diagnostic.app
if os.getenv('SMART_WARDROBE_COMPACT_MULTI')=='true':
    owner=fixture.workloads['100']['owner']
    with fixture.db.connection() as c:
        for kind,values in (('styles',['vintage']),('garment_categories',[{'kind':'group','value':'top'}])):
            c.execute('INSERT INTO user_preferences VALUES(?,?,?,?,1,?,1,?,?)',(owner+kind,owner,kind,json.dumps({'values':values}),'synthetic','now','now'))
    fixture.workloads['100']['preference_count']=3


@app.post('/_test/compact-integrated/{profile}/{arm}')
def select(profile:str,arm:str):
    AssistantScoringSelection(profile)
    if arm not in ('reference','compact'):raise ValueError('Unknown test arm')
    execution=AssistantExecutionSelection(REFERENCE if arm=='reference' else COMPACT)
    service=fixture.assistant_service()
    service.scoring_profile=profile;service.execution_engine=execution.engine
    return {'engine':execution.engine,'profile':profile,'test_only':True}


@app.get('/_test/resources')
def resources():
    row={'at':datetime.now(timezone.utc).isoformat(),'backend':memory(),
        'method':'Before/after observations, not continuous isolation. Process CPU values are cumulative seconds; CPU LoadPercentage is OS reported. No user processes terminated.',
        'proxy':'Existing production Next proxy; unchanged timeout','servers':'One uvicorn process + production Next on loopback; sequential timing requests'}
    command="$m=Get-CimInstance Win32_OperatingSystem;$c=Get-CimInstance Win32_Processor|Select-Object -First 1;@{free_physical_kib=$m.FreePhysicalMemory;total_physical_kib=$m.TotalVisibleMemorySize;free_virtual_kib=$m.FreeVirtualMemory;cpu_name=$c.Name;cpu_load_percent=$c.LoadPercentage;logical_processors=$c.NumberOfLogicalProcessors;competing_processes=@(Get-Process|Sort-Object WorkingSet64 -Descending|Select-Object -First 8 Name,Id,CPU,WorkingSet64)}|ConvertTo-Json -Depth 4 -Compress"
    try:
        result=subprocess.run(['powershell','-NoProfile','-Command',command],capture_output=True,text=True,timeout=20)
        if result.returncode:raise ValueError('Resource observation command failed')
        row.update(available=True,system=json.loads(result.stdout))
    except Exception as exc:row.update(available=False,error=type(exc).__name__)
    return row


original_rank=CompactAssistantScorer.rank
def observed_rank(self,*args,**kwargs):
    result=original_rank(self,*args,**kwargs)
    row=diagnostic.ACTIVE.get()
    if row is not None and self.kernel:row.update(kernel_stages=self.kernel.timings,cache=self.kernel.cache_statistics)
    return result
CompactAssistantScorer.rank=observed_rank
original_recommend=OutfitAssistantService.recommend
def observed_recommend(self,*args,**kwargs):
    result=original_recommend(self,*args,**kwargs)
    row=diagnostic.ACTIVE.get()
    if row is not None:row['memory']=memory()
    return result
OutfitAssistantService.recommend=observed_recommend


if __name__=='__main__':
    try:fixture.uvicorn.run(app,host='127.0.0.1',port=3201,access_log=False)
    finally:fixture.temporary.cleanup()
