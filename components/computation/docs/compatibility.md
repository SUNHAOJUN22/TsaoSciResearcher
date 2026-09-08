# Compatibility policy

## Patch

Patch releases fix defects, strengthen validation, add evidence, or improve documentation without intentionally breaking valid public contracts.

## Minor

Minor releases may add backward-compatible fields, capabilities, workflows, adapters, commands, and evidence formats. New required fields need a migration path or a new Schema version.

## Major

Major releases may remove fields, change state semantics, redefine acceptance, or otherwise break valid contracts. Migration guidance and an explicit compatibility review are required.

## Schema

Every machine-readable artifact declares a Schema version. Unknown fields are rejected where a contract is security- or science-sensitive. Additive optional fields are preferred. A required-field change must not be silently applied to existing user artifacts.

## CLI

Documented command names, exit-code meanings, and JSON keys are public behavior. Human-readable prose may improve, but machine-readable output changes follow semantic versioning.

## Adapter

Adapter maturity and certification are separate from solver availability. `A5` requires versioned live evidence. Adapter slugs are durable identifiers and must not be reused for a different solver or semantic surface.

## Registry identifiers

Capability IDs, workflow slugs, adapter slugs, state names, and published evidence keys must not be reused after removal. Deprecation must precede removal when a compatibility path exists.
