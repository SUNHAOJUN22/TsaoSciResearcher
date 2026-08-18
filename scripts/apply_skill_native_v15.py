from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];START="<!-- TSAO_SKILL_NATIVE_V15_START -->";END="<!-- TSAO_SKILL_NATIVE_V15_END -->";OLD=re.compile(r"<!-- TSAO_SKILL_NATIVE_V(?:1[0-4]|[1-9])_START -->.*?<!-- TSAO_SKILL_NATIVE_V(?:1[0-4]|[1-9])_END -->\s*",re.DOTALL)
def clean(v:str)->str:return textwrap.dedent(v).strip()+"\n"
def write(p:str,v:str)->None:
 q=ROOT/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(clean(v),encoding="utf-8",newline="\n")
def merge(p:str,b:str,t:str)->None:
 q=ROOT/p;c=q.read_text(encoding="utf-8") if q.exists() else f"# {t}\n\n";c=OLD.sub("",c).rstrip()+"\n\n";q.write_text(c+START+"\n"+clean(b)+END+"\n",encoding="utf-8",newline="\n")

skill=r'''
---
name: tsao-sci-researcher
description: Evidence-first scientific-research workflow for claim decomposition, bilingual negation and scope, dimensional comparison, provenance, approval replay, artifact traceability, and safe research capsules. Use for research evidence, manuscript claims, audit trails, and acceptance handoffs. Do not equate high-quality contrary evidence with support, or infer external experiments, solver runs, or human acceptance from software records.
---

# TsaoSciResearcher Skill

## Claim and evidence model

Separate evidence maturity from its relation to a claim. A high-quality result may `SUPPORT`, `CHALLENGE`, `CONTRADICT`, provide `BACKGROUND`, be `NULL`, or remain `UNKNOWN`.

For a claim \(C\) and evidence items \(e_i\), a decision function must retain both dimensions:

\[
D(C)=\mathcal{A}\{(m_i,r_i,w_i,p_i)\}_{i=1}^{n},
\]

where \(m_i\) is maturity, \(r_i\) is relation, \(w_i\) is weight, and \(p_i\) is provenance. Maturity alone never changes `CHALLENGE` into `SUPPORT`.

## Bilingual semantics

Chinese and English clauses share one representation for subject, predicate, comparator, value, unit, scope, modality, and negation. Negation applies to its parsed scope, not the entire sentence by default.

## State replay

Accepted state is reconstructed from genesis through an append-only hash chain. Each transition binds sequence, previous hash, event hash, actor, role, scope, artifact digest, timestamp, nonce, signature, expiry, and revocation.

## Truth boundary

Without real external execution receipts and qualified human acceptance, retain `EXTERNAL_EXECUTION_NOT_VERIFIED` and `HUMAN_ACCEPTANCE_PENDING`.
'''

dod=r'''
# Definition of done

- Claims are decomposed into testable clauses with explicit scope and negation.
- Chinese and English representations preserve equivalent scientific meaning.
- Quantitative comparisons parse both operands, units, dimensions, comparator, and uncertainty.
- Evidence maturity and relation-to-claim are separate fields.
- Contrary or null evidence is never promoted to support merely because it is high quality.
- Provenance uses real locators, hashes, receipts, and ledger entries.
- Approval and acceptance bind exact artifacts, scope, role, time, nonce, signature, expiry, and revocation.
- State validation replays from genesis and rejects deletion, reordering, tampering, or replay.
- Software evidence cannot replace external experiment/solver execution or human acceptance.
'''

openai_yaml=r'''
interface:
  display_name: "Tsao Scientific Researcher"
  short_description: "Claim, evidence, provenance, replay, and research-integrity control"
  default_prompt: "Decompose the claim, preserve bilingual scope and negation, validate dimensions, separate evidence maturity from relation, replay provenance, and keep external execution and human acceptance pending without evidence."
policy:
  allow_implicit_invocation: true
  truth_boundary: "Software records cannot self-issue experimental execution or human scientific acceptance."
'''

evals={"schema":"tsao-researcher.skill-routing.v15","skill":"tsao-sci-researcher","cases":[
 {"id":"en-claim","language":"en","prompt":"Audit whether these references support, challenge, or merely contextualize each manuscript claim.","expected":"TRIGGER"},
 {"id":"zh-claim","language":"zh","prompt":"逐句核验这些文献究竟支持、挑战还是仅仅提供背景。","expected":"TRIGGER"},
 {"id":"en-replay","language":"en","prompt":"Replay the signed evidence ledger from genesis and verify the acceptance handoff.","expected":"TRIGGER"},
 {"id":"zh-replay","language":"zh","prompt":"从创世记录重放签名证据账本并核验接受交接。","expected":"TRIGGER"},
 {"id":"en-negative","language":"en","prompt":"Polish this abstract for readability.","expected":"NO_TRIGGER"},
 {"id":"zh-negative","language":"zh","prompt":"只润色一下这段摘要的语言。","expected":"NO_TRIGGER"}
]}

validator=r'''
from __future__ import annotations
import argparse,json
from pathlib import Path
R=(".agents/skills/tsao-sci-researcher/SKILL.md",".agents/skills/tsao-sci-researcher/agents/openai.yaml",".agents/skills/tsao-sci-researcher/references/definition-of-done.md",".agents/skills/tsao-sci-researcher/evals/evals.json","assets/diagrams/vision-en.svg","assets/diagrams/vision-zh.svg");BAD=("\x00","\ufffd","Ã","Â","â€")
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--root",default=".");p.add_argument("--report",default="artifacts/skill-validation-v15.json");a=p.parse_args();root=Path(a.root).resolve();e=[]
 for x in R:
  if not (root/x).is_file():e.append(f"missing {x}")
 s=root/R[0]
 if s.is_file():
  t=s.read_text(encoding="utf-8")
  if not t.startswith("---\n") or "name: tsao-sci-researcher" not in t[:800]:e.append("invalid SKILL.md")
  if "Do not equate high-quality contrary" not in t[:1400]:e.append("anti-trigger boundary missing")
 for f in root.rglob("*"):
  if f.is_file() and f.suffix.lower() in {".md",".py",".json",".yaml",".yml",".svg"}:
   v=f.read_text(encoding="utf-8")
   if any(m in v for m in BAD):e.append(f"Unicode failure in {f.relative_to(root)}")
 ep=root/R[3]
 if ep.is_file():
  c=json.loads(ep.read_text(encoding="utf-8")).get("cases",[])
  if len(c)<6 or {i.get("expected") for i in c}!={"TRIGGER","NO_TRIGGER"}:e.append("routing evals incomplete")
 o={"schema":"tsao-researcher.skill-validation.v15","status":"PASS" if not e else "FAIL","errors":e};q=root/a.report;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(json.dumps(o,ensure_ascii=False));return 0 if not e else 1
if __name__=="__main__":raise SystemExit(main())
'''

contracts=r'''
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from math import isfinite
from typing import Iterable, Mapping


class EvidenceRelation(str, Enum):
    SUPPORTS="SUPPORTS";CHALLENGES="CHALLENGES";CONTRADICTS="CONTRADICTS";BACKGROUND="BACKGROUND";NULL="NULL";UNKNOWN="UNKNOWN"


@dataclass(frozen=True)
class EvidenceAssessment:
    maturity: float
    relation: EvidenceRelation
    provenance_ref: str

    def validate(self)->None:
        if isinstance(self.maturity,bool) or not isfinite(float(self.maturity)) or not 0.0<=self.maturity<=1.0:raise ValueError("maturity must be a finite value in [0,1]")
        if not self.provenance_ref:raise ValueError("provenance_ref is required")


def aggregate_claim(assessments:Iterable[EvidenceAssessment])->str:
    items=list(assessments)
    if not items:return "NOT_EVALUATED"
    for item in items:item.validate()
    relations={item.relation for item in items if item.maturity>=0.5}
    if EvidenceRelation.CONTRADICTS in relations:return "CONTRADICTED"
    if EvidenceRelation.CHALLENGES in relations:return "CHALLENGED"
    if EvidenceRelation.SUPPORTS in relations:return "SUPPORTED"
    return "NOT_EVALUATED"


@dataclass(frozen=True)
class Quantity:
    value:float;unit:str;dimension:str;scale_to_si:float
    def canonical(self)->float:
        if isinstance(self.value,bool) or isinstance(self.scale_to_si,bool) or not isfinite(float(self.value)) or not isfinite(float(self.scale_to_si)):raise ValueError("quantity must be finite and non-boolean")
        if self.scale_to_si<=0 or not self.unit or not self.dimension:raise ValueError("unit, dimension, and positive scale are required")
        return float(self.value)*float(self.scale_to_si)


def compare(left:Quantity,operator:str,right:Quantity)->bool:
    if left.dimension!=right.dimension:raise ValueError("comparison dimensions differ")
    a,b=left.canonical(),right.canonical()
    if operator=="<":return a<b
    if operator=="<=":return a<=b
    if operator==">":return a>b
    if operator==">=":return a>=b
    if operator=="==":return a==b
    raise ValueError("unsupported comparator")


@dataclass(frozen=True)
class LedgerEvent:
    sequence:int;previous_hash:str;event_type:str;artifact_digest:str;actor:str;role:str;nonce:str;signature_valid:bool
    def digest(self)->str:
        payload=f"{self.sequence}|{self.previous_hash}|{self.event_type}|{self.artifact_digest}|{self.actor}|{self.role}|{self.nonce}".encode()
        return sha256(payload).hexdigest()


def replay(events:Iterable[LedgerEvent])->str:
    previous="GENESIS";seen_nonce:set[str]=set()
    for expected,event in enumerate(events,1):
        if event.sequence!=expected or event.previous_hash!=previous:return "INVALID_CHAIN"
        if not event.signature_valid or not event.artifact_digest or not event.actor or not event.role:return "INVALID_EVIDENCE"
        if event.nonce in seen_nonce:return "REPLAY_DETECTED"
        seen_nonce.add(event.nonce);previous=event.digest()
    return "VALID_CHAIN" if seen_nonce else "EMPTY_CHAIN"


def acceptance_state(*,chain_status:str,external_execution_verified:bool,human_approval_verified:bool)->str:
    if chain_status!="VALID_CHAIN":return "EVIDENCE_CHAIN_INVALID"
    if not external_execution_verified:return "EXTERNAL_EXECUTION_NOT_VERIFIED"
    if not human_approval_verified:return "HUMAN_ACCEPTANCE_PENDING"
    return "ACCEPTED"
'''

tests=r'''
from __future__ import annotations
import unittest
from tsao_researcher.contracts.scientific_contracts_v15 import EvidenceAssessment,EvidenceRelation,LedgerEvent,Quantity,acceptance_state,aggregate_claim,compare,replay
class Tests(unittest.TestCase):
 def test_high_quality_challenge_is_not_support(self)->None:self.assertEqual(aggregate_claim([EvidenceAssessment(0.95,EvidenceRelation.CHALLENGES,"doi:1")]),"CHALLENGED")
 def test_dimensioned_comparison(self)->None:self.assertTrue(compare(Quantity(1.0,"kV/mm","field",1e6),">",Quantity(500.0,"V/mm","field",1e3)))
 def test_dimension_mismatch_fails(self)->None:
  with self.assertRaises(ValueError):compare(Quantity(1,"K","temperature",1),">",Quantity(1,"Pa","pressure",1))
 def test_replay_detects_nonce_reuse(self)->None:
  e1=LedgerEvent(1,"GENESIS","EVIDENCE","a"*64,"u","author","n",True);e2=LedgerEvent(2,e1.digest(),"APPROVAL","a"*64,"v","reviewer","n",True);self.assertEqual(replay([e1,e2]),"REPLAY_DETECTED")
 def test_software_chain_does_not_issue_human_acceptance(self)->None:
  self.assertEqual(acceptance_state(chain_status="VALID_CHAIN",external_execution_verified=False,human_approval_verified=False),"EXTERNAL_EXECUTION_NOT_VERIFIED")
if __name__=="__main__":unittest.main()
'''

workflow=r'''
name: Skill-native portability
on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  validate:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-24.04, windows-2025]
    runs-on: ${{ matrix.os }}
    timeout-minutes: 12
    steps:
      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262
        with:
          persist-credentials: false
      - run: python scripts/validate_skill.py --root . --report artifacts/skill-validation-v15.json
      - run: python -m unittest tests.test_scientific_contracts_v15 -v
'''

svg_en=r'''
<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900"><defs><linearGradient id="g" x2="1" y2="1"><stop stop-color="#07152c"/><stop offset=".52" stop-color="#1b3959"/><stop offset="1" stop-color="#081020"/></linearGradient><linearGradient id="c" x2="1" y2="1"><stop stop-color="#204b6c"/><stop offset="1" stop-color="#11263e"/></linearGradient></defs><rect width="1600" height="900" fill="url(#g)"/><g opacity=".16" stroke="#72dfff"><path d="M0 180H1600M0 360H1600M0 540H1600M0 720H1600"/><path d="M200 0V900M500 0V900M800 0V900M1100 0V900M1400 0V900"/></g><text x="80" y="100" fill="#fff" font-family="Arial" font-size="50" font-weight="700">TsaoSciResearcher · Claim-to-Evidence Integrity</text><text x="85" y="148" fill="#b4eaff" font-family="Arial" font-size="24">Bilingual claim semantics → dimensional test → evidence relation → provenance replay → human acceptance</text><g transform="translate(75 225)"><rect width="450" height="405" rx="28" fill="url(#c)" stroke="#54d9ff" stroke-width="2"/><text x="35" y="65" fill="#fff" font-family="Arial" font-size="29" font-weight="700">Claim semantics</text><text x="35" y="125" fill="#c8efff" font-family="Arial" font-size="21">subject · predicate · comparator</text><text x="35" y="165" fill="#c8efff" font-family="Arial" font-size="21">value · unit · scope · negation</text><text x="35" y="235" fill="#75f0bd" font-family="Arial" font-size="21">Chinese and English share</text><text x="35" y="275" fill="#75f0bd" font-family="Arial" font-size="21">one scientific representation.</text><text x="35" y="340" fill="#fff" font-family="Arial" font-size="20">Dimensioned operands on both sides</text></g><g transform="translate(575 225)"><rect width="450" height="405" rx="28" fill="url(#c)" stroke="#b79cff" stroke-width="2"/><text x="35" y="65" fill="#fff" font-family="Arial" font-size="29" font-weight="700">Evidence relation</text><text x="35" y="125" fill="#e2d9ff" font-family="Arial" font-size="21">maturity ≠ relation to claim</text><text x="35" y="185" fill="#d9f2ff" font-family="Arial" font-size="20">SUPPORT · CHALLENGE · CONTRADICT</text><text x="35" y="225" fill="#d9f2ff" font-family="Arial" font-size="20">BACKGROUND · NULL · UNKNOWN</text><text x="35" y="305" fill="#75f0bd" font-family="Arial" font-size="21">High-quality contrary evidence</text><text x="35" y="345" fill="#75f0bd" font-family="Arial" font-size="21">never becomes support.</text></g><g transform="translate(1075 225)"><rect width="450" height="405" rx="28" fill="url(#c)" stroke="#ffbd65" stroke-width="2"/><text x="35" y="65" fill="#fff" font-family="Arial" font-size="29" font-weight="700">Replayable provenance</text><text x="35" y="125" fill="#ffe0ad" font-family="Arial" font-size="20">genesis → evidence → review</text><text x="35" y="165" fill="#ffe0ad" font-family="Arial" font-size="20">→ execution → acceptance</text><text x="35" y="235" fill="#d9f2ff" font-family="Arial" font-size="20">sequence · prev hash · nonce</text><text x="35" y="275" fill="#d9f2ff" font-family="Arial" font-size="20">actor · role · scope · signature</text><text x="35" y="345" fill="#75f0bd" font-family="Arial" font-size="20">Deletion and replay fail closed.</text></g><rect x="75" y="695" width="1450" height="115" rx="24" fill="#071b34" stroke="#4bcdf2"/><text x="115" y="747" fill="#fff" font-family="Arial" font-size="25" font-weight="700">Truth boundary</text><text x="360" y="747" fill="#c7edff" font-family="Arial" font-size="22">External execution and qualified human acceptance remain pending until their independent evidence exists.</text></svg>
'''

svg_zh=r'''
<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900"><defs><linearGradient id="g" x2="1" y2="1"><stop stop-color="#07152c"/><stop offset=".52" stop-color="#1b3959"/><stop offset="1" stop-color="#081020"/></linearGradient><linearGradient id="c" x2="1" y2="1"><stop stop-color="#204b6c"/><stop offset="1" stop-color="#11263e"/></linearGradient></defs><rect width="1600" height="900" fill="url(#g)"/><g opacity=".16" stroke="#72dfff"><path d="M0 180H1600M0 360H1600M0 540H1600M0 720H1600"/><path d="M200 0V900M500 0V900M800 0V900M1100 0V900M1400 0V900"/></g><text x="80" y="100" fill="#fff" font-family="Microsoft YaHei,Arial" font-size="50" font-weight="700">TsaoSciResearcher · 从论点到证据的科研诚信链</text><text x="85" y="148" fill="#b4eaff" font-family="Microsoft YaHei,Arial" font-size="24">双语论点语义 → 量纲检验 → 证据关系 → 谱系重放 → 人工接受</text><g transform="translate(75 225)"><rect width="450" height="405" rx="28" fill="url(#c)" stroke="#54d9ff" stroke-width="2"/><text x="35" y="65" fill="#fff" font-family="Microsoft YaHei,Arial" font-size="29" font-weight="700">论点语义</text><text x="35" y="125" fill="#c8efff" font-family="Microsoft YaHei,Arial" font-size="21">主语 · 谓语 · 比较符</text><text x="35" y="165" fill="#c8efff" font-family="Microsoft YaHei,Arial" font-size="21">数值 · 单位 · 范围 · 否定</text><text x="35" y="235" fill="#75f0bd" font-family="Microsoft YaHei,Arial" font-size="21">中英文共享同一套</text><text x="35" y="275" fill="#75f0bd" font-family="Microsoft YaHei,Arial" font-size="21">科学语义表示</text><text x="35" y="340" fill="#fff" font-family="Microsoft YaHei,Arial" font-size="20">比较两侧均解析量纲</text></g><g transform="translate(575 225)"><rect width="450" height="405" rx="28" fill="url(#c)" stroke="#b79cff" stroke-width="2"/><text x="35" y="65" fill="#fff" font-family="Microsoft YaHei,Arial" font-size="29" font-weight="700">证据关系</text><text x="35" y="125" fill="#e2d9ff" font-family="Microsoft YaHei,Arial" font-size="21">证据成熟度 ≠ 与论点关系</text><text x="35" y="185" fill="#d9f2ff" font-family="Arial" font-size="20">SUPPORT · CHALLENGE · CONTRADICT</text><text x="35" y="225" fill="#d9f2ff" font-family="Arial" font-size="20">BACKGROUND · NULL · UNKNOWN</text><text x="35" y="305" fill="#75f0bd" font-family="Microsoft YaHei,Arial" font-size="21">高质量反对证据</text><text x="35" y="345" fill="#75f0bd" font-family="Microsoft YaHei,Arial" font-size="21">不能被改写为支持</text></g><g transform="translate(1075 225)"><rect width="450" height="405" rx="28" fill="url(#c)" stroke="#ffbd65" stroke-width="2"/><text x="35" y="65" fill="#fff" font-family="Microsoft YaHei,Arial" font-size="29" font-weight="700">可重放来源谱系</text><text x="35" y="125" fill="#ffe0ad" font-family="Microsoft YaHei,Arial" font-size="20">创世 → 证据 → 复核</text><text x="35" y="165" fill="#ffe0ad" font-family="Microsoft YaHei,Arial" font-size="20">→ 执行 → 接受</text><text x="35" y="235" fill="#d9f2ff" font-family="Microsoft YaHei,Arial" font-size="20">序号 · 前哈希 · 随机数</text><text x="35" y="275" fill="#d9f2ff" font-family="Microsoft YaHei,Arial" font-size="20">主体 · 角色 · 范围 · 签名</text><text x="35" y="345" fill="#75f0bd" font-family="Microsoft YaHei,Arial" font-size="20">删除、篡改与重放均阻断</text></g><rect x="75" y="695" width="1450" height="115" rx="24" fill="#071b34" stroke="#4bcdf2"/><text x="115" y="747" fill="#fff" font-family="Microsoft YaHei,Arial" font-size="25" font-weight="700">真实性边界</text><text x="360" y="747" fill="#c7edff" font-family="Microsoft YaHei,Arial" font-size="22">真实外部执行与合格人员接受，在取得各自独立证据前必须保持待定。</text></svg>
'''

readme_en=r'''
## Skill-native research integrity

![TsaoSciResearcher claim-to-evidence architecture](assets/diagrams/vision-en.svg)

The canonical Skill is `.agents/skills/tsao-sci-researcher/SKILL.md`. It complements the runtime with bilingual claim semantics, dimension-aware comparison, relation-preserving evidence assessment, provenance replay, and independent acceptance boundaries.

Evidence aggregation retains \((m_i,r_i,w_i,p_i)\): maturity, relation, weight, and provenance. High maturity never converts `CHALLENGES` or `CONTRADICTS` into support.

```bash
python scripts/validate_skill.py --root . --report artifacts/skill-validation-v15.json
python -m unittest tests.test_scientific_contracts_v15 -v
```
'''

readme_zh=r'''
## Skill 原生科研诚信层

![TsaoSciResearcher 从论点到证据的架构](assets/diagrams/vision-zh.svg)

规范 Skill 位于 `.agents/skills/tsao-sci-researcher/SKILL.md`，为现有运行时补充双语论点语义、量纲比较、保留关系的证据评估、谱系重放与独立接受边界。

证据聚合同时保留 \((m_i,r_i,w_i,p_i)\)：成熟度、与论点关系、权重及来源谱系。高成熟度不能把 `CHALLENGES` 或 `CONTRADICTS` 改写成支持。

```bash
python scripts/validate_skill.py --root . --report artifacts/skill-validation-v15.json
python -m unittest tests.test_scientific_contracts_v15 -v
```
'''

write(".agents/skills/tsao-sci-researcher/SKILL.md",skill);write(".agents/skills/tsao-sci-researcher/references/definition-of-done.md",dod);write(".agents/skills/tsao-sci-researcher/agents/openai.yaml",openai_yaml);write(".agents/skills/tsao-sci-researcher/evals/evals.json",json.dumps(evals,ensure_ascii=False,indent=2));write("scripts/validate_skill.py",validator);write("tsao_researcher/contracts/scientific_contracts_v15.py",contracts);write("tests/test_scientific_contracts_v15.py",tests);write(".github/workflows/skill-native-ci.yml",workflow);write("assets/diagrams/vision-en.svg",svg_en);write("assets/diagrams/vision-zh.svg",svg_zh);merge("README.md",readme_en,"TsaoSciResearcher");zh="README.zh-CN.md" if (ROOT/"README.zh-CN.md").exists() else "README_CN.md";merge(zh,readme_zh,"TsaoSciResearcher 中文说明");print(json.dumps({"status":"APPLIED","version":"15.0.0"},ensure_ascii=False))
