"""Lossless, leaf-only source table. No qualification or raw JSON normalization.

Identity is exact UTF-8 bytes, not parsed JSON equality or a digest alone.
The physical table keeps the existing 3 MiB budget; expansion is bounded by
100 sources * the unchanged 256 KiB individual-source limit.
"""
import hashlib
from app.domain.value_objects.attribute_conditions import encode,decode,exact

VERSION='request-local-source-table-1.0.0'
MAX_SOURCES=100
MAX_SOURCE_BYTES=262144
MAX_TABLE_BYTES=3145728
MAX_BLOBS=3*MAX_SOURCES
MAX_EXPANDED_BYTES=MAX_SOURCES*MAX_SOURCE_BYTES
SOURCE_FIELDS=('snapshot','description','category_source','links','media','media_sha256')
CATEGORY_FIELDS=('id','category','attributes_json','additional_attributes','preferred_media_id','updated_at')
RAW_FIELDS=('attributes_json','additional_attributes')


def _source_shape(source):
    exact(source,SOURCE_FIELDS);exact(source['category_source'],CATEGORY_FIELDS)


def pack_sources(sources):
    if type(sources) is not list or not 1<=len(sources)<=MAX_SOURCES:raise ValueError('Unbounded codec source count.')
    blobs=[];indices={};entries=[]
    def reference(raw):
        if type(raw) is not bytes or len(raw)>MAX_SOURCE_BYTES:raise ValueError('Oversized codec blob.')
        if raw not in indices:
            indices[raw]=len(blobs)
            blobs.append({'sha256':hashlib.sha256(raw).hexdigest(),'utf8_bytes':len(raw),'text':raw.decode('utf-8')})
        return {'blob':indices[raw]}
    for source in sources:
        _source_shape(source)
        if len(encode(source))>MAX_SOURCE_BYTES:raise ValueError('Expanded codec source exceeds its byte budget.')
        if type(source['description']) is not dict:raise ValueError('Codec description object required.')
        category=dict(source['category_source'])
        for field in RAW_FIELDS:
            raw=category[field]
            if raw is not None and type(raw) is not str:raise ValueError('Codec raw source must be text or null.')
            category[field]=None if raw is None else reference(raw.encode('utf-8'))
        entries.append({**source,'description':reference(encode(source['description'])),'category_source':category})
    result={'version':VERSION,'entries':entries,'blobs':blobs}
    if len(blobs)>MAX_BLOBS or len(encode(result))>MAX_TABLE_BYTES:raise ValueError('Encoded codec source table exceeds its byte budget.')
    return result


def unpack_sources(table):
    exact(table,('version','entries','blobs'))
    if table['version']!=VERSION or type(table['entries']) is not list or not 1<=len(table['entries'])<=MAX_SOURCES or type(table['blobs']) is not list or not 1<=len(table['blobs'])<=MAX_BLOBS:raise ValueError('Invalid codec version/counts.')
    if len(encode(table))>MAX_TABLE_BYTES:raise ValueError('Oversized codec source table.')
    leaves=[];identities=set();used=set()
    for blob in table['blobs']:
        # Leaves contain only literal text, never another reference or segments.
        # Cycles and reference chains consequently have no valid representation.
        exact(blob,('sha256','utf8_bytes','text'))
        if type(blob['text']) is not str or type(blob['utf8_bytes']) is not int or not 0<=blob['utf8_bytes']<=MAX_SOURCE_BYTES:raise ValueError('Invalid codec blob leaf.')
        raw=blob['text'].encode('utf-8')
        if len(raw)!=blob['utf8_bytes'] or hashlib.sha256(raw).hexdigest()!=blob['sha256'] or raw in identities:raise ValueError('Changed/duplicate codec blob bytes.')
        identities.add(raw);leaves.append(raw)
    def resolve(ref):
        exact(ref,('blob',));index=ref['blob']
        if type(index) is not int or not 0<=index<len(leaves):raise ValueError('Missing/invalid codec reference.')
        used.add(index);return leaves[index]
    sources=[];expanded_bytes=0
    for entry in table['entries']:
        _source_shape(entry);category=dict(entry['category_source'])
        for field in RAW_FIELDS:
            category[field]=None if category[field] is None else resolve(category[field]).decode('utf-8')
        raw=resolve(entry['description']);description=decode(raw,MAX_SOURCE_BYTES)
        if type(description) is not dict or encode(description)!=raw:raise ValueError('Noncanonical codec description bytes.')
        source={**entry,'description':description,'category_source':category}
        size=len(encode(source));expanded_bytes+=size
        if size>MAX_SOURCE_BYTES or expanded_bytes>MAX_EXPANDED_BYTES:raise ValueError('Oversized codec expansion.')
        sources.append(source)
    if used!=set(range(len(leaves))):raise ValueError('Unused codec blob.')
    return sources
