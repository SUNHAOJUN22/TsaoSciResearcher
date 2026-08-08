from __future__ import annotations

from html import escape
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CONFIG = {'repo': 'TsaoSciResearcher', 'readmes': {'zh': 'README.zh-CN.md', 'en': 'README.md'}, 'english_mirrors': ['README_EN.md'], 'paths': {'zh': 'docs/localized-vision/researcher-vision-zh.svg', 'en': 'docs/localized-vision/researcher-vision-en.svg'}, 'anchors': {'zh': '</div>', 'en': '</div>'}, 'zh': {'eyebrow': 'TSAO SCI RESEARCHER · 证据优先科研控制层', 'title': '从科学问题到可证伪、可交接的研究路线', 'subtitle': '问题/观测量 · 模型合同 · 证据冲突 · UQ/尺度桥 · 受控执行回执', 'vision_label': '项目愿景', 'vision': '让科研智能体不仅“会回答”，更能声明证据、限制、反例和下一步验证', 'vision_note': '策略和 PASS 不等于科学真理；外部计算、实验和人工审批保持独立。', 'formula_label': '核心科研推理合同', 'formula_rows': ['S(c|q,o,e)=wqR(q,c)+woR(o,c)+weM(e,c)−wxC(c)', 'Σy≈JΣθJᵀ+Σnum+Σsample+Σmodel+Σtransfer   ·   G=min(gquantity,gapplicability,gevidence,gidentifiability,gbridge)'], 'cards': [{'title': '问题与观测量', 'subtitle': 'Question · Observable', 'formula': 'x=(v,u,d)', 'formula_note': '数值、单位、量纲', 'lines': ['决策问题', '验收阈值', '反例条件']}, {'title': '模型合同', 'subtitle': 'State · Mechanism · Constraint', 'formula': 'ẋ=f(x,u,θ)', 'formula_note': '最低充分可证伪模型', 'lines': ['状态与控制量', '守恒和边界', '竞争机理']}, {'title': '证据三分', 'subtitle': 'Support · Challenge · Unknown', 'formula': 'E=(E₊,E₋,E₀)', 'formula_note': '冲突不被平均', 'lines': ['引用与位置', '支持/反驳', '未决与缺口']}, {'title': 'UQ 与尺度桥', 'subtitle': 'Uncertainty · Applicability', 'formula': 'Ubridge²=Us²+Um²+Uc²+Ut²', 'formula_note': '微观不能直接跳工业', 'lines': ['采样/模型误差', '适用域外推', '桥变量与闭合']}, {'title': '受控交接', 'subtitle': 'Handoff · Receipt · Review', 'formula': 'H=SHA256(strategy∥input∥receipt)', 'formula_note': '自动批准固定为 false', 'lines': ['外部执行计划', '结果哈希回执', '合格人工审批']}], 'disclaimer': 'AI辅助概念设计 · 非科学数据 · 公式对应软件合同而非运行结果', 'footer': 'TsaoSciResearcher · 中文科研智能体愿景', 'accessible_title': 'TsaoSciResearcher 中文证据优先科研路线愿景图', 'accessible_desc': '从问题观测量、模型合同、证据三分、不确定度尺度桥到受控交接的中文概念设计图。', 'readme_heading': '中文项目愿景图：从科学问题到可证伪、可交接的研究路线', 'readme_alt': 'TsaoSciResearcher 中文证据优先科研控制架构', 'readme_note': '图中公式映射能力路由、量纲、证据冲突、不确定度、尺度桥和回执验证代码；图不是论文证据、实验结果或自动科学批准。'}, 'en': {'eyebrow': 'TSAO SCI RESEARCHER · EVIDENCE-FIRST RESEARCH CONTROL LAYER', 'title': 'From Scientific Questions to Falsifiable, Transferable Research Plans', 'subtitle': 'Question/observable · model contract · evidence conflict · UQ/scale bridge · guarded execution receipt', 'vision_label': 'VISION', 'vision': 'Move research agents beyond fluent answers toward explicit evidence, limits, counterexamples and next validation', 'vision_note': 'A strategy or PASS label is not scientific truth; external computation, experiment and human approval remain separate.', 'formula_label': 'CORE RESEARCH-REASONING CONTRACTS', 'formula_rows': ['S(c|q,o,e)=wqR(q,c)+woR(o,c)+weM(e,c)−wxC(c)', 'Σy≈JΣθJᵀ+Σnum+Σsample+Σmodel+Σtransfer   ·   G=min(gquantity,gapplicability,gevidence,gidentifiability,gbridge)'], 'cards': [{'title': 'Question & observable', 'subtitle': 'Question · Observable', 'formula': 'x=(v,u,d)', 'formula_note': 'value, unit, dimension', 'lines': ['decision question', 'acceptance threshold', 'falsification condition']}, {'title': 'Model contract', 'subtitle': 'State · Mechanism · Constraint', 'formula': 'ẋ=f(x,u,θ)', 'formula_note': 'minimum falsifiable model', 'lines': ['state and controls', 'conservation/boundary', 'competing mechanisms']}, {'title': 'Evidence triad', 'subtitle': 'Support · Challenge · Unknown', 'formula': 'E=(E₊,E₋,E₀)', 'formula_note': 'conflict is not averaged', 'lines': ['citation & location', 'support/refutation', 'unknowns and gaps']}, {'title': 'UQ & scale bridge', 'subtitle': 'Uncertainty · Applicability', 'formula': 'Ubridge²=Us²+Um²+Uc²+Ut²', 'formula_note': 'no micro-to-plant jump', 'lines': ['sampling/model error', 'domain extrapolation', 'bridge variables/closure']}, {'title': 'Guarded handoff', 'subtitle': 'Handoff · Receipt · Review', 'formula': 'H=SHA256(strategy∥input∥receipt)', 'formula_note': 'automatic approval is false', 'lines': ['external execution plan', 'result-hash receipt', 'qualified human review']}], 'disclaimer': 'AI-ASSISTED CONCEPTUAL DESIGN · NOT SCIENTIFIC DATA', 'footer': 'TsaoSciResearcher · English research-agent vision', 'accessible_title': 'TsaoSciResearcher English evidence-first research-plan vision', 'accessible_desc': 'English conceptual design from questions and observables through model contracts, evidence triads, uncertainty and scale bridges to guarded handoff.', 'readme_heading': 'Project vision: from scientific questions to falsifiable, transferable research plans', 'readme_alt': 'TsaoSciResearcher English evidence-first research control architecture', 'readme_note': 'The equations map to capability routing, dimensional checks, evidence conflict, uncertainty, scale bridges and receipt verification. The figure is not paper evidence, an experiment or automatic scientific approval.'}}

FONT = "Inter,'Noto Sans SC','Noto Sans CJK SC','Microsoft YaHei','PingFang SC','WenQuanYi Micro Hei','Segoe UI',Arial,sans-serif"
MATH_FONT = "'STIX Two Math','Cambria Math','Noto Sans Math','Noto Sans SC',serif"


def text(value: object) -> str:
    return escape(str(value), quote=True)


def render_svg(spec: dict[str, object]) -> str:
    cards = list(spec['cards'])
    colors = ['#22d3ee', '#818cf8', '#c084fc', '#34d399', '#fbbf24']
    x_positions = [78, 370, 662, 954, 1246]
    card_markup: list[str] = []
    for index, card in enumerate(cards):
        x = x_positions[index]
        color = colors[index]
        lines = list(card['lines'])
        formula = card['formula']
        card_markup.append(f'''<g transform="translate({x} 250)" filter="url(#shadow)">
  <rect width="250" height="390" rx="26" fill="#0d2034" stroke="{color}" stroke-width="2"/>
  <circle cx="42" cy="42" r="23" fill="{color}"/><text x="42" y="48" text-anchor="middle" class="step">{index + 1}</text>
  <text x="24" y="93" class="card-title">{text(card['title'])}</text>
  <text x="24" y="124" class="card-sub">{text(card['subtitle'])}</text>
  <rect x="20" y="151" width="210" height="76" rx="15" fill="#081522" stroke="#334155"/>
  <text x="125" y="184" text-anchor="middle" class="formula-small">{text(formula)}</text>
  <text x="125" y="207" text-anchor="middle" class="micro">{text(card['formula_note'])}</text>
  <circle cx="34" cy="274" r="6" fill="{color}"/><text x="51" y="280" class="body">{text(lines[0])}</text>
  <circle cx="34" cy="316" r="6" fill="{color}"/><text x="51" y="322" class="body">{text(lines[1])}</text>
  <circle cx="34" cy="358" r="6" fill="{color}"/><text x="51" y="364" class="body">{text(lines[2])}</text>
</g>''')
    arrows = []
    for x in [330, 622, 914, 1206]:
        arrows.append(f'<path d="M{x} 445h28" stroke="#94a3b8" stroke-width="4"/><path d="M{x+28} 445l-12-8v16z" fill="#94a3b8"/>')

    formula_rows = list(spec['formula_rows'])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" role="img" aria-labelledby="title desc">
<title id="title">{text(spec['accessible_title'])}</title>
<desc id="desc">{text(spec['accessible_desc'])}</desc>
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#06121f"/><stop offset="0.55" stop-color="#10233f"/><stop offset="1" stop-color="#1f2554"/></linearGradient>
  <radialGradient id="halo" cx="50%" cy="50%" r="60%"><stop offset="0" stop-color="#22d3ee" stop-opacity=".30"/><stop offset="1" stop-color="#22d3ee" stop-opacity="0"/></radialGradient>
  <filter id="shadow" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="14" stdDeviation="18" flood-color="#020617" flood-opacity=".42"/></filter>
  <pattern id="grid" width="38" height="38" patternUnits="userSpaceOnUse"><path d="M38 0H0V38" fill="none" stroke="#dbeafe" stroke-opacity=".055"/></pattern>
  <style>
    text{{font-family:{FONT}}}
    .eyebrow{{font-size:17px;letter-spacing:3.5px;font-weight:800;fill:#67e8f9}}
    .title{{font-size:50px;font-weight:850;fill:#f8fafc}}
    .subtitle{{font-size:21px;fill:#cbd5e1}}
    .vision{{font-size:18px;font-weight:700;fill:#dbeafe}}
    .card-title{{font-size:23px;font-weight:800;fill:#f8fafc}}
    .card-sub{{font-size:15px;fill:#9fb1c8}}
    .body{{font-size:15px;fill:#d5deea}}
    .micro{{font-size:12px;fill:#8ea2ba}}
    .step{{font-size:15px;font-weight:900;fill:#07111f}}
    .formula{{font-family:{MATH_FONT};font-size:22px;fill:#e0f2fe}}
    .formula-small{{font-family:{MATH_FONT};font-size:17px;fill:#f0f9ff}}
    .disclaimer{{font-size:12px;font-weight:850;letter-spacing:1.1px;fill:#111827}}
  </style>
</defs>
<rect width="1600" height="900" fill="url(#bg)"/>
<rect width="1600" height="900" fill="url(#grid)"/>
<ellipse cx="800" cy="188" rx="610" ry="190" fill="url(#halo)"/>
<g transform="translate(78 54)"><text class="eyebrow">{text(spec['eyebrow'])}</text><text class="title" y="63">{text(spec['title'])}</text><text class="subtitle" y="105">{text(spec['subtitle'])}</text></g>
<g transform="translate(1030 68)" filter="url(#shadow)"><rect width="490" height="104" rx="24" fill="#0a1829" stroke="#334155"/><text x="24" y="36" class="vision">{text(spec['vision_label'])}</text><text x="24" y="70" class="formula-small">{text(spec['vision'])}</text><text x="24" y="92" class="micro">{text(spec['vision_note'])}</text></g>
{''.join(card_markup)}
{''.join(arrows)}
<g transform="translate(78 686)" filter="url(#shadow)"><rect width="1444" height="128" rx="25" fill="#091827" stroke="#334155"/><text x="24" y="34" class="vision">{text(spec['formula_label'])}</text><text x="24" y="68" class="formula">{text(formula_rows[0])}</text><text x="24" y="100" class="formula">{text(formula_rows[1])}</text></g>
<g transform="translate(78 842)"><rect width="640" height="28" rx="14" fill="#f8fafc" opacity=".95"/><text x="320" y="19" text-anchor="middle" class="disclaimer">{text(spec['disclaimer'])}</text><text x="1440" y="20" text-anchor="end" class="micro">{text(spec['footer'])}</text></g>
</svg>'''


def localized_block(language: str, image_path: str, spec: dict[str, object]) -> str:
    marker = f'LOCALIZED_VISION_{language.upper()}'
    return f'''<!-- {marker}:START -->
## {spec['readme_heading']}

<p align="center">
  <img src="{image_path}" width="100%" alt="{spec['readme_alt']}">
</p>

> {spec['readme_note']}

<!-- {marker}:END -->'''


def replace_or_insert(path: Path, language: str, image_path: str, spec: dict[str, object], anchor: str) -> None:
    content = path.read_text(encoding='utf-8')
    marker = f'LOCALIZED_VISION_{language.upper()}'
    pattern = re.compile(rf'<!-- {re.escape(marker)}:START -->.*?<!-- {re.escape(marker)}:END -->', flags=re.DOTALL)
    block = localized_block(language, image_path, spec)
    if pattern.search(content):
        content = pattern.sub(block, content, count=1)
    elif anchor and anchor in content:
        content = content.replace(anchor, anchor + '\n\n' + block, 1)
    elif '</div>' in content[:5000]:
        content = content.replace('</div>', '</div>\n\n' + block, 1)
    else:
        first_break = content.find('\n\n')
        if first_break < 0:
            raise RuntimeError(f'{path}: no safe insertion point')
        content = content[:first_break] + '\n\n' + block + content[first_break:]
    path.write_text(content, encoding='utf-8', newline='\n')


def main() -> None:
    for language in ('zh', 'en'):
        svg_path = ROOT / CONFIG['paths'][language]
        svg_path.parent.mkdir(parents=True, exist_ok=True)
        svg_path.write_text(render_svg(CONFIG[language]), encoding='utf-8', newline='\n')
        parsed = ET.parse(svg_path).getroot()
        if not parsed.tag.endswith('svg') or not parsed.attrib.get('viewBox'):
            raise RuntimeError(f'{svg_path}: invalid SVG root/viewBox')
        raw = svg_path.read_text(encoding='utf-8')
        if '\ufffd' in raw or '<script' in raw.lower() or 'javascript:' in raw.lower():
            raise RuntimeError(f'{svg_path}: unsafe or corrupted content')

    replace_or_insert(ROOT / CONFIG['readmes']['zh'], 'zh', CONFIG['paths']['zh'], CONFIG['zh'], CONFIG['anchors']['zh'])
    replace_or_insert(ROOT / CONFIG['readmes']['en'], 'en', CONFIG['paths']['en'], CONFIG['en'], CONFIG['anchors']['en'])
    for mirror in CONFIG.get('english_mirrors', []):
        replace_or_insert(ROOT / mirror, 'en', CONFIG['paths']['en'], CONFIG['en'], CONFIG['anchors']['en'])

    for language in ('zh', 'en'):
        target = ROOT / CONFIG['readmes'][language]
        if CONFIG['paths'][language] not in target.read_text(encoding='utf-8'):
            raise RuntimeError(f'{target}: localized image reference missing')
    print(f"localized README vision generated for {CONFIG['repo']}")


if __name__ == '__main__':
    main()
