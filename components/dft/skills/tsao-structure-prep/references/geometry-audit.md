# Geometry and Atom-Mapping Audit

Use deterministic geometry checks before engine input generation. Minimum distances and radius-based bonds are triage signals only. They do not establish bond order, oxidation state, protonation, coordination, or electronic structure.

Atom ordering must be preserved across counterpoise fragments, charge-density differences, NEB images, phonon displacements, and restart chains. When reordering is unavoidable, store an explicit mapping and validate element identity.
