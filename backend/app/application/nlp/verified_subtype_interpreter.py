"""Finite noun matches at original offsets; literals and residual modifiers survive."""
import os,re
from app.domain.value_objects.verified_garment_subtype import registry,PROFILE,ENVIRONMENT_KEY
from app.domain.value_objects.attribute_conditions import AttributeRequestError
def active():return os.getenv(ENVIRONMENT_KEY,'disabled')==PROFILE
def heads(text):
    if not active():return ()
    candidates=[]
    for entry in registry()['entries']:
        for alias in entry['aliases']:
            pattern=r'(?<!\w)'+re.escape(alias).replace(r'\ ',r'[\s-]+')+r's?(?!\w)'
            candidates.extend((m,entry['id']) for m in re.finditer(pattern,text,re.I))
    candidates.sort(key=lambda pair:(pair[0].start(),-len(pair[0].group())))
    result=[];end=-1
    for match,kind in candidates:
        if match.start()<end:continue
        if result and re.fullmatch(r'\s*',text[end:match.start()]):raise AttributeRequestError('GarmentWordingClarification','ambiguous_garment_product_identity')
        result.append((match,'upper','subtype:'+kind));end=match.end()
    return tuple(result)
