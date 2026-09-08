import { describe, expect, it } from "vitest";
import {
  assessProductForScreening,
  summarizeScreening,
  type ScreeningPropertyValue,
} from "../qaScreening";

const thresholds = { mfrMin: 0.8, mfrMax: 25, tensileMinMpa: 20 };

function product(properties: Record<string, ScreeningPropertyValue>) {
  return { id: "P-1", gradeName: "Example", properties };
}

function mfr(value: unknown = 10): ScreeningPropertyValue {
  return {
    value,
    unit: "g/10 min",
    temperature: 230,
    load: 2.16,
    method: "declared MFR method",
    referenceId: "REF-MFR-1",
    batchId: "BATCH-1",
  };
}

function tensile(value: unknown = 25, unit = "MPa"): ScreeningPropertyValue {
  return {
    value,
    unit,
    method: "declared tensile method",
    referenceId: "REF-TENSILE-1",
    sampleId: "SAMPLE-1",
  };
}

describe("qaScreening fail-closed contract", () => {
  it("keeps an empty property set NOT_ASSESSED", () => {
    const result = assessProductForScreening(product({}), thresholds);
    expect(result.status).toBe("NOT_ASSESSED");
    expect(result.reasonCodes).toContain("MISSING_PROPERTY");
    expect(result.assessedCriteria).toBe(0);
  });

  it("resolves Chinese aliases through the shared canonical resolver", () => {
    const result = assessProductForScreening(
      product({
        熔体质量流动速率: mfr("12.5"),
        拉伸屈服强度: tensile(25),
      }),
      thresholds,
    );
    expect(result.status).toBe("ASSESSED_WITHIN_DECLARED_THRESHOLD");
    expect(result.assessedCriteria).toBe(2);
  });

  it("requires MFR temperature and load", () => {
    const result = assessProductForScreening(
      product({
        MFR: {
          ...mfr(),
          temperature: undefined,
          load: undefined,
        },
        "Tensile Strength": tensile(),
      }),
      thresholds,
    );
    expect(result.status).toBe("NOT_ASSESSED");
    expect(result.reasonCodes).toContain("MISSING_MFR_TEMPERATURE");
    expect(result.reasonCodes).toContain("MISSING_MFR_LOAD");
  });

  it.each([
    ["method", { method: undefined }, "MISSING_METHOD"],
    ["source", { referenceId: undefined, sourceUrl: undefined }, "MISSING_SOURCE"],
    ["sample", { sampleId: undefined, batchId: undefined }, "MISSING_SAMPLE_OR_BATCH_ID"],
  ])("keeps data without %s evidence NOT_ASSESSED", (_label, patch, reason) => {
    const result = assessProductForScreening(
      product({
        MFR: { ...mfr(), ...(patch as Partial<ScreeningPropertyValue>) },
        "Tensile Strength": tensile(),
      }),
      thresholds,
    );
    expect(result.status).toBe("NOT_ASSESSED");
    expect(result.reasonCodes).toContain(reason);
  });

  it("converts GPa to MPa rather than changing only the label", () => {
    const result = assessProductForScreening(
      product({ MFR: mfr(), "Tensile Strength": tensile(0.025, "GPa") }),
      thresholds,
    );
    expect(result.criteria[1].canonicalValue).toBe(25);
    expect(result.status).toBe("ASSESSED_WITHIN_DECLARED_THRESHOLD");
  });

  it.each(["NaN", "Infinity", "", "12 MPa"])(
    "rejects non-strict numeric input %s",
    (value) => {
      const result = assessProductForScreening(
        product({ MFR: mfr(value), "Tensile Strength": tensile() }),
        thresholds,
      );
      expect(result.status).toBe("NOT_ASSESSED");
      expect(result.reasonCodes).toContain("NON_FINITE_VALUE");
    },
  );

  it("does not let a missing criterion improve the result", () => {
    const complete = assessProductForScreening(
      product({ MFR: mfr(), "Tensile Strength": tensile() }),
      thresholds,
    );
    const missing = assessProductForScreening(product({ MFR: mfr() }), thresholds);
    expect(complete.status).toBe("ASSESSED_WITHIN_DECLARED_THRESHOLD");
    expect(missing.status).toBe("NOT_ASSESSED");
  });

  it("reports a known threshold excursion even when another field is unknown", () => {
    const result = assessProductForScreening(product({ MFR: mfr(100) }), thresholds);
    expect(result.status).toBe("ASSESSED_OUTSIDE_DECLARED_THRESHOLD");
  });

  it("rejects an inverted threshold range", () => {
    const result = assessProductForScreening(product({}), {
      mfrMin: 25,
      mfrMax: 1,
      tensileMinMpa: 20,
    });
    expect(result.status).toBe("NOT_ASSESSED");
    expect(result.reasonCodes).toContain("INVALID_THRESHOLD_CONFIGURATION");
  });

  it("summarizes outside and unknown states conservatively", () => {
    const within = assessProductForScreening(
      product({ MFR: mfr(), "Tensile Strength": tensile() }),
      thresholds,
    );
    const unknown = assessProductForScreening(product({}), thresholds);
    expect(summarizeScreening([within, unknown]).status).toBe("NOT_ASSESSED");
  });
});
