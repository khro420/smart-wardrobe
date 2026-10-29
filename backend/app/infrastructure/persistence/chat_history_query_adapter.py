"""SQLite read-only history; reuse Phase 5A restoration on the same read snapshot."""
import base64
from contextlib import contextmanager
import hashlib
import hmac
import json
from pathlib import Path
import sqlite3
from app.infrastructure.config import DATABASE_PATH
from app.infrastructure.security import TOKEN_SECRET
from app.infrastructure.persistence.recommendation_repository_adapter import SqliteRecommendationRepository


ELIGIBLE = """
FROM nlp_chats c JOIN recommendations r ON r.chat_id=c.id AND r.user_id=c.user_id
WHERE c.user_id=? AND c.status='completed' AND c.completed_at IS NOT NULL
AND c.profile_id=? AND r.profile_id=c.profile_id
AND length(trim(c.request_text, char(9)||char(10)||char(13)||' '))>0
AND r.status IN ('available','saved') AND r.recommendation_type IN ('assistant','wardrobe_outfit')
AND EXISTS(SELECT 1 FROM recommendation_items i WHERE i.recommendation_id=r.id)
AND NOT EXISTS(SELECT 1 FROM recommendations other WHERE other.chat_id=c.id AND other.id<>r.id)
"""


class SqliteChatHistoryQuery:
    def __init__(self,database_path=DATABASE_PATH,cursor_secret=TOKEN_SECRET):
        self.database_path = Path(database_path)
        self.cursor_secret = cursor_secret.encode()
        self.reader = SqliteRecommendationRepository(database_path)

    @contextmanager
    def _connection(self,user_id):
        conn = sqlite3.connect(self.database_path.resolve().as_uri()+'?mode=ro',uri=True)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute('PRAGMA query_only=ON')
            conn.create_function('history_casefold',1,lambda text:text.casefold() if isinstance(text,str) else '',deterministic=True)
            conn.execute('BEGIN')
            if not conn.execute("SELECT 1 FROM users WHERE id=? AND account_status='active'",(user_id,)).fetchone():
                raise LookupError('Completed chat not found.')
            yield conn
        finally:
            conn.rollback()
            conn.close()

    def _binding(self,user_id,profile_id,search):
        return hashlib.sha256(json.dumps([user_id,profile_id,search],ensure_ascii=True).encode()).hexdigest()

    def _encode_cursor(self,value):
        payload = base64.urlsafe_b64encode(json.dumps(value,separators=(',',':')).encode()).decode()
        signature = hmac.new(self.cursor_secret,payload.encode(),hashlib.sha256).hexdigest()
        return payload+'.'+signature

    def _decode_cursor(self,cursor,binding):
        try:
            payload,signature = cursor.split('.')
            expected = hmac.new(self.cursor_secret,payload.encode(),hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature,expected): raise ValueError()
            value = json.loads(base64.urlsafe_b64decode(payload))
            if (value.get('v')!=1 or value.get('binding')!=binding
                    or any(not isinstance(value.get(k),list) or len(value[k])!=2 or any(not isinstance(x,str) for x in value[k]) for k in ('anchor','after'))):
                raise ValueError()
            return value
        except Exception:
            raise ValueError('Invalid history cursor.') from None

    def search(self,user_id,search='',limit=50,cursor=None,profile_id=None):
        if not profile_id: raise LookupError('Completed chat not found.')
        binding = self._binding(user_id,profile_id,search)
        position = self._decode_cursor(cursor,binding) if cursor else None
        escaped = search.casefold().replace('!','!!').replace('%','!%').replace('_','!_')
        sql,params = ELIGIBLE+" AND history_casefold(c.request_text) LIKE ? ESCAPE '!'",[user_id,profile_id,'%'+escaped+'%']
        with self._connection(user_id) as conn:
            if position:
                date,identifier = position['anchor']
                sql += ' AND (c.created_at<? OR (c.created_at=? AND c.id>=?))'
                params += [date,date,identifier]
            total = conn.execute('SELECT count(*) '+sql,params).fetchone()[0]
            if position:
                date,identifier = position['after']
                sql += ' AND (c.created_at<? OR (c.created_at=? AND c.id>?))'
                params += [date,date,identifier]
            rows = conn.execute("SELECT c.id AS chat_id,c.request_text,c.created_at,c.completed_at,r.id AS recommendation_id,r.status AS recommendation_status "+sql+' ORDER BY c.created_at DESC,c.id ASC LIMIT ?',(*params,limit+1)).fetchall()
            page,more = rows[:limit],len(rows)>limit
            items = [{**dict(row),'read_only':True} for row in page]
            next_cursor = None
            if more:
                next_cursor = self._encode_cursor({'v':1,'binding':binding,'anchor':position['anchor'] if position else [page[0]['created_at'],page[0]['chat_id']],
                    'after':[page[-1]['created_at'],page[-1]['chat_id']]})
            return {'status':'CompletedChats' if items else 'NoResults','items':items,'total':total,'limit':limit,'next_cursor':next_cursor,'read_only':True}

    def get(self,user_id,chat_id,profile_id=None):
        if not profile_id: raise LookupError('Completed chat not found.')
        with self._connection(user_id) as conn:
            row = conn.execute('SELECT c.*,r.id AS recommendation_id '+ELIGIBLE+' AND c.id=?',(user_id,profile_id,chat_id)).fetchone()
            if row is None: raise LookupError('Completed chat not found.')
            # Protected helper reuse is internal to persistence, never a writer
            # call: the supplied connection is query_only and mode=ro.
            try:
                recommendation = self.reader._read(conn,user_id,row['recommendation_id'])
            except (ValueError,TypeError):
                raise RuntimeError('Stored history evidence could not be restored.') from None
            for item in recommendation['items']:
                media = item.get('preferred_media_id')
                accessible = bool(media and conn.execute("SELECT 1 FROM media_assets WHERE id=? AND user_id=? AND status='available'",(media,user_id)).fetchone())
                item['historical_media_accessible'] = accessible
                if not accessible: item['preferred_media_id'] = None
            try:
                entities = json.loads(row['extracted_entities_json']) if row['extracted_entities_json'] is not None else None
                interpretation_state = 'Available' if isinstance(entities,dict) else 'MissingOrUnsupported'
            except (ValueError,TypeError):
                entities,interpretation_state = None,'Malformed'
            fields = {'intent','occasion','style','colours','garment_categories','formality'}
            structured = entities if isinstance(entities,dict) and fields <= entities.keys() and entities.get('intent')=='outfit_recommendation' else None
            return {'status':'CompletedChat','chat_id':row['id'],'request_text':row['request_text'],
                'interpreted_intent':row['interpreted_intent'],'interpreted_entities':entities,'structured_request':structured,
                'interpretation_state':interpretation_state,'created_at':row['created_at'],'completed_at':row['completed_at'],
                'read_only':True,'requires_action_revalidation':True,'recommendation':recommendation}
