"""Bounded owned reads of the separate garment continuation receipt namespace."""
import json
from app.domain.value_objects.garment_only_refinement import KEY,step_key
from app.domain.value_objects.recommendation_refinement import canonical_uuid
from app.infrastructure.persistence.refinement_lineage_query import SELECT_RECORD

def read_record(conn,user,identifier):
    canonical_uuid(identifier)
    row=conn.execute(SELECT_RECORD,(user,identifier)).fetchone()
    if row is None:raise LookupError('Recommendation not found.')
    result=dict(row)
    if len(result['provenance_json'].encode())>1048576 or len(result['score_json'].encode())>262144 or len(result['extracted_entities_json'].encode())>65536:raise ValueError('Oversized garment lineage record.')
    result['items']=[{**json.loads(r['display_json']),'garment_id':r['garment_id'],'garment_role':r['garment_role'],'item_order':r['item_order']} for r in conn.execute('SELECT i.*,s.display_json FROM recommendation_items i JOIN recommendation_item_snapshots s USING(recommendation_id,garment_id) WHERE i.recommendation_id=? ORDER BY i.item_order',(identifier,))]
    return result

def read_chain(conn,user,parent_id):
    parent=read_record(conn,user,parent_id)
    proof=json.loads(parent['provenance_json']).get(KEY)
    if type(proof) is not dict:return parent,()
    root=canonical_uuid(proof.get('root_id'));records=[parent if root==parent_id else read_record(conn,user,root)]
    keys=tuple(step_key(root,n) for n in range(1,10))
    rows=conn.execute("SELECT submission_key,recommendation_id FROM recommendation_submissions WHERE user_id=? AND operation='assistant' AND submission_key IN (?,?,?,?,?,?,?,?,?)",(user,*keys)).fetchall()
    children={r['submission_key']:r['recommendation_id'] for r in rows}
    for key in keys:
        if key in children:
            child=read_record(conn,user,children[key]);child['submission_key']=key;records.append(child)
    return parent,tuple(records)
