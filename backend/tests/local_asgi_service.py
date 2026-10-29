"""Local process runner for untouched app.main:app with graceful supervisor stop.

No routes, adapters, services, profiles or environment selections are replaced.
The stop file controls process lifecycle only, like a service-manager stop signal.
"""
import argparse
from pathlib import Path
import sys
import threading
import time
import uvicorn

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

parser=argparse.ArgumentParser()
parser.add_argument('--stop-file',required=True)
parser.add_argument('--port',type=int,default=3101)
args=parser.parse_args()
server=uvicorn.Server(uvicorn.Config('app.main:app',host='127.0.0.1',port=args.port,access_log=False))
def watch():
    while not server.should_exit:
        if Path(args.stop_file).exists():
            server.should_exit=True
            return
        time.sleep(.1)
threading.Thread(target=watch,daemon=True).start()
server.run()
