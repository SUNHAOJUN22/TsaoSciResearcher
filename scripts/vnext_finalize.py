#!/usr/bin/env python3
from __future__ import annotations
import json,re,subprocess,sys
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
VERSION='0.4.0'

def main():
    (ROOT/'VERSION').write_text(VERSION+'\n',encoding='utf-8')
    skill=ROOT/'SKILL.md'; text=skill.read_text(encoding='utf-8'); text=re.sub(r'(?m)^version:\s*[^\n]+$',f'version: {VERSION}',text,count=1); skill.write_text(text,encoding='utf-8')
    agent_path=ROOT/'agents/openai.yaml'; agent=yaml.safe_load(agent_path.read_text(encoding='utf-8')); agent['version']=VERSION; agent_path.write_text(yaml.safe_dump(agent,sort_keys=False,allow_unicode=True),encoding='utf-8')
    py=ROOT/'pyproject.toml'; text=py.read_text(encoding='utf-8'); text=re.sub(r'(?m)^version\s*=\s*"[^"]+"',f'version = "{VERSION}"',text,count=1); py.write_text(text,encoding='utf-8')
    manifest_path=ROOT/'manifest.json'; manifest=json.loads(manifest_path.read_text(encoding='utf-8')); manifest.update({'version':VERSION,'entrypoint':'SKILL.md','agent_metadata':'agents/openai.yaml','capability_index':'capability-index/capabilities.json','capability_index_v2':'capabilities/v2/index.json','project_state_dir':'.tsao-research','compatibility':{'codex':True,'claude_code':True,'open_agent_skills':True,'windows':True,'linux':True,'macos':True}}); manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    subprocess.run([sys.executable,'scripts/generate_checksums.py','--write'],cwd=ROOT,check=True)
    print(json.dumps({'version':VERSION,'metadata_aligned':True,'checksum_written':True}))
if __name__=='__main__':main()
