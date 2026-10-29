"""Finite expression/qualifier composition with lossless spans and residual checks."""
import re
from app.application.nlp.general_context_interpreter import phrase_pattern
from app.application.nlp.request_field_extractor import UnsupportedMeaning
from app.domain.value_objects.general_context_request import ContextSlot,SourceSpan,GeneralContext,GeneralContextRequest
from app.domain.value_objects.nlp_result import NLPOutcome


def interpret_expanded(parser,original):
    if not isinstance(original,str) or not original.strip() or len(original)>500:return parser.legacy.interpret(original)
    text=original.lower().replace('\u2019',"'").replace('\u2018',"'").replace('é','e')
    text=re.sub('[-_\u2010-\u2014]',' ',text)
    if len(text)!=len(original):return NLPOutcome('UnsupportedRequest','unsupported_text_encoding','This text cannot be represented safely.',original)
    try:
        if re.search(r"\b(?:no|not|without|avoid|excluding|except|don't|never)\b",text):raise UnsupportedMeaning('negation')
        if re.search(r'\b(?:or|either|instead)\b',text):raise UnsupportedMeaning('alternatives')
        grammar=parser.grammar
        situations={s.identifier:s for s in parser.situations}
        expressions={e['situation']:e for e in grammar['expressions']}
        events=[]
        for sid,situation in situations.items():
            phrases=expressions[sid]['anchors'] if sid in expressions else situation.phrases
            if sid=='everyday.casual_outing':phrases=(*phrases,'hanging out with friends','hanging out with my friends')
            for phrase in phrases:
                events.extend((m,situation) for m in re.finditer(phrase_pattern(phrase),text))
        refinements={('interview.unspecified','professional.job_interview'),('presentation.unspecified','academic.presentation'),('everyday.academic_attendance','academic.presentation'),('professional.office_day','professional.workplace_meeting'),('professional.workplace_meeting','academic.group_study'),('academic.group_study','academic.library_study'),('professional.workplace_meeting','everyday.casual_outing')}
        events=[(m,s) for m,s in events if not any(o.start()<=m.start() and m.end()<=o.end() and ((s.identifier,t.identifier) in refinements or s.identifier==t.identifier and (o.start(),o.end())!=(m.start(),m.end())) for o,t in events)]
        # The retained meal companion frame is not another outing or work meeting.
        events=[(m,s) for m,s in events if not (
            s.identifier=='everyday.casual_outing' and m.group()=='meeting friends'
            and any(t.identifier=='social.meal' and re.fullmatch(r'\s+for\s+(?:a\s+)?',text[m.end():other.start()]) for other,t in events))]
        if any(s.identifier=='academic.group_study' for _,s in events) and re.search(r'\bmeeting (?:my )?classmates for (?:a )?study session\b',text):
            events=[(m,s) for m,s in events if not (s.identifier=='professional.workplace_meeting' and m.group()=='meeting')]
        if any(s.identifier=='social.cafe_meetup' for _,s in events) and re.search(r'\b(?:someone|friend|friends|family)\b',text):
            events=[(m,s) for m,s in events if not (s.identifier=='professional.workplace_meeting' and m.group()=='meeting')]
        if any(s.identifier=='professional.workplace_meeting' for _,s in events) and re.search(r'\b(?:university|campus)\b',text) and not re.search(r'\b(?:colleagues|workplace|office|company)\b',text):raise UnsupportedMeaning('context_clarification_required')
        venues=[]
        for venue in grammar['venues']:
            if venue=='friend_home':continue
            venues.extend((m,venue) for m in re.finditer(r'\b(?:at|in|to|around|on) (?:a |the )?'+phrase_pattern(venue),text))
        # A licensed venue is context, not another event. Other words remain.
        events=[(m,s) for m,s in events if not (s.identifier in ('everyday.academic_attendance','professional.office_day','social.cafe_meetup','leisure.cinema_outing') and any(v.start()<=m.start() and m.end()<=v.end() for v,_ in venues) and len(events)>1)]
        if any(s.identifier=='social.cafe_meetup' for _,s in events):
            events=[(m,s) for m,s in events if not (s.identifier=='everyday.casual_outing' and m.group()=='meeting friends')]
        if not events:
            if re.search(r'\b(?:meeting|project meeting|going to work|sightseeing|library)\b',text):raise UnsupportedMeaning('context_clarification_required')
            return parser.legacy.interpret(original)
        for m,s in events:
            expression=expressions.get(s.identifier)
            if expression and expression['required_any'] and not any(re.search(phrase_pattern(word),text) for word in expression['required_any']):raise UnsupportedMeaning('context_clarification_required')
        facet_observations=[]
        ids={s.identifier for _,s in events}
        if ids=={'social.date','social.meal'} and 'dinner_date' in grammar['compounds'] and re.search(r'\bdinner\s+date\b|\bdate\s+(?:for|over)\s+dinner\b',text):
            facet_observations=[(m,'meal:dinner') for m,s in events if s.identifier=='social.meal']
            events=[(m,s) for m,s in events if s.identifier=='social.date']
        elif ids=={'social.meal','social.birthday_gathering'} and 'birthday_dinner' in grammar['compounds'] and re.search(r'\bbirthday\s+dinner\b',text):
            facet_observations=[(m,'celebration:birthday') for m,s in events if s.identifier=='social.birthday_gathering']
            events=[(m,s) for m,s in events if s.identifier=='social.meal']
        if len(events)!=1:raise UnsupportedMeaning('multiple_requests')
        event,situation=events[0]
        work=list(text);slots={}
        def consume(match):work[match.start():match.end()]=' '*(match.end()-match.start())
        def slot(name,observations):
            if not observations:return
            values=tuple(dict.fromkeys(value for _,value in observations))
            slots[name]=ContextSlot('Known' if len(values)==1 or name in ('facets','soft_preferences','goals') else 'Conflicting',values,tuple(SourceSpan(m.start(),m.end(),original[m.start():m.end()]) for m,_ in observations))
            for m,_ in observations:consume(m)
        prefix=re.match(r"\s*(?:please\s+)?(?:(?:i'm|im|i am)\s+(?:going(?:\s+(?:out\s+for|to|on))?|attending|meeting|having|studying|working|visiting|watching|seeing|taking|sightseeing|hanging\s+out|presenting|being(?=\s+interviewed)|conducting|interviewing|in the audience)|i\s+(?:have|want|will|need\s+to\s+go)|what\s+(?:should|can)\s+i\s+wear)\b",text)
        if prefix:consume(prefix)
        elif not parser.legacy.classifier.classify(text):raise UnsupportedMeaning('unsupported_intent')
        if re.search(r'\b(?:buy|delete|archive|password|instructions|explain|define|translate)\b',text):raise UnsupportedMeaning('unsupported_intent')
        slot('situation',[(event,situation.identifier)])
        if situation.activity:slots['activity']=ContextSlot('Known',(situation.activity,),slots['situation'].spans)
        if situation.venue:slots['venue']=ContextSlot('Known',(situation.venue,),slots['situation'].spans)
        # A venue named inside a compound expression is still explicitly stated.
        # Recreate absolute offsets for embedded lexical spans.
        for venue in grammar['venues']:
            if venue=='friend_home':continue
            for m in re.finditer(phrase_pattern(venue),text):
                if event.start()<=m.start() and m.end()<=event.end():venues.append((m,venue))
        house=[(m,'friend_home') for m in re.finditer(r"\bfriend(?:'s|s') (?:house|place)\b",text)]
        venues.extend(house)
        old=slots.get('venue');slot('venue',venues)
        if old and venues and old.value not in slots['venue'].values:slots['venue']=ContextSlot('Conflicting',(*old.values,*slots['venue'].values),(*old.spans,*slots['venue'].spans))
        roles=[(m,m.group(1)) for m in re.finditer(r'\bas (?:a|an|the) ('+'|'.join(map(re.escape,grammar['roles']))+r')\b',text)]
        if situation.identifier in ('professional.job_interview','interview.unspecified','academic.presentation','presentation.unspecified'):
            for pattern,role in ((r'\bbeing interviewed\b','candidate'),(r'\bconducting\b','interviewer'),(r'\bpresenting\b','presenter'),(r'\bin the audience\b','attendee')):roles.extend((m,role) for m in re.finditer(pattern,text))
        slot('role',roles)
        if len(roles)>1:raise UnsupportedMeaning('conflicting_role')
        codes=[]
        choices='|'.join(phrase_pattern(p) for p in grammar['dress_codes'])
        for pattern in (r'\b(?:the )?dress code is ('+choices+r')',r'('+choices+r')\s+(?='+phrase_pattern(event.group())+r')'):
            codes.extend((m,grammar['dress_codes'][re.sub(r'\s+',' ',m.group(1))]) for m in re.finditer(pattern,text))
        slot('dress_code',codes)
        if len({v for _,v in codes})>1:raise UnsupportedMeaning('conflicting_formality')
        slot('temporal',[(m,word) for word in grammar['temporal'] for m in re.finditer(phrase_pattern(word),text)])
        if slots.get('temporal',ContextSlot()).state=='Conflicting':raise UnsupportedMeaning('conflicting_time')
        companions=[]
        for word,value in (('friends','friends'),('friend','friends'),('family','family'),('colleagues','colleagues'),('classmates','classmates'),('someone','someone')):
            companions.extend((m,value) for m in re.finditer(phrase_pattern(word),text))
        if house:companions.extend((m,'friends') for m,_ in house)
        slot('companions',companions)
        if situation.identifier=='travel.journey':
            transports=[(m,'transport:'+m.group(1)) for m in re.finditer(r'\b(?:a |the )?(train|bus|flight)\b',text)]
            facet_observations.extend(transports)
        slot('facets',facet_observations)
        slot('goals',[(m,goal) for goal in grammar['goals'] for m in re.finditer(phrase_pattern(goal),text)])
        soft=[]
        for field,value,phrase,_ in parser.vocabulary.entries:
            if field in ('style','colours'):soft.extend((m,field+':'+value) for m in re.finditer(r'\bprefer\s+'+phrase_pattern(phrase),text))
        slot('soft_preferences',soft)
        if situation.identifier=='presentation.unspecified' and slots.get('venue',ContextSlot()).value=='university':
            situation=situations['academic.presentation'];slots['situation']=ContextSlot('Known',(situation.identifier,),(*slots['situation'].spans,*slots['venue'].spans))
        matches=parser.extractor.extract(''.join(work));fields=parser.mapper.map_values(matches)
        if fields['occasion']:raise UnsupportedMeaning('conflicting_occasion')
        for field,name in (('style','style'),('colours','colours'),('garment_categories','categories'),('formality','formality')):
            found=[m for m in matches if m.field==field]
            if found:slots[name]=ContextSlot('Known',tuple(dict.fromkeys((m.kind+':' if m.kind else '')+m.canonical_value for m in found)),tuple(SourceSpan(m.start,m.end,original[m.start:m.end]) for m in found))
        code=slots.get('dress_code',ContextSlot()).value;formality=next(iter(fields['formality']),None)
        if code is not None and formality is not None and code!=formality:raise UnsupportedMeaning('conflicting_formality')
        frame=GeneralContext(original,**slots,grammar_sha256=parser.grammar_hash,taxonomy_sha256=parser.taxonomy_hash,version='general-context-1.1.0',bundle_id=parser.bundle_id)
        request=GeneralContextRequest(occasion=situation.projection_occasion,style=next(iter(fields['style']),None),colours=fields['colours'] or None,garment_categories=fields['garment_categories'] or None,formality=code if code is not None else formality,context=frame)
        return NLPOutcome('Supported','context_interpreted','Situation understood; policy availability is checked separately.',original,request,matches)
    except UnsupportedMeaning as error:
        return NLPOutcome('UnsupportedRequest',error.reason,'Specify one ordinary supported situation and retain its meaningful requirements.',original)
