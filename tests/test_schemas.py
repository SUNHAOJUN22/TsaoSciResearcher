import json, unittest
from pathlib import Path
import jsonschema
ROOT=Path(__file__).resolve().parents[1]
class TestSchemas(unittest.TestCase):
 def test_schemas_are_valid(self):
  for p in (ROOT/'schemas').glob('*.json'):
   schema=json.loads(p.read_text(encoding='utf-8')); jsonschema.Draft202012Validator.check_schema(schema)
if __name__=='__main__': unittest.main()
