"""Synthetic history query/API timings; no NLP or recommendation generation."""
import argparse
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys
import tempfile
from time import perf_counter

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))
from fastapi.testclient import TestClient
from app.main import app
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.persistence.chat_history_query_adapter import SqliteChatHistoryQuery
from app.application.chat_history.chat_history_service import ChatHistoryService
from app.application.ports.chat_history_runtime import chat_history_service
from app.infrastructure.security import issue_access_token


def seed(size):
    with db.connection() as c:
        for user in ('benchmark','other'):
            c.execute("INSERT INTO users VALUES(?,?,'','Synthetic','active','now','now')",(user,user+'@test'))
            for index in range(size):
                identifier = f'{user}-{index:08d}'
                timestamp = (datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(seconds=index)).isoformat()
                text = f'Campus CAFÉ vintage 100% cotton_look {index}' if index%10==0 else f'Work outfit request {index}'
                # Synthetic completed legacy fixtures; no model/quality claim.
                c.execute("INSERT INTO nlp_chats VALUES(?,?,?,'outfit_recommendation','{\"keywords\":[]}','completed',?,?)",(identifier,user,text,timestamp,timestamp))
                c.execute("INSERT INTO recommendations(id,user_id,chat_id,recommendation_type,status,created_at) VALUES(?,?,?,'wardrobe_outfit','available','now')",(identifier,user,identifier))
                c.execute("INSERT INTO recommendation_items VALUES(?,?,'one_piece',1,'now')",(identifier,user+'-garment'))
        for user in ('benchmark','other'):
            c.execute("INSERT INTO garments(id,user_id,preferred_media_id,name,category,attributes_json,created_at,updated_at) VALUES(?,?,'synthetic-media','Historical dress','vest_dress','{}','now','now')",(user+'-garment',user))


def run(sizes,repeats):
    records = []
    previous = db.DATABASE_PATH
    try:
        with tempfile.TemporaryDirectory(prefix='history-benchmark-') as directory:
            for size in sizes:
                db.DATABASE_PATH = Path(directory)/f'{size}.db'
                db.initialise_database()
                seed(size)
                query = SqliteChatHistoryQuery(db.DATABASE_PATH,cursor_secret='synthetic-benchmark-key')
                service = ChatHistoryService(query)
                with TestClient(app) as client:
                    app.dependency_overrides[chat_history_service] = lambda:service
                    try:
                        for term,expected in [('',size),('CAMPUS',size//10),('%',size//10),('_',size//10),('café',size//10),('no-match',0)]:
                            direct,api = [],[]
                            for _ in range(repeats):
                                start = perf_counter()
                                page = query.search('benchmark',term,50)
                                direct.append(perf_counter()-start)
                                assert page['total'] == expected
                                start = perf_counter()
                                response = client.get('/api/v1/chats',headers={'Authorization':'Bearer '+issue_access_token('benchmark')},params={'search':term,'limit':50})
                                api.append(perf_counter()-start)
                                assert response.status_code==200 and response.json()['total']==expected
                            record = {'personal_chats':size,'other_user_chats':size,'search':term,'matches':expected,'page_size':50,
                                      'query_boundary_trials_seconds':direct,'api_trials_seconds':api,
                                      'median_query_boundary_seconds':statistics.median(direct),'median_api_seconds':statistics.median(api)}
                            records.append(record)
                            print(json.dumps(record),flush=True)
                    finally: app.dependency_overrides.pop(chat_history_service,None)
    finally: db.DATABASE_PATH = previous
    sources = [Path(__file__),BACKEND/'app/infrastructure/persistence/chat_history_query_adapter.py']
    return {'python':platform.python_version(),'platform':platform.platform(),'processor':platform.processor(),
        'method':'Synthetic legacy histories, equal unrelated-user population, 3 reads per query by default, 50-item page. Query-boundary timing includes connection/SQL/count/pagination; API timing additionally includes bearer auth and TestClient serialization/transport. Seed/migration/startup and browser/network excluded. Requested sizes are representative, not an approved maximum-workload definition or formal NFR-03 compliance.',
        'source_sha256':{str(p.relative_to(BACKEND)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},'records':records}


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sizes',type=int,nargs='+',default=[1000,10000])
    parser.add_argument('--repeats',type=int,default=3)
    parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    if min(args.sizes)<10 or any(n%10 for n in args.sizes) or len(set(args.sizes))!=len(args.sizes) or args.repeats<1:
        parser.error('Use unique positive sizes divisible by ten and positive repeats.')
    result = run(args.sizes,args.repeats)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
