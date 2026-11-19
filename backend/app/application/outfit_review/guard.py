"""Portable evaluation guard derived from Phase 3D-A; owned workers only.

No application GPU settings are changed. Missing activity/job readings fail closed.
"""
from pathlib import Path
import json,time,math,threading,subprocess,sqlite3,psutil
R=Path(__file__).parent
from app.infrastructure.config import DATABASE_PATH
DB=DATABASE_PATH.resolve()
RAM_FLOOR=2*2**30;VRAM_FLOOR=512;ACTIVITY_EPSILON=.1;SUSTAINED=2;QUIET=5;STALE=3

def measured_activity(record,expected,now):
 """A complete valid engine inventory can report no context for an idle PID.

 Missing/stale/invalid global telemetry is never interpreted as zero activity.
 Process creation identities and job state are independently monitored below.
 """
 if (record.get('version')!='gpu-engine-activity-1.1.0' or record.get('global_valid') is not True
     or type(record.get('global_counter_count')) is not int or record['global_counter_count']<=0
     or abs(now-record.get('time',0))>=STALE or set(record.get('requested_ids',()))!=expected):return False,0
 samples=record.get('samples',[])
 if isinstance(samples,dict):samples=[samples]
 seen={int(s['instance'].split('_')[1]) for s in samples}
 observed=set(record.get('observed_gpu_pids',()))
 if (not seen<=expected or not seen<=observed or expected & observed != seen
     or record.get('counter_count')!=len(samples)
     or not all(s['status'] in (0,1) and math.isfinite(s['percent']) and s['percent']>=0 for s in samples)):return False,0
 return True,max((s['percent'] for s in samples),default=0)

class Policy:
 def __init__(self):self.quiet=0;self.active=0
 def activity(self,valid,pct):
  if not valid:return 'GPU activity measurement invalid or missing'
  if pct>ACTIVITY_EPSILON:
   self.active+=1;self.quiet=0
   if self.active>=SUSTAINED:return 'Sustained backend GPU-engine activity detected'
  else:self.active=0;self.quiet+=1
  return None
 @staticmethod
 def resources(ram,free):
  if ram<RAM_FLOOR:return 'Available RAM below2GiB'
  if free is not None and free<VRAM_FLOOR:return 'Free VRAM below512MiB'
 @staticmethod
 def jobs(counts):return 'Active Student1 processing/VTON job' if any(counts.values()) else None

def discover_backend(pid=None):
 p=psutil.Process(pid if pid is not None else __import__('os').getpid())
 children=p.children(recursive=True)
 return {'pid':p.pid,'created':p.create_time(),'exe':p.exe(),'children':{str(x.pid):x.create_time() for x in children}}

def job_counts():
 with sqlite3.connect(DB.as_uri()+'?mode=ro',uri=True,timeout=.5) as c:
  return {t:c.execute('SELECT COUNT(*) FROM '+t+" WHERE status NOT IN ('completed','failed','cancelled','review_required')").fetchone()[0] for t in ['processing_jobs','visualisations','group_visualisations']}

class Guard:
 def __init__(self,folder,identity,monitor_job=None):
  self.monitor_job=monitor_job
  self.folder=folder;self.identity=identity;self.proc=None;self.gpu=None;self.activity_proc=None;self.stop=threading.Event();self.unsafe=None;self.policy=Policy();self.gpu_last=None;self.activity_last=None;self.jobs_last=None;self.free_gpu=None;self.started=time.monotonic();self.lock=threading.RLock();self.threads=[]
 def abort(self,reason):
  with self.lock:
   if self.unsafe is None:
    self.unsafe={'reason':reason,'time':time.time(),'owned_pid':None if self.proc is None else self.proc.pid}
    if self.proc is not None and self.proc.poll() is None:self.proc.terminate()
    try:(self.folder/'SAFETY_STOP.json').write_text(json.dumps(self.unsafe,indent=2))
    except OSError:pass  # Safety termination must not depend on writable logs.
 def attach(self,proc):
  with self.lock:
   self.proc=proc
   if self.unsafe is not None and proc.poll() is None:proc.terminate()
 def __enter__(self):
  try:return self._start()
  except Exception:
   self.__exit__(None,None,None)
   raise
 def _start(self):
  self.folder.mkdir(exist_ok=True);self.sf=(self.folder/'SYSTEM.jsonl').open('w');self.gf=(self.folder/'GPU.csv').open('w');self.af=(self.folder/'ACTIVITY.jsonl').open('w');self.jf=(self.folder/'JOBS.jsonl').open('w');self.ef=(self.folder/'activity-helper-stderr.log').open('w')
  self.gpu=subprocess.Popen(['nvidia-smi','--query-gpu=timestamp,memory.used,memory.free,utilization.gpu','--format=csv,noheader,nounits','-lms','500'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,creationflags=0x08000000)
  if self.monitor_job is not None:self.monitor_job.attach(self.gpu.pid)
  ids=','.join([str(self.identity['pid']),*self.identity['children']])
  self.activity_proc=subprocess.Popen(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(R/'gpu_activity.ps1'),'-TargetIds',ids],stdout=subprocess.PIPE,stderr=self.ef,text=True,encoding='utf-8-sig',creationflags=0x08000000)
  if self.monitor_job is not None:self.monitor_job.attach(self.activity_proc.pid)
  def gpu():
   for line in self.gpu.stdout:
    if self.stop.is_set():break
    self.gf.write(line);self.gf.flush()
    try:self.free_gpu=int(line.split(',')[2]);self.gpu_last=time.monotonic()
    except (ValueError,IndexError):self.abort('Invalid GPU memory sample')
   if not self.stop.is_set():self.abort('GPU memory monitor ended')
  def activity():
   for line in self.activity_proc.stdout:
    if self.stop.is_set():break
    self.af.write(line);self.af.flush()
    try:
     x=json.loads(line)
     expected={self.identity['pid'],*[int(p) for p in self.identity['children']]}
     valid,pct=measured_activity(x,expected,time.time());reason=self.policy.activity(valid,pct);self.activity_last=time.monotonic()
     if reason:self.abort(reason)
    except Exception as e:self.abort('Cannot decode GPU activity: '+str(e))
   if not self.stop.is_set():self.abort('GPU activity monitor ended')
  def jobs():
   while not self.stop.is_set():
    try:
     # Serialize ownership discovery with the runner's spawn/attach sequence.
     # Only held own worker/monitor subtrees are excluded; new unknown children
     # still invalidate the original activity-coverage snapshot.
     with self.lock:
      p=psutil.Process(self.identity['pid'])
      if p.create_time()!=self.identity['created']:raise RuntimeError('Backend PID identity changed')
      owned={self.gpu.pid,self.activity_proc.pid}
      if self.proc is not None:owned.add(self.proc.pid)
      descendants=p.children(recursive=True)
      for task in descendants:
       if any(parent.pid in owned for parent in task.parents()):owned.add(task.pid)
      current={str(x.pid):x.create_time() for x in descendants if x.pid not in owned}
      if current!=self.identity['children']:raise RuntimeError('Backend process tree changed; activity coverage uncertain')
     counts=job_counts();self.jf.write(json.dumps({'time':time.time(),'counts':counts})+'\n');self.jf.flush();self.jobs_last=time.monotonic();reason=self.policy.jobs(counts)
     if reason:self.abort(reason)
    except Exception as e:self.abort('Cannot establish backend/job state: '+str(e))
    self.stop.wait(1)
  def memory():
   psutil.cpu_percent()
   while not self.stop.is_set():
    m=psutil.virtual_memory();x={'time':time.time(),'ram_available':m.available,'ram_used':m.used,'cpu_percent':psutil.cpu_percent(),'gpu_free_mib':self.free_gpu,'backend_quiet_samples':self.policy.quiet}
    if self.proc is not None:
     try:
      a=psutil.Process(self.proc.pid).memory_info();x.update(rss=a.rss,peak_wset=getattr(a,'peak_wset',None),vms=a.vms)
     except psutil.Error:pass
    self.sf.write(json.dumps(x)+'\n');self.sf.flush();reason=self.policy.resources(m.available,self.free_gpu)
    if reason:self.abort(reason)
    now=time.monotonic()
    for name,last in [('GPU memory',self.gpu_last),('GPU activity',self.activity_last),('job',self.jobs_last)]:
     if (last is None and now-self.started>10) or (last is not None and now-last>STALE):self.abort(name+' measurement unavailable/stale')
    self.stop.wait(.25)
  for fn in [gpu,activity,jobs,memory]:
   t=threading.Thread(target=fn,daemon=True);self.threads.append(t);t.start()
  return self
 def safe(self):
  if self.unsafe:raise RuntimeError('Safety stop: '+self.unsafe['reason'])
  now=time.monotonic()
  if any(x is None or now-x>STALE for x in [self.gpu_last,self.activity_last,self.jobs_last]):raise RuntimeError('Reliable fresh measurements unavailable')
 def preflight(self):
  deadline=time.monotonic()+20
  while time.monotonic()<deadline:
   if self.unsafe:raise RuntimeError('Preflight stop: '+self.unsafe['reason'])
   if self.policy.quiet>=QUIET and all(x is not None for x in [self.gpu_last,self.activity_last,self.jobs_last]):
    self.safe();available=psutil.virtual_memory().available
    if available<8*2**30:raise RuntimeError('Preload available RAM below8GiB; model not started')
    return {'time':time.time(),'available_ram_gib':available/2**30,'gpu_free_mib':self.free_gpu,'consecutive_quiet_activity_samples':self.policy.quiet,'backend_identity':self.identity}
   self.stop.wait(.1)
  raise RuntimeError('Five valid quiet GPU intervals not established within20seconds')
 def __exit__(self,*exc):
  self.stop.set()
  for p in [self.gpu,self.activity_proc]:
   if p is not None and p.poll() is None:p.terminate()
  for p in [self.gpu,self.activity_proc]:
   if p is not None:
    try:p.wait(timeout=10)
    except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
  for t in self.threads:t.join(timeout=5)
  for name in ['sf','gf','af','jf','ef']:
   f=getattr(self,name,None)
   if f is not None:f.close()
