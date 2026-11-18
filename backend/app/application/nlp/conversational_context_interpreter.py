"""Opt-in finite conversational lexicon; original context policies stay authoritative."""
from dataclasses import replace
from pathlib import Path
import hashlib,json,re
from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
from app.application.nlp.request_field_extractor import UnsupportedMeaning
from app.domain.value_objects.nlp_result import NLPOutcome
from app.domain.value_objects.general_context_request import ContextSlot,SourceSpan,GeneralContext,GeneralContextRequest
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from app.shared_contracts.grammar_identity import canonical_bytes

PROFILE='conversational_language_v1'
RESOURCE_SHA256='58686ffab49c60b82de14fb76f681e3d80cbc994774ead1859055ac3aa7c2a15'
RESOURCE=Path(__file__).with_name('config')/'conversational_language.v1.json'

# A shopping-purpose description is not a purchase command. Only this complete
# finite frame licenses "buy"; all residual requirements still reach extraction.
SHOPPING_DESCRIPTION = (r"\b(?:i'm|i\s+am|we're|we\s+are)\s+(?:heading|going)\s+to\s+"
                        r"(?:the\s+)?(?:mall|shops)\s+to\s+buy\s+(?:a\s+few|some)\s+(?:things|items)\b")


def requested_formality_spans(original):
    """Explicit whole-outfit appearance scope, not a garment's style label."""
    value = r'(smart\s+casual|casual|formal|black\s+tie)'
    context = r'(?=\s+for\s+(?:(?:my|a|the)\s+)?(?:job\s+interview|university\s+presentation)\b)'
    frames = (r"\b(?:i\s+(?:need|want)|suggest|recommend)\s+(?:something|(?:an?\s+)?outfit)\s+" + value + context,
              r"\b(?:i\s+(?:need|want)|suggest|recommend)\s+(?:an?\s+)?" + value + r'\s+outfit' + context)
    return tuple((m.start(1),m.end(1),re.sub(r'\s+',' ',m.group(1).lower()).replace(' ','_'))
                 for pattern in frames for m in re.finditer(pattern,outside_literals(original),re.I))

def load_language(path=RESOURCE):
    with Path(path).open('rb') as stream:raw=stream.read(65537)
    if len(raw)>65536:raise ValueError('Unregistered conversational language resource.')
    raw=canonical_bytes(raw)
    if hashlib.sha256(raw).hexdigest()!=RESOURCE_SHA256:raise ValueError('Unregistered conversational language resource.')
    def pairs(items):
        result={}
        for k,v in items:
            if k in result:raise ValueError('Duplicate language resource key.')
            result[k]=v
        return result
    data=json.loads(raw,object_pairs_hook=pairs)
    if data['profile']!=PROFILE or data['base_bundle']!='context_18_v1' or len(data['contexts'])!=18:raise ValueError('Invalid conversational language contract.')
    return data

def fingerprint():
    from app.shared_contracts import grammar_identity
    from app.application.nlp import conversational_attribute_forms
    paths=[Path(__file__),Path(__file__).with_name('conversational_attribute_interpreter.py'),Path(__file__).parents[1]/'recommendation/conversational_request_pipeline.py',RESOURCE]
    paths.extend(Path(__file__).with_name(name+'.py') for name in ('general_context_interpreter','context_expression_matcher','attribute_request_interpreter','nlp_interpreter','request_field_extractor','controlled_value_mapper','structured_request_builder'))
    from app.application.nlp.verified_subtype_interpreter import active
    if active():
        from app.domain.value_objects.verified_garment_subtype import RESOURCE as SUBTYPE_RESOURCE
        paths.extend((Path(__file__).with_name('verified_subtype_interpreter.py'),SUBTYPE_RESOURCE))
    paths.append(Path(grammar_identity.__file__))
    paths.append(Path(conversational_attribute_forms.__file__))
    return grammar_identity.semantic_fingerprint(p.read_bytes() for p in paths)

def matching(original):
    if type(original) is not str or not original.strip() or len(original)>500:raise UnsupportedMeaning('invalid_text')
    text=original.lower().replace('\u2019',"'").replace('\u2018',"'").replace('\u00e9','e')
    if len(text)!=len(original):raise UnsupportedMeaning('unsupported_text_encoding')
    return text

def outside_literals(text):
    chars=list(text)
    for m in re.finditer(r'("(?:[^"\\]|\\.)*")',text,re.I):chars[m.start(1):m.end(1)]=' '*(m.end(1)-m.start(1))
    return ''.join(chars)


def neutral_request(original):
    """Complete neutral frames only; never a prefix that can hide requirements."""
    return type(original) is str and re.fullmatch(
        r'\s*(?:surprise\s+me\s+with\s+an\s+outfit|'
        r'can\s+you\s+recommend\s+something\s+for\s+me\s+to\s+wear|'
        r'pick\s+something\s+for\s+me|help\s+me\s+choose\s+an\s+outfit|'
        r'could\s+you\s+suggest\s+an\s+outfit\s*,?\s+please)\s*[.!?]*\s*',
        original,re.I) is not None


def mask_polite_frame(original,remaining=None):
    """Mask closed request wrappers at original offsets, retaining every body word."""
    prefix=re.match(r'\s*(?:(?:hey|hi)\s*,\s*)?(?:(?:can|could)\s+you\s+'
                    r'(?:help\s+me\s+find|suggest|recommend)|please\s+(?:suggest|recommend))\s+',original,re.I)
    if prefix is None:return original if remaining is None else remaining
    work=list(original if remaining is None else remaining)
    work[:prefix.end()]=' '*prefix.end()
    # Keep the actual request verb: existing complete "recommend any outfit"
    # frames and request-count safeguards still see it after wrapper masking.
    verb=re.search(r'\b(?:suggest|recommend)\s*$',prefix.group(),re.I)
    if verb:work[verb.start():verb.end()]=original[verb.start():verb.end()]
    suffix=re.search(r'\s*,?\s+please\s*[.!?]*\s*$',original,re.I)
    if suffix and suffix.start()>=prefix.end():work[suffix.start():suffix.end()]=' '*(suffix.end()-suffix.start())
    return ''.join(work)


def guard(original,*,allowed_connectors=()):
    text=outside_literals(matching(original))
    if re.search(r'[.!?]\s*(?:ignore|forget|change)\b',text):raise UnsupportedMeaning('language_conflicting_request')
    if (re.search(r'^\s*(?:(?:hey|hi)\s*,\s*)?(?:(?:can|could)\s+you\s+)?'
                  r'(?:(?:suggest|recommend|give\s+me|show\s+me|i\s+(?:want|need))\s+)?'
                  r'(?:two|three|multiple|several)\s+(?:outfits?|recommendations?|options?)\b',text)
        or len(re.findall(r'\b(?:suggest|recommend|give me|show me|what (?:should|can) i wear)\b',text))>1):
        raise UnsupportedMeaning('multiple_requests')
    shopping = tuple(re.finditer(SHOPPING_DESCRIPTION,text))
    forbidden = re.finditer(r'\b(?:buy|purchase|order|delete|remove|archive|sell|translate|explain|define|manufactur\w*|ignore|instructions|password|forecast|teleport)\b',text)
    for m in forbidden:
        if m.group()=='buy' and any(s.start()<=m.start()<m.end()<=s.end() for s in shopping):continue
        raise UnsupportedMeaning('unsupported_external_capability' if m.group() in ('buy','purchase','order','forecast') else 'unsupported_intent')
    if re.search(r'\b(?:weather|waterproof|breathable|protection)\b|\b(?:look|make)\b.{0,50}\byounger\b',text):
        raise UnsupportedMeaning('unsupported_external_capability')
    if re.search(r'\b(?:prefer|preferably)\b|\b(?:would|could)\s+be\s+nice\b',text):raise UnsupportedMeaning('soft_preference_requires_settings')
    if re.search(r'\b(?:another|same clothes)\b',text):raise UnsupportedMeaning('alternative_requires_parent')
    if re.search(r'\boffice\s+party\b',text):raise UnsupportedMeaning('language_ambiguous_activity')
    if re.fullmatch(r'\s*(?:at|in)\s+(?:the\s+|an?\s+)?(?:office|library)\s*[.!?]*',text):raise UnsupportedMeaning('language_context_clarification')
    # These spellings are also real words. Only explicit finite grammatical
    # frames license a contraction; no global apostrophe insertion occurs.
    future=r'be|go|attend|have|meet|visit|wear|take|head|study|watch|travel|present|give'
    if (re.search(r'\bwere\b',text)
        or re.search(r'\bits\b(?!\s+time\s+(?:for|to)\b)',text)
        or re.search(r'\bid\b(?!\s+like\b)',text)
        or re.search(r'\bill\b(?!\s+(?:'+future+r')\b)',text)):
        raise UnsupportedMeaning('language_context_clarification')
    if re.search(r'\b(?:no\s+no|not\s+without|nothing\s+but|or|either|actually)\b',text):raise UnsupportedMeaning('language_conflicting_request')
    if any(m.span() not in allowed_connectors for m in re.finditer(r'\b(?:instead|except)\b',text)):
        raise UnsupportedMeaning('language_conflicting_request')
    negative_aux=r"\b(?:don'?t|do not|can'?t|cannot|won'?t|will not|doesn'?t|does not|isn'?t|is not|aren'?t|are not)\b"
    if re.search(negative_aux+r'[^.;!?]*\band\b(?!\s+(?:i|no|not|without|avoid|excluding)\b)',text):
        raise UnsupportedMeaning('language_conflicting_request')
    event=r'(?:class(?:es)?|dinner|lunch|supper|date|shopping|office|library|meeting|wedding|interview|presentation|eat|cinema|movies|coffee|birthday|journey)\b'
    if re.search(r"\b(?:no|not|never|don'?t|doesn'?t|can'?t|won'?t|isn'?t|aren'?t|cannot|do not|does not|will not|is not|are not)\s+(?:(?:going|go|gonna|attending|attend|having|have|want|wanna|out|to|a|an|the)\s+){0,7}"+event,text):raise UnsupportedMeaning('language_negated_event')
    if re.search(r'\b(?:guarantee\w*|waterproof|breathable|protection|attractive|quantum|rayon|under\s+\$)\b',text):raise UnsupportedMeaning('language_unsupported_requirement')
    return text

class ConversationalContextInterpreter(GeneralContextInterpreter):
    def __init__(self):
        super().__init__('context_18_v1')
        self.language=load_language();self.hash=fingerprint()
        self.anchors=tuple((sid,re.compile(r'(?<!\w)(?:'+p+r')(?!\w)',re.I)) for sid,patterns in self.language['contexts'].items() for p in patterns)
        self.anchors=(*self.anchors,('everyday.shopping',re.compile(SHOPPING_DESCRIPTION,re.I)))

    def interpret(self,original):
        try:guard(original)
        except UnsupportedMeaning as e:return NLPOutcome('InvalidInput' if e.reason=='invalid_text' else 'UnsupportedRequest',e.reason,'Please clarify the indicated request condition.',original)
        old=super().interpret(original)
        newer=self.interpret_masked(original,original)
        if old.status=='Supported':
            old_sid=getattr(getattr(old.structured_request,'context',None),'situation',ContextSlot()).value
            new_sid=getattr(getattr(newer.structured_request,'context',None),'situation',ContextSlot()).value if newer.status=='Supported' else None
            if new_sid is None or new_sid==old_sid:return old
        return newer

    def interpret_masked(self,original,remaining):
        try:
            if type(remaining) is not str or len(remaining)!=len(original):raise UnsupportedMeaning('unsupported_text_encoding')
            if neutral_request(original):
                return NLPOutcome('Supported','interpreted','Outfit request interpreted.',original,StructuredOutfitRequest())
            text=matching(mask_polite_frame(original,remaining))
            if len(text)!=len(original):raise UnsupportedMeaning('unsupported_text_encoding')
            events=[(sid,m) for sid,p in self.anchors for m in p.finditer(text)]
            # Prefer complete lexical expressions over contained aliases.
            refined={('everyday.academic_attendance','academic.presentation'),('professional.office_day','professional.workplace_meeting'),('social.meal','social.date')}
            events=[(sid,m) for sid,m in events if not any(o.start()<=m.start() and m.end()<=o.end() and ((sid==other and o.end()-o.start()>m.end()-m.start()) or (sid,other) in refined) for other,o in events)]
            events=list({(sid,m.start(),m.end()):(sid,m) for sid,m in events}.values())
            ids={sid for sid,m in events}
            ordered=sorted(events,key=lambda pair:pair[1].start())
            one_expression=all(b.start()<a.end() or re.fullmatch(r'\s+(?:for|at|in|to)\s+',text[a.end():b.start()]) for (_,a),(_,b) in zip(ordered,ordered[1:]))
            if len(ids)>1 or not one_expression:raise UnsupportedMeaning('language_conflicting_request')
            if not events and re.search(r'\b(?:interview|presentation|meeting|library|going out|at the office)\b',text):raise UnsupportedMeaning('language_context_clarification')
            slots={};work=list(text)
            def consume(a,b):work[a:b]=' '*(b-a)
            def slot(name,observations):
                if not observations:return
                values=tuple(dict.fromkeys(v for a,b,v in observations))
                spans=tuple(SourceSpan(a,b,original[a:b]) for a,b,v in observations)
                slots[name]=ContextSlot('Known' if len(values)==1 or name=='facets' else 'Conflicting',values,spans)
                for a,b,v in observations:consume(a,b)
            sid=next(iter(ids)) if ids else None
            if sid:
                situation=next(s for s in self.situations if s.identifier==sid)
                slot('situation',[(m.start(),m.end(),sid) for _,m in events])
                for name in ('activity','venue'):
                    value=getattr(situation,name)
                    if value is not None:slots[name]=ContextSlot('Known',(value,),slots['situation'].spans)
            roles=[]
            for m in re.finditer(r"\b(?:as (?:a|an|the) |(?:i'm|i am) (?:a|the) )(guest|bride|groom|bridesmaid|groomsman|presenter|attendee|candidate|graduate|interviewer|employee|staff)\b",text):roles.append((m.start(),m.end(),m.group(1)))
            # Teammate's closed interview-role forms also apply through this
            # conversational companion; consume their complete original spans.
            if sid=='professional.job_interview':
                for pattern in (r'\bas (candidate|interviewer)\b',
                                r"\bwhere\s+(?:i\s+am|i'm)\s+(?:the\s+)?(candidate|interviewer)\b"):
                    roles.extend((m.start(),m.end(),m.group(1)) for m in re.finditer(pattern,text))
            for pattern,value in [(r'\bbeing interviewed\b','candidate'),(r'\bpresenting\b','presenter'),(r'\bgiving\b(?=.{0,30}\bpresentation\b)','presenter'),(r'\bconducting\b','interviewer'),(r'\bin the audience\b','attendee')]:
                if sid in ('academic.presentation','professional.job_interview'):roles.extend((m.start(),m.end(),value) for m in re.finditer(pattern,text))
            slot('role',roles)
            if slots.get('role',ContextSlot()).state=='Conflicting':raise UnsupportedMeaning('language_conflicting_request')
            codes=[(m.start(),m.end(),self.grammar['dress_codes'][m.group(1)]) for m in re.finditer(r'\b(?:the )?dress code is (smart casual|casual|formal|black tie)\b',text)]
            slot('dress_code',codes)
            if slots.get('dress_code',ContextSlot()).state=='Conflicting':raise UnsupportedMeaning('language_conflicting_request')
            slot('formality',[(a,b,value) for a,b,value in requested_formality_spans(original) if text[a:b].strip()])
            slot('temporal',[(m.start(),m.end(),m.group()) for m in re.finditer(r'\b(?:today|tonight|tomorrow|later)\b',text)])
            if slots.get('temporal',ContextSlot()).state=='Conflicting':raise UnsupportedMeaning('language_conflicting_request')
            venues=[]
            for m in re.finditer(r'\b(?:at|in|to|around|for)\s+(?:(?:a|the|my)\s+)?(hotel|office|restaurant|university|uni|campus|library|cinema|cafe|city|indoors|outdoors)\b',text):venues.append((m.start(),m.end(),'university' if m.group(1)=='uni' else m.group(1)))
            slot('venue',venues)
            companions=[]
            for m in re.finditer(r"\b(friends?|family|colleagues|classmates|someone)\b(?:'s|')?",text):
                # An indefinite person establishes no restricted companion class.
                # Original text remains captured; modifiers remain unconsumed.
                if sid=='social.meal' and m.group()=='someone':
                    consume(m.start(),m.end());continue
                companions.append((m.start(),m.end(),'friends' if m.group(1) in ('friend','friends') else m.group(1)))
            slot('companions',companions)
            if sid=='social.date':slot('facets',[(m.start(),m.end(),'meal:dinner') for m in re.finditer(r'\bdinner\b',text)])
            if sid=='travel.journey':slot('facets',[(m.start(),m.end(),'transport:'+m.group()) for m in re.finditer(r'\b(?:train|bus|flight)\b',text)])
            for pattern in self.language['function_frames']:
                for m in re.finditer(pattern,text):consume(m.start(),m.end())
            # Functional words are licensed only around an actual context or
            # garment request. No semantic descriptor or unknown word is erased.
            for m in re.finditer(r'\b(?:be|our|some|regular|ordinary)\b',text):consume(m.start(),m.end())
            residue=''.join(work)
            # "Any" licenses only these complete neutral request frames. Match
            # the unconsumed input, not a prefix or a globally ignored token;
            # modifiers/activities must still be parsed or refused normally.
            if sid is None and re.fullmatch(r'\s*(?:please\s+)?(?:suggest|recommend)\s+any\s+outfit\s*[.!?]*\s*',text):
                residue=' ' * len(residue)
            fields=self.mapper.map_values(self.extractor.extract(residue))
            if fields['occasion']:raise UnsupportedMeaning('language_conflicting_request')
            if not sid:
                if not any(fields.values()) and not re.search(r'\b(?:outfit|clothes|clothing|wear|something)\b',text):raise UnsupportedMeaning('unsupported_intent')
                return NLPOutcome('Supported','interpreted','Outfit request interpreted.',original,StructuredOutfitRequest(style=next(iter(fields['style']),None),colours=fields['colours'] or None,garment_categories=fields['garment_categories'] or None,formality=next(iter(fields['formality']),None)))
            for field,name in [('style','style'),('colours','colours'),('garment_categories','categories'),('formality','formality')]:
                matches=[m for m in self.extractor.extract(residue) if m.field==field]
                observations=[(m.start,m.end,(m.kind+':' if m.kind else '')+m.canonical_value) for m in matches]
                prior=slots.get(name,ContextSlot())
                if name=='formality':observations.extend((s.start,s.end,prior.value) for s in prior.spans)
                slot(name,observations)
            if slots.get('formality',ContextSlot()).state=='Conflicting':raise UnsupportedMeaning('language_conflicting_request')
            code=slots.get('dress_code',ContextSlot()).value;formality=slots.get('formality',ContextSlot()).value
            if code is not None and formality is not None and code!=formality:raise UnsupportedMeaning('language_conflicting_request')
            frame=GeneralContext(original,**slots,grammar_sha256=self.grammar_hash,taxonomy_sha256=self.taxonomy_hash,version='general-context-1.1.0',bundle_id=self.bundle_id)
            request=GeneralContextRequest(occasion=situation.projection_occasion,style=next(iter(fields['style']),None),colours=fields['colours'] or None,garment_categories=fields['garment_categories'] or None,formality=code if code is not None else formality,context=frame)
            return NLPOutcome('Supported','context_interpreted','Situation understood; eligibility is checked separately.',original,request)
        except UnsupportedMeaning as e:
            reason=e.reason
            if reason in ('unrecognized_condition','garment_colour_binding'):reason='language_unsupported_requirement'
            return NLPOutcome('UnsupportedRequest',reason,'Please clarify the indicated request condition.',original)
