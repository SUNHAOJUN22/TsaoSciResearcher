# Command cookbook

Paths vary by workstation/cluster; resolve them from the local environment.

## Gaussian utilities

```bash
# Convert checkpoint after identifying the correct Gaussian installation
formchk molecule.chk molecule.fchk

# Example cube generation; orbital index and grid must be reviewed
cubegen 0 MO=HOMO molecule.fchk homo.cube -2 h
cubegen 0 MO=LUMO molecule.fchk lumo.cube -2 h
```

## Skill helpers

```bash
python scripts/init_project.py project-name
python scripts/preflight_project.py project-name --json
python scripts/parse_gaussian.py job.log --json --out job-summary.json
python scripts/build_energy_profile.py energies.csv --column g_hartree --out figures/path
python scripts/validate_figure_spec.py figure-spec.yaml --json
python scripts/make_vmd_tcl.py figure-spec.yaml --out render.tcl --allow-missing
python scripts/qa_bundle.py figure-spec.yaml --json
```

## VMD headless render

```bash
vmd -dispdev text -e render.tcl
```

## Multiwfn

Use a version-reviewed menu input. A generic invocation is:

```bash
Multiwfn molecule.fchk < reviewed-menu.txt > analysis.log
```

Do not reuse an unverified menu script across Multiwfn versions. Preserve the
menu file, stdout and generated cubes as provenance artifacts.
