import { describe, expect, it } from "vitest";

import {
  authorityBoundary,
  canonicalizeQuantity,
  eligibleForRanking,
  evaluateFormula,
  screeningStatus,
} from "../../src/lib/scientificContractsV16.mjs";

describe("ResinDB V16 scientific contracts", () => {
  it("converts density value and unit together", () => {
    expect(
      canonicalizeQuantity({ value: 905, unit: "kg/m3" }, "g/cm3"),
    ).toMatchObject({
      status: "VALID",
      value: 0.905,
      unit: "g/cm3",
      dimension: "density",
    });
  });

  it("converts GPa to MPa numerically", () => {
    expect(
      canonicalizeQuantity({ value: 1.5, unit: "GPa" }, "MPa").value,
    ).toBe(1500);
  });

  it("keeps missing formula input distinct from a true zero", () => {
    expect(evaluateFormula([undefined], (value) => value).status).toBe(
      "UNKNOWN",
    );
    expect(evaluateFormula([0], (value) => value)).toEqual({
      status: "OK",
      value: 0,
    });
  });

  it("does not reward a record with a missing cost criterion", () => {
    expect(
      eligibleForRanking({ benefit: 10 }, ["benefit", "cost"]),
    ).toEqual({ eligible: false, missing: ["cost"] });
  });

  it("keeps unassessed data out of declared-threshold PASS", () => {
    expect(
      screeningStatus({ assessed: false, value: 0, minimum: 0, maximum: 1 }),
    ).toBe("NOT_ASSESSED");
  });

  it("does not claim certification or material release", () => {
    expect(authorityBoundary).toBe("SOFTWARE_VALIDATED_FOR_SCREENING");
  });
});
