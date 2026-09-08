import assert from "node:assert/strict";

import {
  authorityBoundary,
  canonicalizeQuantity,
  eligibleForRanking,
  evaluateFormula,
  screeningStatus,
} from "../src/lib/scientificContractsV16.mjs";

assert.equal(
  canonicalizeQuantity({ value: 905, unit: "kg/m3" }, "g/cm3").value,
  0.905,
);
assert.equal(
  canonicalizeQuantity({ value: 1.5, unit: "GPa" }, "MPa").value,
  1500,
);
assert.equal(evaluateFormula([undefined], (value) => value).status, "UNKNOWN");
assert.equal(evaluateFormula([0], (value) => value).value, 0);
assert.deepEqual(eligibleForRanking({ benefit: 10 }, ["benefit", "cost"]), {
  eligible: false,
  missing: ["cost"],
});
assert.equal(
  screeningStatus({ assessed: false, value: 0, minimum: 0, maximum: 1 }),
  "NOT_ASSESSED",
);
assert.equal(authorityBoundary, "SOFTWARE_VALIDATED_FOR_SCREENING");
console.log("ResinDB scientific contracts V16: PASS");
