"""J19 lifecycle observation only; untouched app.main composition and routes."""
import argparse
import asyncio
import faulthandler
import json
from pathlib import Path
import sys
import uvicorn

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
parser=argparse.ArgumentParser();parser.add_argument('--stop-file',required=True);parser.add_argument('--diagnostics',required=True);parser.add_argument('--port',type=int,default=3101)
args=parser.parse_args();folder=Path(args.diagnostics);folder.mkdir(parents=True,exist_ok=True)
server=uvicorn.Server(uvicorn.Config('app.main:app',host='127.0.0.1',port=args.port,access_log=False))
def capture(label):
    tasks=[]
    for task in asyncio.all_tasks():
        tasks.append({'name':task.get_name(),'coroutine':getattr(task.get_coro(),'__qualname__',type(task.get_coro()).__name__),
            'done':task.done(),'frames':[{'file':str(Path(frame.f_code.co_filename)),'line':frame.f_lineno,'function':frame.f_code.co_name} for frame in task.get_stack(limit=4)]})
    (folder/(label+'.json')).write_text(json.dumps({'asyncio_tasks':tasks,'uvicorn_connections':len(server.server_state.connections),'uvicorn_request_tasks':len(server.server_state.tasks)},indent=2)+'\n',encoding='utf-8')
async def watch():
    while not Path(args.stop_file).exists():await asyncio.sleep(.1)
    capture('before-graceful-stop');server.should_exit=True
    await asyncio.sleep(25);capture('still-pending-after-25s')
async def main():
    watcher=asyncio.create_task(watch(),name='J19-lifecycle-stop-observer')
    try:await server.serve()
    finally:
        watcher.cancel();await asyncio.gather(watcher,return_exceptions=True)
asyncio.run(main())
