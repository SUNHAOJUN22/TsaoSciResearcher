/**
 * Evidence-completeness gate for regulatory/test records.
 *
 * This module does not issue a compliance decision. It only determines whether
 * a record is complete enough for qualified human review, using artifact and
 * approval IDs already verified by an external trust service.
 */
export type EvidenceReviewStatus =
  | 'READY_FOR_QUALIFIED_HUMAN_REVIEW'
  | 'NOT_ASSESSED'
  | 'INVALID_EVIDENCE';

export interface AnalyteEvidence {
  analyte: string;
  result: number;
  unit: string;
  limit: number;
  limitUnit: string;
}

export interface RegulatoryEvidenceRecord {
  evidenceId: string;
  standard: string;
  standardVersion: string;
  method: string;
  sampleId: string;
  batchId: string;
  laboratoryId: string;
  laboratoryQualificationRef: string;
  testDate: string;
  reportArtifactSha256: string;
  scope: string;
  approvalAttestationId: string;
  analytes: AnalyteEvidence[];
}

export interface VerifiedEvidenceContext {
  verifiedArtifactDigests: ReadonlySet<string>;
  verifiedApprovalIds: ReadonlySet<string>;
  allowedScopes: ReadonlySet<string>;
  qualifiedLaboratoryRefs: ReadonlySet<string>;
  nowIso: string;
}

export interface EvidenceReviewDecision {
  status: EvidenceReviewStatus;
  conclusionAllowed: false;
  reasonCodes: string[];
  assessedAnalytes: number;
  evidenceId?: string;
  scope?: string;
}

const SHA256 = /^[0-9a-f]{64}$/;

function finiteReal(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function nonEmpty(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

function sameUnit(left: string, right: string): boolean {
  return left.trim().replace(/\s+/g, ' ') === right.trim().replace(/\s+/g, ' ');
}

export function assessEvidenceForHumanReview(
  record: Partial<RegulatoryEvidenceRecord> | null | undefined,
  context: VerifiedEvidenceContext,
): EvidenceReviewDecision {
  if (!record) {
    return {
      status: 'NOT_ASSESSED',
      conclusionAllowed: false,
      reasonCodes: ['EVIDENCE_RECORD_MISSING'],
      assessedAnalytes: 0,
    };
  }
  const reasons: string[] = [];
  const requiredStrings: Array<keyof RegulatoryEvidenceRecord> = [
    'evidenceId', 'standard', 'standardVersion', 'method', 'sampleId', 'batchId',
    'laboratoryId', 'laboratoryQualificationRef', 'testDate',
    'reportArtifactSha256', 'scope', 'approvalAttestationId',
  ];
  for (const field of requiredStrings) {
    if (!nonEmpty(record[field])) reasons.push(`MISSING_${String(field).toUpperCase()}`);
  }
  if (nonEmpty(record.reportArtifactSha256)) {
    if (!SHA256.test(record.reportArtifactSha256)) {
      reasons.push('REPORT_ARTIFACT_SHA256_INVALID');
    } else if (!context.verifiedArtifactDigests.has(record.reportArtifactSha256)) {
      reasons.push('REPORT_ARTIFACT_NOT_VERIFIED');
    }
  }
  if (nonEmpty(record.approvalAttestationId)
      && !context.verifiedApprovalIds.has(record.approvalAttestationId)) {
    reasons.push('APPROVAL_ATTESTATION_NOT_VERIFIED');
  }
  if (nonEmpty(record.scope) && !context.allowedScopes.has(record.scope)) {
    reasons.push('SCOPE_NOT_AUTHORIZED');
  }
  if (nonEmpty(record.laboratoryQualificationRef)
      && !context.qualifiedLaboratoryRefs.has(record.laboratoryQualificationRef)) {
    reasons.push('LABORATORY_QUALIFICATION_NOT_VERIFIED');
  }
  if (nonEmpty(record.testDate)) {
    const testTime = Date.parse(record.testDate);
    const nowTime = Date.parse(context.nowIso);
    if (!Number.isFinite(testTime) || !Number.isFinite(nowTime)) {
      reasons.push('TEST_DATE_INVALID');
    } else if (testTime > nowTime) {
      reasons.push('TEST_DATE_IN_FUTURE');
    }
  }
  const analytes = Array.isArray(record.analytes) ? record.analytes : [];
  if (analytes.length === 0) reasons.push('ANALYTES_MISSING');
  const seen = new Set<string>();
  for (const [index, analyte] of analytes.entries()) {
    if (!analyte || !nonEmpty(analyte.analyte)) {
      reasons.push(`ANALYTE_${index}_NAME_MISSING`);
      continue;
    }
    const key = analyte.analyte.trim().toLocaleLowerCase();
    if (seen.has(key)) reasons.push(`ANALYTE_${index}_DUPLICATE`);
    seen.add(key);
    if (!finiteReal(analyte.result) || !finiteReal(analyte.limit)) {
      reasons.push(`ANALYTE_${index}_NONFINITE`);
    }
    if (!nonEmpty(analyte.unit) || !nonEmpty(analyte.limitUnit)) {
      reasons.push(`ANALYTE_${index}_UNIT_MISSING`);
    } else if (!sameUnit(analyte.unit, analyte.limitUnit)) {
      reasons.push(`ANALYTE_${index}_UNIT_MISMATCH`);
    }
  }
  const invalid = reasons.some((reason) =>
    reason.includes('INVALID') || reason.includes('NONFINITE') || reason.includes('MISMATCH')
    || reason.includes('DUPLICATE') || reason.includes('FUTURE'));
  return {
    status: reasons.length === 0
      ? 'READY_FOR_QUALIFIED_HUMAN_REVIEW'
      : invalid ? 'INVALID_EVIDENCE' : 'NOT_ASSESSED',
    conclusionAllowed: false,
    reasonCodes: reasons,
    assessedAnalytes: analytes.length,
    evidenceId: nonEmpty(record.evidenceId) ? record.evidenceId : undefined,
    scope: nonEmpty(record.scope) ? record.scope : undefined,
  };
}
