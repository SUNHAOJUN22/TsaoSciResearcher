# Error recovery

Use the exact error/log evidence. Change one variable at a time and retain the
failed input/output.

## Gaussian categories

- SCF nonconvergence or unstable state;
- geometry step/coordinate failure;
- optimization step limit;
- wrong or missing basis/ECP;
- disk, memory, checkpoint or scratch failure;
- wrong charge/multiplicity;
- TS converged to minimum or wrong mode;
- IRC step failure;
- TD root/state switching;
- numerical low-frequency or integration-grid issues.

A retry is not automatically a scientific fix. For example, `SCF=XQC` may help
convergence but does not prove the electronic state is correct. After any retry,
repeat the full validation ladder.

## Multiwfn/VMD categories

- wavefunction file lacks orbitals/state information;
- menu script incompatible with program version;
- density and property cubes use different grids;
- orbital sign/indices swapped;
- blank or clipped render;
- color scale automatically reset;
- comparison views/cameras differ.

Stop on ambiguous menu behavior or provenance mismatch. Do not “make the image
work” by changing scientific isovalues without recording and justifying it.
