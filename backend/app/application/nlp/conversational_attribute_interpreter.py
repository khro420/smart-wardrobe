"""Supplement existing B1 bindings without altering its canonical algebra."""
import re,json,hashlib
from app.application.nlp.attribute_request_interpreter import AttributeRequestInterpreter,AttributeInterpretation
from app.application.nlp.conversational_context_interpreter import load_language,fingerprint,outside_literals
from app.domain.value_objects.attribute_conditions import AttributeConditions,AttributeRequestError,CANONICAL_ENUMS,VERSION

class ConversationalAttributeInterpreter(AttributeRequestInterpreter):
    def __init__(self):
        super().__init__();self.language=load_language()
        self.descriptors=(*self.descriptors,*((re.compile(r'(?<!\w)(?:'+a['pattern']+r')(?!\w)',re.I),a['field'],a['value']) for a in self.language['attribute_aliases']))
    @property
    def sha256(self):return fingerprint()

    def _legacy_parse(self,original):
        shield=[False]*len(original);matching=outside_literals(original)
        for patterns in self.language['contexts'].values():
            for pattern in patterns:
                for m in re.finditer(r'(?<!\w)(?:'+pattern+r')(?!\w)',matching,re.I):shield[m.start():m.end()]=[True]*(m.end()-m.start())
        for m in re.finditer(r'\b(?:the )?dress code is (?:smart casual|casual|formal|black tie)\b',matching,re.I):shield[m.start():m.end()]=[True]*(m.end()-m.start())
        attribute_text=''.join(' ' if used else c for c,used in zip(original,shield))
        # Explicit field-first colour clauses are aliases of the existing
        # field-qualified forms. Shield them before generic colour extraction
        # so a secondary colour cannot accidentally become a primary colour.
        names='|'.join(re.escape(v) for v in sorted(CANONICAL_ENUMS['primary_colour'],key=len,reverse=True))
        qualified=list(re.finditer(r'\b(primary|main|secondary)\s+colou?r\s+(?:is\s+)?('+names+r'|#[0-9a-fA-F]{6})(?!\w)',outside_literals(attribute_text),re.I))
        qualified=[m for m in qualified if not re.search(r'\bexact\s+$',original[:m.start()],re.I)]
        if len(qualified)>1:raise AttributeRequestError('UnsupportedRequest','ambiguous_same_binding')
        base=list(attribute_text)
        for m in qualified:base[m.start():m.end()]=' '*(m.end()-m.start())
        old=super().parse(''.join(base))
        if qualified and old.conditions is not None:
            raise AttributeRequestError('UnsupportedRequest','ambiguous_same_binding')
        groups=old.conditions.to_dict()['groups'] if old.conditions else []
        spans=list(old.spans);work=list(old.remaining);text=outside_literals(attribute_text)
        for m in qualified:work[m.start():m.end()]=original[m.start():m.end()]
        next_id=max((int(c['id'][1:]) for g in groups for c in g['conditions']),default=0)
        def consume(a,b):work[a:b]=' '*(b-a)
        def free(a,b):return any(not c.isspace() for c in ''.join(work[a:b]))
        def negative(start):
            # Match commands against original coordinates. Never erase a
            # negative auxiliary unless a recognized garment condition follows.
            command=r"(?:i\s+)?(?:(?:do\s+not|don['\u2019]?t)\s+(?:want(?:\s+to\s+(?:wear|include|use))?|wanna\s+(?:wear|include|use)|wear|include|use)|(?:can['\u2019]?t|cannot|won['\u2019]?t|will\s+not)\s+(?:wear|include|use))"
            outfit=r"(?:(?:an?|the)\s+)?outfit(?:\s+that)?\s+(?:(?:doesn['\u2019]?t|does\s+not)\s+(?:include|contain|use)|isn['\u2019]?t|is\s+not)"
            clothes=r"(?:clothes|garments)(?:\s+that)?\s+(?:aren['\u2019]?t|are\s+not)"
            return re.search(r'\b(?:'+command+'|'+outfit+'|'+clothes+r'|nothing\s+made\s+of|no|not|without|avoid|excluding)\s+(?:any\s+|an?\s+)?$',original[:start],re.I)
        def append(field,value,a,b,role=None,quantifier=None,end=None):
            nonlocal next_id
            if not free(a,b):return
            neg=negative(a)
            if neg:
                quantifier='none';consume(neg.start(),neg.end())
            if role is None:role='all_selected' if neg else 'base_upper_body' if field in ('neckline','sleeve_length') else 'base' if field in ('style','silhouette') else 'all_selected'
            next_id+=1;cid=f'c{next_id:02d}'
            op='exact_hex' if field in ('primary_colour','secondary_colour') and value.startswith('#') else 'contains_any' if field in ('material','style') else 'in'
            groups.append({'id':f'g{len(groups)+1:02d}','role':role,'quantifier':quantifier or 'exists','conditions':[{'id':cid,'attribute':field,'operator':op,'values':[value]}]})
            spans.append((cid,'nlp',a,b,original[a:b]))
            if neg:spans.append((cid,'nlp',neg.start(),neg.end(),original[neg.start():neg.end()]))
            consume(a,end or b)
            if end and end>b:spans.append((cid,'nlp',b,end,original[b:end]))
        for m in qualified:
            append('secondary_colour' if m.group(1).lower()=='secondary' else 'primary_colour',m.group(2).lower(),m.start(),m.end())
            noun=re.search(r'\bgarment\s+(?:whose|with)\s+$',original[:m.start()],re.I)
            if noun:consume(noun.start(),noun.end())
        # Extend negation on already-bound original phrases, retaining noun scope.
        for g in groups:
            starts=[s[2] for s in spans if s[0] in {c['id'] for c in g['conditions']}]
            neg=negative(min(starts)) if starts else None
            if neg:
                g['quantifier']='none';consume(neg.start(),neg.end())
                for c in g['conditions']:spans.append((c['id'],'nlp',neg.start(),neg.end(),original[neg.start():neg.end()]))
        # Jeans carries both existing category and material semantics on one member.
        for m in re.finditer(r'\bjeans\b',text,re.I):
            target=next((g for g in groups if any(s[0] in {c['id'] for c in g['conditions']} and s[2]<m.end() and m.start()<s[3] for s in spans)),None)
            if target is None:
                if not free(m.start(),m.end()):continue
                append('category','trousers',m.start(),m.end(),role='lower');target=groups[-1]
            if not any(c['attribute']=='material' and 'denim' in c['values'] for c in target['conditions']):
                next_id+=1;cid=f'c{next_id:02d}';target['conditions'].append({'id':cid,'attribute':'material','operator':'contains_any','values':['denim']});spans.append((cid,'nlp',m.start(),m.end(),original[m.start():m.end()]))
        candidates=[]
        for entry in self.language['attribute_aliases']:
            candidates.extend((m,entry['field'],entry['value']) for m in re.finditer(r'(?<!\w)(?:'+entry['pattern']+r')(?!\w)',text,re.I))
        for field in ('pattern','material','style','silhouette','neckline','primary_colour'):
            for value in CANONICAL_ENUMS[field]:
                pattern=r'(?<!\w)'+r'[\s-]+'.join(re.escape(p) for p in value.split())+r'(?!\w)'
                candidates.extend((m,field,value) for m in re.finditer(pattern,text,re.I))
        for m,field,value in sorted(candidates,key=lambda x:(-(x[0].end()-x[0].start()),x[0].start())):
            if not free(m.start(),m.end()):continue
            if any(c!=' ' for c in ''.join(work[m.start():m.end()]) if not c.isspace()) and any(work[i]==' ' and not original[i].isspace() for i in range(m.start(),m.end())):continue
            suffix=re.match(r'\s+(tops?|shirts?|dresses?|garments?|outfits?)\b',original[m.end():],re.I)
            role=None;end=None
            if suffix:
                noun=suffix.group(1).lower();role='upper' if noun.startswith(('top','shirt')) else 'one_piece' if noun.startswith('dress') else 'all_selected';end=m.end()+suffix.end()
            append(field,value,m.start(),m.end(),role=role,end=end)
        if not groups:return AttributeInterpretation(None,original,(),self.sha256)
        # Consume only connectors that introduce an actually recognized span.
        for m in re.finditer(r'\b(?:and\s+(?:i\s+)?want|with|made\s+of)\s+(?:a\s+|an\s+)?',original,re.I):
            if m.end()<len(work) and work[m.end()]==' ':consume(m.start(),m.end())
        starts={c['id']:min(s[2] for s in spans if s[0]==c['id']) for g in groups for c in g['conditions']}
        groups.sort(key=lambda g:min(starts[c['id']] for c in g['conditions']))
        remap={};index=0
        for number,g in enumerate(groups,1):
            g['id']=f'g{number:02d}';g['conditions'].sort(key=lambda c:starts[c['id']])
            for c in g['conditions']:index+=1;prior=c['id'];c['id']=f'c{index:02d}';remap[prior]=c['id']
        spans=[(remap[cid],source,a,b,raw) for cid,source,a,b,raw in spans]
        for i,used in enumerate(shield):
            if used:work[i]=original[i]
        return AttributeInterpretation(AttributeConditions.from_dict({'version':VERSION,'groups':groups}),''.join(work),tuple(spans),self.sha256)

    def parse(self,original):
        """Bind finite noun phrases before the older independent-field scanner.

        Each consumed character retains its original position. Anything outside
        the licensed phrase is passed to the existing parser/residual check.
        """
        if type(original) is not str or not original.strip() or len(original)>500:
            return self._legacy_parse(original)
        if re.search(r'\bon\s+the\s+same\s+garment\b',original,re.I):return self._legacy_parse(original)
        descriptors=(*self.descriptors,*((p,e['attribute'],e['value']) for p,e in self.entries if e['attribute']=='sleeve_length' and e['status']=='Planned'))
        descriptors=(*descriptors,*((re.compile(r'(?<!\w)(?:'+d['pattern']+r')(?!\w)',re.I),d['field'],d['value']) for d in self.language['noun_descriptors']))
        text=outside_literals(original);blocked=[False]*len(text)
        for patterns in self.language['contexts'].values():
            for pattern in patterns:
                for m in re.finditer(r'(?<!\w)(?:'+pattern+r')(?!\w)',text,re.I):blocked[m.start():m.end()]=[True]*(m.end()-m.start())
        # Explicit field identities and quoted literals retain their exact grammar.
        for pattern,entry in self.entries:
            if entry['attribute'] not in ('category','primary_colour','secondary_colour','palette_colour','palette_coverage'):continue
            for m in pattern.finditer(text):blocked[m.start():m.end()]=[True]*(m.end()-m.start())
        for m in re.finditer(r'\b(?:the )?dress code is (?:smart casual|casual|formal|black tie)\b',text,re.I):blocked[m.start():m.end()]=[True]*(m.end()-m.start())
        occupied=blocked[:];consumed=[False]*len(text);groups=[];spans=[]
        def free(a,b):return not any(occupied[a:b])
        def use(a,b):
            occupied[a:b]=[True]*(b-a);consumed[a:b]=[True]*(b-a)
        def descriptors_before(end):
            observations=[];cursor=end
            while True:
                found=[(m,f,v) for p,f,v in descriptors for m in p.finditer(text,0,cursor)
                    if free(m.start(),m.end()) and re.fullmatch(r'\s*(?:and\s+)?',text[m.end():cursor],re.I)]
                if not found:break
                m,f,v=max(found,key=lambda row:row[0].end()-row[0].start())
                observations.insert(0,(f,v,m.start(),m.end()));cursor=m.start()
            return observations,cursor
        def descriptors_after(start,connector):
            observations=[];cursor=start
            while True:
                link=re.match(connector if not observations else r'\s+(?:(?:and|with|made\s+of)\s+)?',text[cursor:],re.I)
                if not link:break
                pos=cursor+link.end()
                found=[(m,f,v) for p,f,v in descriptors if (m:=p.match(text,pos)) and free(m.start(),m.end())]
                if not found:break
                m,f,v=max(found,key=lambda row:row[0].end()-row[0].start())
                observations.append((f,v,m.start(),m.end()));cursor=m.end()
            return observations,cursor
        command=r"(?:i\s+)?(?:(?:do\s+not|don['\u2019]?t)\s+(?:want(?:\s+to\s+(?:wear|include|use))?|wanna\s+(?:wear|include|use)|wear|include|use)|(?:can['\u2019]?t|cannot|won['\u2019]?t|will\s+not)\s+(?:wear|include|use))"
        def negative(start):return re.search(r'\b(?:'+command+r'|no|not|without|avoid|excluding)\s+(?:any\s+|an?\s+)?$',text[:start],re.I)
        def add(obs,role,quantifier,noun,extra=()):
            if not obs:return
            conditions=[]
            for field,value,a,b in obs:
                cid=f'c{1+sum(len(g["conditions"]) for g in groups)+len(conditions):02d}'
                conditions.append({'id':cid,'attribute':field,'operator':'exact_text' if field=='garment_name' else 'bool_eq' if type(value) is bool else 'contains_any' if field in ('material','style') else 'in','values':list(value) if type(value) is tuple else [value]})
                for x,y in ((a,b),noun,*extra):spans.append((cid,'nlp',x,y,original[x:y]))
            groups.append({'id':f'g{len(groups)+1:02d}','role':role,'quantifier':quantifier,'conditions':conditions})
        heads=[]
        for name,role in self.nouns.items():
            heads.extend((m,role,None) for m in re.finditer(r'\b'+re.escape(name)+(r'\b' if name.endswith('s') or name=='something' else r's?\b'),text,re.I))
        tee_aliases=((re.compile(r'(?<!\w)long[\s-]+sleeve(?:d)?\s+t[\s-]+shirts?(?!\w)',re.I),'long_sleeve_top'),(re.compile(r'(?<!\w)t[\s-]+shirts?(?!\w)',re.I),'short_sleeve_top'))
        from app.application.nlp.verified_subtype_interpreter import active,heads as subtype_heads
        if active():tee_aliases=()
        heads.extend(subtype_heads(text))
        for p,cat in (*tee_aliases,*self.category_aliases):
            role='upper' if cat.endswith('_top') else 'one_piece' if cat.endswith('_dress') else 'outerwear' if 'outwear' in cat else 'lower'
            heads.extend((m,role,cat) for m in p.finditer(text))
        for noun,cat in [('trousers','trousers'),('pants','trousers'),('shorts','shorts'),('skirt','skirt'),('jeans','trousers')]:
            heads.extend((m,'lower',cat) for m in re.finditer(r'\b'+noun+r's?\b',text,re.I))
        heads.sort(key=lambda row:(row[0].start(),-(row[0].end()-row[0].start()),row[2] is None))
        def before_next_head(observations,end,noun_end,*,negative=False):
            if not observations or not any(h.start()>=end and re.fullmatch(r'\s*',text[end:h.start()]) for h,_,_ in heads):
                return observations,end
            # A trailing prenominal phrase belongs to the next noun. Keep the
            # current noun's postnominal prefix only across one explicit join.
            gaps=[(i,text[observations[i-1][3]:observations[i][2]]) for i in range(1,len(observations))]
            joins=[i for i,gap in gaps if re.fullmatch(r'\s+and\s+',gap,re.I)]
            if not joins:joins=[i for i,gap in gaps if re.fullmatch(r'\s+with\s+',gap,re.I)]
            if not joins:return [],noun_end
            if negative or len(joins)!=1:raise AttributeRequestError('UnsupportedRequest','ambiguous_same_binding')
            split=joins[0]
            # "with blue and red jeans" also admits a same-member reading.
            # Do not pick an attachment when both sides describe the same axis.
            if {o[0] for o in observations[:split]}&{o[0] for o in observations[split:]}:
                raise AttributeRequestError('UnsupportedRequest','ambiguous_same_binding')
            return observations[:split],observations[split-1][3]
        for noun,role,category in heads:
            a,b=noun.span()
            if noun.group().lower().rstrip('s')=='outfit':continue
            if not free(a,b):continue
            negative_tail,negative_end=descriptors_after(b,r'\s+(?:without|with\s+no)\s+(?:an?\s+)?')
            before_next_head(negative_tail,negative_end,b,negative=True)
            obs,start=descriptors_before(a)
            # "no floral patterns on my top" names a role after its descriptor.
            scoped=re.search(r'\s+(?:patterns?\s+)?on\s+(?:my|the|a)\s+$',text[:a],re.I)
            if scoped:
                before,cursor=descriptors_before(scoped.start())
                if before:obs=before;start=cursor
            anonymous=noun.group().lower()=='something'
            after,end=descriptors_after(b,r'\s+(?:(?:with|made\s+of)\s+)?' if anonymous else r'\s+(?:with|made\s+of)\s+(?:an?\s+)?')
            if after and re.match(r'\s+(?:pattern|material|style|silhouette|neckline)\b',text[end:],re.I):continue
            after,end=before_next_head(after,end,b)
            obs.extend(after)
            neg=negative(start)
            every=re.search(r'\b(?:all|every)\s+(?:selected\s+)?$',text[:start],re.I)
            quantifier='none' if neg else 'all_present' if every else 'exists'
            if category and category.startswith('subtype:'):
                if quantifier=='none':role='all_selected'
                obs.append(('verified_subtype',category.split(':',1)[1],a,b))
                named=re.match(r'\s+named\s+("(?:[^"\\]|\\.)*")',original[b:],re.I)
                if named:
                    value=json.loads(named.group(1))
                    obs.append(('garment_name',value,b+named.start(1),b+named.end(1)))
                    end=b+named.end()
            elif category:
                if category=='long_sleeve_top' and re.search(r'\bt[\s-]+shirts?\b',noun.group(),re.I):obs.append(('sleeve_length','wrist-length',a,b))
                obs.append(('category',category,a,b))
                if category=='trousers' and noun.group().lower()=='jeans':obs.append(('material','denim',a,b))
                # Natural long-sleeve claims require fine evidence, independently
                # of the coarse category. Explicit field-qualified forms above
                # are shielded and never acquire inferred fine attributes.
                if not neg and '_' not in noun.group() and re.search(r'long[\s-]+sleeve',noun.group(),re.I) and not any(o[0]=='sleeve_length' for o in obs):obs.append(('sleeve_length','wrist-length',a,b))
            if anonymous:
                if len(obs)<2:continue  # bare "something blue" keeps its contract
                role='base_upper_body' if any(o[0] in ('sleeve_length','neckline') for o in obs) else 'base' if any(o[0] in ('style','silhouette') for o in obs) else 'all_selected'
            if not obs and noun.group().lower().rstrip('s') in ('shirt','top'):
                # A finite unmodified upper head coordinated with an actual
                # canonical lower noun is an existence requirement. No upper
                # colour or fine property is inferred from the second head.
                for following,following_role,following_category in heads:
                    if following.start()<=b or following_role!='lower':continue
                    lower_observations,lower_start=descriptors_before(following.start())
                    if re.fullmatch(r'\s+(?:with|and)\s+(?:an?\s+)?',text[b:lower_start],re.I):
                        if neg:raise AttributeRequestError('UnsupportedRequest','nested_binding_negation')
                        upper=tuple(c for c in CANONICAL_ENUMS['category'] if c in ('short_sleeve_top','long_sleeve_top','vest','sling'))
                        obs=[('category',upper,a,b)]
                        break
            if not obs:continue
            # No implicit alternatives or duplicated contradictory colour axis.
            colours={v for f,v,_,_ in obs if f=='primary_colour'}
            if len(colours)>1:raise AttributeRequestError('UnsupportedRequest','ambiguous_same_binding')
            obs.sort(key=lambda o:o[2])
            extra=tuple(x for x in ((neg.start(),neg.end()) if neg else None,(every.start(),every.end()) if every else None,(scoped.start(),scoped.end()) if scoped else None) if x)
            add(obs,role,quantifier,(a,b),extra)
            use(start,end)
            if neg:use(neg.start(),neg.end())
            if every:use(every.start(),every.end())
            # A post-nominal negative belongs to that noun's role, not to every
            # selected member. It has its own B1 none conjunction.
            suffix=re.match(r'\s+(?:without|with\s+no)\s+(?:an?\s+)?',text[end:],re.I)
            if suffix:
                if neg:raise AttributeRequestError('UnsupportedRequest','nested_binding_negation')
                other,stop=descriptors_after(end,r'\s+(?:without|with\s+no)\s+(?:an?\s+)?')
                if other:
                    unit=re.match(r'\s+patterns?\b',text[stop:],re.I) if other[-1][0]=='pattern' else None
                    extra=((end,end+suffix.end()),)+(((stop,stop+unit.end()),) if unit else ())
                    if unit:stop+=unit.end()
                    add(other,role,'none',(a,b),extra);use(end,stop)
            if noun.group().lower().rstrip('s')=='outfit':consumed[a:b]=[False]*(b-a)
        if not groups:return self._legacy_parse(original)
        masked=''.join(' ' if used else c for c,used in zip(original,consumed))
        rest=self._legacy_parse(masked) if masked.strip() else AttributeInterpretation(None,masked,(),self.sha256)
        if rest.conditions:
            offset=sum(len(g['conditions']) for g in groups);mapping={}
            for g in rest.conditions.to_dict()['groups']:
                for c in g['conditions']:
                    old=c['id'];offset+=1;c['id']=f'c{offset:02d}';mapping[old]=c['id']
                groups.append(g)
            spans.extend((mapping[cid],src,a,b,original[a:b]) for cid,src,a,b,_ in rest.spans)
        starts={c['id']:min(s[2] for s in spans if s[0]==c['id']) for g in groups for c in g['conditions']}
        groups.sort(key=lambda g:min(starts[c['id']] for c in g['conditions']))
        remap={};index=0
        for i,g in enumerate(groups,1):
            g['id']=f'g{i:02d}';g['conditions'].sort(key=lambda c:starts[c['id']])
            for c in g['conditions']:index+=1;old=c['id'];c['id']=f'c{index:02d}';remap[old]=c['id']
        spans=tuple((remap[cid],src,a,b,raw) for cid,src,a,b,raw in spans)
        version='attribute-conditions-2.0.0' if any(c['attribute']=='verified_subtype' for g in groups for c in g['conditions']) else VERSION
        return AttributeInterpretation(AttributeConditions.from_dict({'version':version,'groups':groups}),rest.remaining,spans,self.sha256)
