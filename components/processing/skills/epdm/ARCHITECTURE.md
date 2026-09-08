# EPDM flagship architecture

EPDM extends the universal `tsao.process_package` contract with fourteen specialist modules covering customer CQA, catalyst/active sites, terpolymerization, molecular architecture, diene branching/gel, thermodynamics/rheology, reactor/mixing/heat removal, quench/deashing/devolatilization, recycle impurities, Mooney/compound/cure, dynamics, durability/customer qualification, scale-up/HSE and package acceptance.

The reference kernels are intentionally transparent and unit-declared. They are used for known-solution tests, contradiction detection and Gate preparation; they do not replace qualified multi-site population balances, commercial property packages, CFD, reaction calorimetry or physical qualification.

## V2 Phase A1 contract layer

`JSON/Schema` → `canonical_loader.py` → frozen `contracts.py` → temporary `registry.py` closure → immutable publication; `validation_v2.py` and `qualification_v2.py` consume the same governed contract boundary, while `migration.py` remains metadata-only for V1.

This layer has no numerical solver and is not imported by the frozen V1 `core.py` export surface.
Stable V2 objects reject unknown fields; experimental additions are confined to `extensions`.


The canonical loader rejects duplicate JSON object keys, non-finite values, unknown schema versions, dataclass type confusion, duplicate global IDs, local rate-law escapes and unresolved cross-registry references. It binds the complete source payload and core registry to separate SHA-256 identities so extensions remain traceable without changing the stable registry contract.

## Software-acceptance path

`CanonicalProjectSnapshot` → A2 generated state/network → full A3 41-binding audit → A4 adaptive analytic smoke → machine acceptance report. The acceptance route never re-indexes raw JSON after publication and is verified in source checkout, Wheel target installation and isolated virtual environment. Synthetic reference parameters remain explicitly non-calibrated.
