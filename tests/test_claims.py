import json, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TestClaims(unittest.TestCase):
 def test_claim_evidence_link(self):
  with tempfile.TemporaryDirectory() as d:
   ev=Path(d)/'e.jsonl'; cl=Path(d)/'c.jsonl'
   ev.write_text(json.dumps({'schema_version':'1.0','evidence_id':'EV-1','evidence_type':'sourced_fact','title':'source','source':{'kind':'paper','locator':'10.1000/test'},'supports_claims':['CL-1'],'limitations':[]})+'\n')
   cl.write_text(json.dumps({'schema_version':'1.0','claim_id':'CL-1','statement':'A supported statement','claim_type':'sourced_fact','evidence_ids':['EV-1'],'assumptions':[],'status':'checked','limitations':[]})+'\n')
   subprocess.run([sys.executable,str(ROOT/'scripts/validate_evidence.py'),str(ev)],check=True)
   subprocess.run([sys.executable,str(ROOT/'scripts/validate_claims.py'),str(cl),'--evidence',str(ev)],check=True)
if __name__=='__main__': unittest.main()
