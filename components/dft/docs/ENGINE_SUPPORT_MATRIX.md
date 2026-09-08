# DFT Engine and Capability Support Matrix

Support levels are evidence labels, not marketing labels:

- **L0_REFERENCE** — scientific documentation only;
- **L1_HANDOFF** — structured Manifest or downstream handoff;
- **L2_VALIDATED_ADAPTER** — deterministic preflight/Parser/validator with repository tests;
- **L3_EXECUTION_TESTED** — L2 plus immutable, scoped evidence from the real engine, build, hardware and site.

| Engine/capability | Current level | Deterministic implementation | Important limitation |
|---|---|---|---|
| Gaussian molecular DFT | L2 | input preflight, selected-field Parser, TS/IRC/thermochemistry/evidence validators | no licensed-engine regression in this repository environment |
| Multiwfn | L1–L2 | semantic recipe validation and provenance/isovalue/fragment checks | menu execution and numerical regression require a real versioned installation |
| VMD/Tachyon | L2 generation | Tcl generation and figure-manifest validation | no real cube-rendering regression here |
| VASP | L2 selected fields | INCAR/POSCAR/KPOINTS/POTCAR-TITEL preflight, fail-closed OUTCAR Parser and bridge | Parser is partial; POTCAR is never distributed |
| Quantum ESPRESSO `pw.x` | L2 selected fields | namelist/card preflight, fail-closed output Parser and bridge | pseudopotentials remain external; advanced modules are not parsed |
| CP2K Quickstep | L2 selected fields | basis/potential/grid/KIND/PBC preflight, fail-closed output Parser and bridge | advanced properties and version-specific syntax remain external |
| ORCA / Psi4 | L0–L1 | method-routing references and handoff only | no deterministic engine adapter yet |
| Structure preparation | L2 | geometry red flags, hashing, atom-order mapping and campaign expansion | no silent bond-order, charge, spin, oxidation-state or surface choice |
| DFT-labelled ML | L2 | leakage/fidelity validation, grouped splitting, NumPy ridge, model card and active-learning batch | DeepChem/GNN execution remains an optional external backend |
| Slurm/PBS/local execution | L2 | structured-argv manifests, scheduler/path/environment injection rejection, bound approval, scripts, arrays and provenance | no site is L3 until legal scheduler/engine regression is recorded |
| Hardware inventory | L2 non-invoking adapter | bounded environment/CPU/GPU/runtime availability and identity collection with `NOT_AVAILABLE` semantics and secret-value suppression | inventory does not execute an engine, prove device usability or measure performance |
| Automatic-tuning candidate generation | L2 deterministic planner; L1 candidate output | `generate_autotuning_candidates.py` locks scientific identity, requires an FP64 CPU reference, enforces hardware/memory/topology/policy limits and resets every candidate to `pending` | generated candidates are not submitted, executed, benchmarked or promoted automatically |
| GPU/native/edge acceleration planning | L2 planner | engine/stage/topology validation, library applicability, Python/native boundary, CPU fallback and matrix materialisation | no speedup is claimed without target measurements |
| Engine Parser contract and bridges | L2 | versioned Gaussian/VASP/QE/CP2K Parser result Schema and deterministic evidence bridges | Parser acceptance remains separate from scientific acceptance |
| Real benchmark evidence and qualification | L2 adapter; scoped L3 eligibility output | executable result/Policy Schemas, plan isolation, numerical equivalence, robust statistics, Ed25519 review, atomic content-addressed evidence and independent verification | fixtures do not establish speedup; public level never changes automatically |
| TST/Eyring and network validation | L2 | rates, detailed-balance closure and uncertainty propagation | downstream microkinetic/reactor models require separate validation |
| Cantera/RMG/Pyomo/CatMAP | L1 | provenance-rich handoff | export is not automatically a runnable validated mechanism |

A public capability may be registered as L3 only when its exact scope includes legal engine/version/build/site/hardware records, accepted CPU reference and repeats, numerical and Parser equivalence, artifact SHA-256, a verified content-addressed evidence root, an Ed25519-signed independent review bound to Policy/plan/candidates, and explicit capability registration without credentials or licensed files.

The repository currently publishes selected capabilities as `L2_VALIDATED_ADAPTER`; scoped qualification output is not public L3 registration.
