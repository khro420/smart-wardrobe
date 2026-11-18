"""Pure frozen-base parsing subprocess: no app startup, DB, models or API calls."""
import json,sys
from app.application.nlp.request_local_soft_parser import IsolatedSoftPreferenceParser,isolated_fingerprint
from app.application.nlp.conversational_context_interpreter import fingerprint

def run():
    if fingerprint()!='e869b32876d3335781a8b10c7b13a6b2905402ce021aca5db6a6413bde53b0ae' or isolated_fingerprint()!='899f67e37b3a39a24cfb766ea0384c42e42ff69701a84ba14597d6fd59eb4b67':
        raise ValueError('Unregistered frozen base source.')
    value=json.loads(sys.stdin.read(4096))
    if set(value)!={'text'}:raise ValueError('Closed worker input required.')
    try:
        p=IsolatedSoftPreferenceParser().interpret(value['text'])
        return {'request':p.mandatory_request.to_dict(),'hard':p.hard_intent.to_dict() if p.hard_intent else None,'local':p.local_intent.to_dict() if p.local_intent else None}
    except ValueError as error:
        code=getattr(error,'status',getattr(error,'code',None))
        if code is None:raise
        return {'error':code,'reason':error.reason}

if __name__=='__main__':print(json.dumps(run()))
