import json,tempfile,unittest
from pathlib import Path
from tsao_researcher.vnext import init,transition,verify,route,handoff
class VNextRelease(unittest.TestCase):
 def test_router(self):
  self.assertEqual(route('做PRISMA系统综述')['primary_workflow'],'systematic-review');self.assertEqual(route('只解释已有GROMACS轨迹，不运行模拟')['primary_workflow'],'data-analysis');self.assertEqual(route('帮我处理事情')['primary_workflow'],'unknown')
 def test_state_and_approval(self):
  with tempfile.TemporaryDirectory() as d:
   r=init('x','what is tested?',d);transition(r,'planned','approved');transition(r,'running','start');self.assertTrue(verify(r)['valid']);
   with self.assertRaises(ValueError):transition(r,'accepted','skip')
 def test_handoff(self):
  with tempfile.TemporaryDirectory() as d:
   r=init('x','what is tested?',d);(r/'data/a.txt').write_text('x');a=handoff(r,'computation/a.json','real question','energy','quantum',['DFT'],['data/a.txt']);b=handoff(r,'computation/b.json','real question','energy','quantum',['DFT'],['data/a.txt']);self.assertNotEqual(a['handoff_id'],b['handoff_id']);self.assertEqual(len(a['inputs'][0]['sha256']),64)
 def test_capability_count(self):
  idx=json.loads((Path(__file__).resolve().parents[1]/'capabilities/v2/index.json').read_text());self.assertEqual(idx['total'],340);self.assertEqual(idx['domain_added'],164)
if __name__=='__main__':unittest.main()
