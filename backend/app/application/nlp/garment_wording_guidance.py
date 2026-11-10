"""Captured wording limits; never infer garment subtypes from names or images."""
import re
from app.application.nlp.conversational_context_interpreter import outside_literals
from app.domain.value_objects.attribute_conditions import AttributeRequestError,digest
VERSION='garment-wording-guidance-1.0.0'
TEE=r'(?<!\w)t[\s-]+shirts?(?!\w)'
def check(text):
    if type(text) is not str:return
    value=outside_literals(text)
    from app.application.nlp.verified_subtype_interpreter import active
    if active():
        if re.search(r'\bdark\b',value,re.I):raise AttributeRequestError('GarmentWordingClarification','unregistered_dark_colour_family')
        return
    if re.search(r'\bblouses?\b',value,re.I):raise AttributeRequestError('GarmentWordingClarification','no_qualified_blouse_subtype')
    if re.search(r'\bdark\s+(?:trousers|pants|jeans|shirts?|tops?)\b',value,re.I):raise AttributeRequestError('GarmentWordingClarification','unregistered_dark_colour_family')
    # Inspect the noun's preceding frame. A postnominal "without floral"
    # remains a real negative pattern condition on the positive coarse top.
    negative=r"\b(?:no|not|without|avoid|excluding|(?:do\s+not|don['’]?t)\s+(?:want|wear|include|use)|(?:can['’]?t|cannot|won['’]?t)\s+wear)\s+"
    modifiers=r"(?:(?!(?:and|with|but|want|need|wear|include|use|trousers|jeans|outfit|garment)\b)[\w-]+\s+){0,6}"
    for match in re.finditer(TEE,value,re.I):
        if re.search(negative+modifiers+r'$',value[:match.start()],re.I) or re.search(r'\b(?:only|exactly|strictly)\b',value,re.I):
            raise AttributeRequestError('GarmentWordingClarification','negative_subtype_cannot_silently_exclude_whole_coarse_category')
def capture(text,intent):
    if intent is None or intent.to_dict()['version']=='assistant-attribute-intent-2.0.0':return None
    spans=[{'start':m.start(),'end':m.end(),'text':text[m.start():m.end()]} for m in re.finditer(TEE,outside_literals(text),re.I)]
    if not spans:return None
    return {'version':VERSION,'original_text_sha256':digest(text),'intent_sha256':intent.sha256,'spans':spans,'message':'T-shirt uses recorded coarse top-category evidence. Exact T-shirt versus blouse subtype is not verified; other top kinds can share that category.'}
def validate(raw,text,intent):
    expected=capture(text,intent)
    if raw!=expected:raise ValueError('Changed captured garment wording guidance.')
    return raw
