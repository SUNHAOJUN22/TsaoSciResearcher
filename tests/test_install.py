import subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TestInstall(unittest.TestCase):
 def test_custom_install(self):
  with tempfile.TemporaryDirectory() as d:
   dst=Path(d)/'skill'
   subprocess.run([sys.executable,str(ROOT/'scripts/install.py'),'--target',str(dst),'--force','--validate'],check=True)
   self.assertTrue((dst/'SKILL.md').exists())
if __name__=='__main__': unittest.main()
