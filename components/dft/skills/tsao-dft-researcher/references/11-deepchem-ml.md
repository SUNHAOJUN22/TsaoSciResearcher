# DFT descriptors and molecular machine learning

Use ML only when the scientific target, sample unit and generalization domain are
clear.

## Dataset contract

- one row/sample definition and structure identifier;
- target source, units and uncertainty;
- descriptor provenance and calculation level;
- duplicate, conformer and stereoisomer policy;
- missing-value/exclusion log;
- split strategy registered before feature selection.

## Leakage-resistant splitting

Prefer scaffold, chemical-family, catalyst-family, reaction-template, time or
source-group splits over random rows when related structures would otherwise
cross train/test boundaries. Keep the test set untouched until the final model.

## Modeling ladder

1. simple mean/linear baseline;
2. interpretable descriptors + regularized linear/RF/GBDT baseline;
3. fingerprints or graph models when data size supports them;
4. transfer learning only with documented domain match;
5. ablation and uncertainty analysis.

Report MAE/RMSE/R² for regression or appropriate classification metrics, across
folds/seeds with variability. High R² on a tiny or leaked test set is not strong
evidence.

## DFT descriptor caution

HOMO/LUMO, charges, Fukui indices, ESP extrema, MPI and structural descriptors
may be collinear and method-dependent. Record level of theory and remove target
leakage (for example, a descriptor algebraically derived from the label).

## Interpretation

SHAP, impurity importance and permutation importance are different quantities.
State which is used. They explain model behavior under the dataset, not chemical
causality. Confirm proposed mechanism links with targeted calculations or
experiments.
