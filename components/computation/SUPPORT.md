# Support

## Start with the verified paths

Use the README, `docs/coverage-matrix.md`, `docs/scientific-trust.md`, and `docs/release.md` before opening an issue. Run the canonical verification command when reporting repository behavior:

```bash
python -m pip install -e '.[validation,quality]'
python scripts/verify_all.py --profile all
```

## Public issue routing

Use the structured issue forms for reproducible software defects, scientific-validity concerns, and bounded capability requests. Blank public issues are disabled so reports include version, evidence, assumptions, and claim boundaries.

Do not use public issues for vulnerabilities, credentials, license files, private datasets, proprietary solver inputs, or production DCS/SIS information. Follow `SECURITY.md` instead.

## Support boundary

Support covers repository orchestration, contracts, routing, deterministic fixtures, parsers, validation controls, packaging, and release evidence. It does not provide third-party solver licenses, production HPC administration, plant-control authorization, or certification of user-supplied scientific models and data.
