import json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
from scripts.capability_io import load_capabilities, capability_index
class TestCapabilities(unittest.TestCase):
 def test_count_and_uniqueness(self):
  data=capability_index(); caps=load_capabilities()
  self.assertEqual(len(caps),158); self.assertEqual(data['total'],158); self.assertEqual(len({c['slug'] for c in caps}),158)
 def test_required_fields(self):
  for c in load_capabilities():
   for k in ['id','slug','name_zh','description_zh','workflow','inputs','outputs','risk_level','references']: self.assertTrue(c.get(k),f'{c.get("slug")} missing {k}')
if __name__=='__main__': unittest.main()
