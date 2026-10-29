"""No NLP, ranking, wardrobe writes or action authorization in history reads."""
from app.application.recommendation.scoring_display import with_scoring_display


class ChatHistoryService:
    def __init__(self,query):
        self.query = query

    def search(self,user_id,search='',limit=50,cursor=None):
        if not isinstance(search,str) or len(search)>500 or isinstance(limit,bool) or not isinstance(limit,int) or not 1<=limit<=100:
            raise ValueError('Invalid history search/page size.')
        if cursor is not None and (not isinstance(cursor,str) or not cursor or len(cursor)>4096):
            raise ValueError('Invalid history cursor.')
        return self.query.search(user_id,search,limit,cursor)

    def get(self,user_id,chat_id):
        if not isinstance(chat_id,str) or not chat_id or len(chat_id)>200:
            raise LookupError('Completed chat not found.')
        result = self.query.get(user_id,chat_id)
        return {**result,"recommendation":with_scoring_display(result["recommendation"])}
