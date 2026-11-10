"""One additive append-only journal, with strict headers and caller-owned transactions."""
from app.domain.value_objects.verified_garment_subtype import decode,encode,validate_event
SQL='CREATE TABLE garment_subtype_events_v1 (\n event_id TEXT PRIMARY KEY,\n user_id TEXT NOT NULL REFERENCES users(id),\n processing_item_id TEXT REFERENCES processing_items(id),\n garment_id TEXT REFERENCES garments(id),\n ordinal INTEGER NOT NULL CHECK(ordinal > 0),\n action_id TEXT NOT NULL,\n prior_revision TEXT,\n revision TEXT NOT NULL,\n created_at TEXT NOT NULL,\n event_json TEXT NOT NULL,\n CHECK ((processing_item_id IS NULL) <> (garment_id IS NULL)),\n UNIQUE(user_id, processing_item_id, ordinal),\n UNIQUE(user_id, garment_id, ordinal),\n UNIQUE(user_id, action_id)\n);'
class SqliteGarmentSubtypeStore:
    @staticmethod
    def initialize(conn):
        row=conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='garment_subtype_events_v1'").fetchone()
        if row:
            if ''.join(row['sql'].split()).rstrip(';')!=''.join(SQL.split()).rstrip(';'):raise ValueError('Unregistered subtype journal schema.')
        else:conn.execute(SQL)
    def _read(self,rows):
        result=[]
        for row in rows:
            event=validate_event(decode(row['event_json']))
            for header,key in [('event_id','event_id'),('user_id','owner_id'),('ordinal','ordinal'),('action_id','action_id'),('prior_revision','prior_revision'),('revision','revision'),('created_at','recorded_at')]:
                if row[header]!=event[key]:raise ValueError('Subtype journal header mismatch.')
            if row['garment_id']!=(event['subject_id'] if event['subject_kind']=='garment' else None) or row['processing_item_id']!=(event['subject_id'] if event['subject_kind']=='processing_item' else None):raise ValueError('Subtype journal subject mismatch.')
            result.append(event)
        return result
    def find_action(self,conn,owner,action_id):
        rows=self._read(conn.execute('SELECT * FROM garment_subtype_events_v1 WHERE user_id=? AND action_id=?',(owner,action_id)).fetchall())
        return rows[0] if rows else None
    def events(self,conn,owner,kind,subject):
        if kind not in ('garment','processing_item'):raise ValueError('Unknown subtype subject kind.')
        column='garment_id' if kind=='garment' else 'processing_item_id'
        return self._read(conn.execute('SELECT * FROM garment_subtype_events_v1 WHERE user_id=? AND '+column+'=? ORDER BY ordinal',(owner,subject)).fetchall())
    def collection(self,conn,owner):
        result={}
        for event in self._read(conn.execute('SELECT * FROM garment_subtype_events_v1 WHERE user_id=? AND garment_id IS NOT NULL ORDER BY garment_id,ordinal',(owner,)).fetchall()):result.setdefault(event['subject_id'],[]).append(event)
        return result
    def append(self,conn,event):
        validate_event(event)
        conn.execute('INSERT INTO garment_subtype_events_v1 (event_id,user_id,processing_item_id,garment_id,ordinal,action_id,prior_revision,revision,created_at,event_json) VALUES (?,?,?,?,?,?,?,?,?,?)',(event['event_id'],event['owner_id'],event['subject_id'] if event['subject_kind']=='processing_item' else None,event['subject_id'] if event['subject_kind']=='garment' else None,event['ordinal'],event['action_id'],event['prior_revision'],event['revision'],event['recorded_at'],encode(event)))
