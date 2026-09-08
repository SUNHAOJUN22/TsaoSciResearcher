# Historical `POE_Kinetics.m` isolation and equation-review record

Status: **`CONTROLLED_HISTORICAL_EVIDENCE`**  
Execution status: **not used by the trusted Python reference kernel**  
Scientific approval: **`NOT_EVALUATED`**

## Audited questions

1. `M_5 = x_1(:,16)./(x_1(:,16)+x_1(:,16))` evaluates to 0.5 whenever the denominator is nonzero. The intended second index must be recovered from the report/equation source before reuse.
2. The historical `f(16)` expression applies the comonomer concentration to only the last term as written. Parentheses, reaction order and units require equation-to-code reconciliation.
3. `f(2)=0` fixes an ethylene state. This may represent a specific semi-batch boundary condition, but its experimental basis and applicability were not encoded.
4. The contract language requested multi-active-site parameter allocation, while the final report describes a single-site metallocene model. This is an explicit deviation, not a silent simplification.
5. Historical rate constants were hard-coded and do not provide a reproducible estimator, uncertainty interval or independent validation split.
6. The historical source uses a GBK/GB18030-family encoding and must be transcoded with byte identity retained.

## Remediation rule

The alpha.6 kernel in `../core.py` is an independent, transparent single-site moment-model fixture with synthetic parameters. Historical values can enter a project only through a parameter passport, unit reconciliation, identifiability review, independent validation and Gate approval.
