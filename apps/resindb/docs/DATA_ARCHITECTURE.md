# ResinDB governed data architecture

## 1. Authoritative rule

`data/` is the authoritative, independently versioned ResinDB data layer. Production UI source files must not embed the complete resin catalog. A code commit may change parsers or views, but it must not silently change data meaning.

The canonical persisted representation is **UTF-8 JSON using the ResinDB versioned data envelope**. Spreadsheet files may be used for interchange, but they are not the authoritative repository format because they make schema, provenance, unit and diff review less reliable.

```text
data/
├── manifest.json
├── metadata.json
├── version.json
├── schemas/
│   ├── resin-data-document.schema.json
│   └── resin-product.schema.json
└── resins/
    ├── manifest.json
    ├── polymerDatabase.json
    ├── myLabUniverse.json
    ├── openMarketUniverse.json
    ├── resin-taxonomy.json
    ├── resin-category-aliases.json
    ├── resin-property-groups.json
    ├── resin-manufacturers.json
    ├── resin-references.json
    └── resin-network.json
```

## 2. Canonical document envelope

Every governed data file uses exactly six top-level fields:

```json
{
  "schemaVersion": "1.0.0",
  "dataKind": "resin-seed-products",
  "sourceType": "curated-demo",
  "recordStatus": "demo",
  "updatedAt": "2026-08-02",
  "data": []
}
```

| Field | Contract |
|---|---|
| `schemaVersion` | Exact data-envelope compatibility version |
| `dataKind` | Stable semantic identity of the payload |
| `sourceType` | Non-empty provenance/source category |
| `recordStatus` | `demo`, `reference`, `measured`, or `imported` |
| `updatedAt` | Real ISO calendar date, `YYYY-MM-DD` |
| `data` | Dataset-specific payload |

Unknown top-level fields are rejected by the JSON Schema and by repository validation.

## 3. Canonical product record

A product/grade record requires:

- stable `id`;
- `gradeName`;
- `manufacturerId` and display `manufacturer`;
- at least one unique category ID;
- `createdAt` and `updatedAt` ISO dates;
- at least one structured property.

A property value is not merely a number. It may include measurement context:

```json
{
  "value": 23.5,
  "unit": "MPa",
  "standard": "ISO 527",
  "temperature": 23,
  "instrument": "Universal testing machine",
  "referenceId": "ref-001",
  "mean": 23.5,
  "stdDev": 0.4,
  "count": 5
}
```

The canonical scalar `value` type is **string or finite number**. Boolean values and non-finite numbers are rejected because current scientific and display contracts are not defined for them.

## 4. Integrity and release manifests

`data/manifest.json` and `data/resins/manifest.json` record:

- file path;
- data kind;
- record status;
- record count where applicable;
- byte length;
- SHA-256 digest.

`npm run data:manifest` regenerates these values. `npm run validate:data` verifies the exact committed bytes and cross-document references.

## 5. Runtime loading

Vite serves `data/` at `/data/` during development and copies it unchanged to `dist/data/` for production. `loadResinDataCatalog()` fetches `/data/resins/*.json` with a bounded timeout and validates:

- canonical envelope version;
- non-empty source type;
- real ISO dates;
- product field and property-value types;
- duplicate identifiers;
- category cycles;
- network and catalog references.

If an external data asset fails, the loader records the exact failure and exposes a deterministic fallback status. Failure is visible and does not masquerade as a complete manufacturer dataset.

## 6. Change policy

1. Do not move governed records into TypeScript constants.
2. Do not edit data and code in a way that hides which layer changed.
3. Regenerate manifests whenever any governed data byte changes.
4. Increment schema versions for incompatible structural changes.
5. Preserve units, standards, temperatures, provenance and record status.
6. Keep `demo`, `reference`, `measured` and `imported` data semantically separate.
7. Never replace missing evidence with a numeric zero.
