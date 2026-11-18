from pathlib import Path
import base64,hashlib,json
from app.shared_contracts.grammar_identity import semantic_fingerprint

def test_exact_main_13_archive_and_later_registered_identities():
    p=Path(__file__).parents[1]/'app/shared_contracts/archives/main_grammar_1_3.v1.json'
    v=json.loads(p.read_text());blocks=[]
    for name in v['component_order']:
        entry=v['components'][name];raw=base64.b64decode(entry['bytes_base64'],validate=True)
        assert hashlib.sha256(raw).hexdigest()==entry['raw_sha256'];blocks.append(raw)
    assert semantic_fingerprint(blocks)==v['grammar_sha256']=='14b41df8fe4f815e655b7b593afc66326c70896f58d699e6174b977b8cf51a14'
    from app.application.nlp.compositional_request_v1 import identity
    from app.application.nlp.normalized_request_v1 import identity as normalized
    from app.shared_contracts.isolated_soft_preference_grammar import REGISTRY
    assert identity()=='f281fd86497f991fb58b1f36a99a72a43e93ad824d4718dcff4ac880bd153543'
    assert normalized()=='c46688062562c228039e331635e4566db869238ae6b51c62e716bcf543040a59'
    assert REGISTRY['conversational-attribute-grammar-1.6.0'][0]=='e869b32876d3335781a8b10c7b13a6b2905402ce021aca5db6a6413bde53b0ae'
    assert REGISTRY['conversational-attribute-grammar-1.7.0'][0]=='899f67e37b3a39a24cfb766ea0384c42e42ff69701a84ba14597d6fd59eb4b67'
