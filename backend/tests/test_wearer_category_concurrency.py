"""Interleave actual source/details writes between selection and commit."""
import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from tests.test_wearer_category_policy import category_api,language_api,palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,set_gender
from tests.test_wearer_category_recommendation import submit
from app.application.ports.assistant_runtime import assistant_service
from app.infrastructure.persistence import postgresql_repository as db

def receipt_counts():
    with db.connection() as conn:return tuple(conn.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('recommendations','recommendation_metadata','recommendation_submissions','nlp_chats'))

@pytest.mark.parametrize('mutation',['gender','gender_round_trip','denied_unselected_source','archival','category'])
def test_changed_scope_refuses_atomic_commit(category_api,monkeypatch,mutation):
    client,male,_=category_api;service=assistant_service();original=service.repository.persist_assistant
    before=receipt_counts()
    def change():
        if mutation.startswith('gender'):
            set_gender(client,male,'female')
            if mutation=='gender_round_trip':set_gender(client,male,'male')
        else:
            with db.connection() as conn:
                conn.execute('BEGIN IMMEDIATE')
                row=conn.execute("SELECT * FROM garments WHERE category LIKE '%dress' LIMIT 1").fetchone()
                if mutation=='archival':conn.execute("UPDATE garments SET status='archived' WHERE id=?",(row['id'],))
                elif mutation=='category':conn.execute("UPDATE garments SET category='skirt' WHERE id=?",(row['id'],))
                else:
                    attrs=json.loads(row['attributes_json']);attrs['race_marker']='changed excluded source'
                    conn.execute('UPDATE garments SET attributes_json=? WHERE id=?',(json.dumps(attrs),row['id']))
    def interleaved(command):
        with ThreadPoolExecutor(max_workers=1) as workers:workers.submit(change).result(timeout=20)
        return original(command)
    monkeypatch.setattr(service.repository,'persist_assistant',interleaved)
    result=submit(client,male)
    assert result.status_code==409 and result.json()['outcome']=='WearerEligibilityChanged',result.text
    assert receipt_counts()==before

def test_same_parent_children_coalesce(category_api):
    client,male,_=category_api;root=submit(client,male);assert root.status_code==201,root.text
    root=root.json();action=root['scoring_display']['refinement']['next_action'];assert action
    def run():return submit(client,male,root['request_text'],submission_key=action['submission_key'],refinement=action['refinement'])
    with ThreadPoolExecutor(max_workers=2) as workers:results=list(workers.map(lambda _:run(),range(2)))
    assert sorted(r.status_code for r in results)==[200,201],[(r.status_code,r.text) for r in results]
    assert results[0].json()['id']==results[1].json()['id']
