from tsao_science.workspace import root
from tsao_science.core.jsonio import read_json

def test_all_sources_have_one_authoritative_location():
    data=read_json(root()/'migration/source-lock.json')
    sources=data['sources']
    assert len(sources)==7
    assert len({item['destination'] for item in sources})==7
    for item in sources:
        assert len(item['sha'])==40
        assert (root()/item['destination']).is_dir()
    assert not (root()/'.gitmodules').exists()

def test_source_inventory_is_preserved():
    import json
    inventory=json.loads((root()/'migration/source-map.json').read_text())
    for source in inventory['sources']:
        for item in source['files']:
            assert (root()/item['target_path']).is_file(),item['target_path']
