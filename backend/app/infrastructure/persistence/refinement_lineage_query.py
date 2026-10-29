"""Bounded owner-scoped SELECTs on existing recommendation and receipt indexes."""
import json
from app.domain.value_objects.recommendation_refinement import canonical_uuid,step_key

SELECT_RECORD='''SELECT r.id,r.user_id,c.request_text,c.extracted_entities_json,
    m.provenance_json,m.score_json FROM recommendations r
    JOIN nlp_chats c ON c.id=r.chat_id AND c.user_id=r.user_id
    JOIN recommendation_metadata m ON m.recommendation_id=r.id
    WHERE r.user_id=? AND r.id=? AND r.recommendation_type='assistant' '''


def read_record(conn,user,identifier):
    canonical_uuid(identifier)
    row=conn.execute(SELECT_RECORD,(user,identifier)).fetchone()
    if row is None:raise LookupError('Recommendation not found.')
    return bounded_record(dict(row))


def bounded_record(row):
    if len(row['provenance_json'].encode())>327680 or len(row['score_json'].encode())>262144:
        raise ValueError('Oversized stored lineage record.')
    return row


def read_chain(conn,user,parent_id):
    parent=read_record(conn,user,parent_id)
    proof=json.loads(parent['provenance_json']).get('refinement')
    if not isinstance(proof,dict):return parent,()
    root_id=canonical_uuid(proof.get('root_id'))
    root=parent if root_id==parent_id else read_record(conn,user,root_id)
    keys=tuple(step_key(root_id,n) for n in range(1,10))
    rows=conn.execute('''SELECT s.submission_key,r.id,r.user_id,c.request_text,c.extracted_entities_json,
        CASE WHEN r.id=? THEN NULL ELSE m.provenance_json END AS provenance_json,
        CASE WHEN r.id=? THEN NULL ELSE m.score_json END AS score_json FROM recommendation_submissions s
        JOIN recommendations r ON r.id=s.recommendation_id AND r.user_id=s.user_id
        JOIN nlp_chats c ON c.id=r.chat_id AND c.user_id=s.user_id
        JOIN recommendation_metadata m ON m.recommendation_id=r.id
        WHERE s.user_id=? AND s.operation='assistant' AND s.submission_key IN (?,?,?,?,?,?,?,?,?)''',
        (parent_id,parent_id,user,*keys)).fetchall()
    # The parent was already read to discover the root. Keep its receipt/index
    # validation here, but do not transfer its bounded payload a second time.
    children={row['submission_key']:(dict(parent,submission_key=row['submission_key'])
        if row['id']==parent_id else bounded_record(dict(row))) for row in rows}
    return parent,(root,*(children[key] for key in keys if key in children))
