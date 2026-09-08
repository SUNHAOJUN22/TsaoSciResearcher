# 40 Inventive Principles / 40 个发明原理

Each principle is a directional transformation, not a complete engineering design. A valid TRIZ answer must translate the selected principle into geometry, material, field, timing, control, interface, or process changes and then validate the resulting mechanism.

| # | Principle | 中文 | Engineering prompt |
|---:|---|---|---|
| 1 | Segmentation | 分割 | divide into independent, modular, replaceable, or graded parts |
| 2 | Taking out / Extraction | 抽取 | separate the harmful/interfering part or isolate the useful property |
| 3 | Local quality | 局部质量 | make regions non-uniform so each performs under favorable local conditions |
| 4 | Asymmetry | 非对称 | replace symmetry with direction/load-adapted asymmetry |
| 5 | Merging | 合并 | combine similar objects/operations in space or time |
| 6 | Universality | 多用性 | make one element perform several functions; eliminate redundancy |
| 7 | Nested doll | 嵌套 | place one object inside another; use cavities/telescoping |
| 8 | Anti-weight | 反重量 | compensate weight using buoyancy, lift, suspension, balance |
| 9 | Preliminary anti-action | 预先反作用 | introduce compensation before expected harm occurs |
| 10 | Preliminary action | 预先作用 | perform required change or preparation in advance |
| 11 | Beforehand cushioning | 预先防护 | prepare buffering, backup, or damage-limiting means |
| 12 | Equipotentiality | 等势 | remove unnecessary work against a potential gradient |
| 13 | The other way round / Inversion | 反向 | reverse action, motion, orientation, active/passive roles |
| 14 | Spheroidality / Curvature | 曲面化 | move from straight/planar to curved, spherical, rolling, rotary forms |
| 15 | Dynamics | 动态化 | make geometry, properties, or connections adjustable by operating state |
| 16 | Partial or excessive action | 未达到或过度作用 | deliberately overshoot/undershoot when exact action is difficult |
| 17 | Another dimension | 多维化 | add dimensions, layers, orientations, or use the opposite surface |
| 18 | Mechanical vibration | 机械振动 | use oscillation, resonance, ultrasound, frequency control |
| 19 | Periodic action | 周期性作用 | replace continuous action with pulses/cycles/pauses |
| 20 | Continuity of useful action | 有效作用连续性 | eliminate idle states; keep useful work continuous |
| 21 | Skipping / Rushing through | 快速通过 | traverse harmful/unstable regime rapidly |
| 22 | Convert harm into benefit | 变害为利 | redirect/combine/amplify a harmful factor so it becomes useful |
| 23 | Feedback | 反馈 | sense output/state and adapt action |
| 24 | Intermediary | 中介 | introduce a temporary carrier, interface, converter, or medium |
| 25 | Self-service | 自服务 | make system clean, calibrate, maintain, or protect itself using own resources |
| 26 | Copying | 复制 | replace costly/inaccessible object with model, image, signal, surrogate |
| 27 | Cheap short-living objects | 廉价短寿命 | use disposable/renewable inexpensive elements instead of one durable expensive element |
| 28 | Mechanics substitution | 机械系统替代 | replace mechanical action with optical, acoustic, electrical, magnetic, EM, etc. |
| 29 | Pneumatics and hydraulics | 气压与液压 | use gas/liquid structures, pressure, jets, cushions, fluidic control |
| 30 | Flexible shells and thin films | 柔性壳与薄膜 | replace bulky structures with membranes, skins, films, flexible barriers |
| 31 | Porous materials | 多孔材料 | introduce/grade/fill/exploit pores and capillary structure |
| 32 | Color changes | 颜色改变 | change optical properties, transparency, contrast, emissivity, indication |
| 33 | Homogeneity | 同质性 | match interacting materials/properties to reduce incompatibility |
| 34 | Discarding and recovering | 抛弃与再生 | remove fulfilled parts or regenerate consumed elements during operation |
| 35 | Parameter changes | 参数改变 | change state, concentration, density, flexibility, temperature, etc. |
| 36 | Phase transitions | 相变 | exploit latent heat, volume, solubility, crystallization, phase-boundary effects |
| 37 | Thermal expansion | 热膨胀 | exploit differential expansion/contraction or bimetal-like response |
| 38 | Strong oxidants | 强氧化剂 | increase oxidation/reactivity only where justified and safe |
| 39 | Inert atmosphere | 惰性环境 | use inert/vacuum/neutral/protective environment or additives |
| 40 | Composite materials | 复合材料 | replace homogeneous material with designed multi-material architecture |

## Translation contract

For every chosen principle, complete this chain:

```text
Principle
→ concrete physical or process modification
→ changed interaction/mechanism
→ predicted useful effect
→ new harmful effect / secondary contradiction
→ governing check / experiment / simulation
```

Do not stop at “use segmentation”, “add feedback”, “make it dynamic”, or similar labels.

## Combination discipline

- Several principles may combine in one concept.
- Matrix-selected principles are suggestions, not exhaustive candidates.
- Principles outside the matrix cell may be used, but label them `direct-principle search` or `inferred`.
- When all concepts derive from one principle family, force at least one structurally different route (separation, Su-Field standard, mechanism substitution, supersystem, or trimming).

## Provenance

Adapted from the MIT-licensed `Antropocosmist/triz-engineering-solver/resources/40_principles.md`; principle ordering and core meanings are cross-checked against the Altshuller Institute public 40 Principles summary. See `sources.md`.
