import { describe, expect, it } from 'vitest';
import { assessEvidenceForHumanReview, type RegulatoryEvidenceRecord } from '../regulatoryEvidence';

const digest = 'a'.repeat(64);
const record: RegulatoryEvidenceRecord = {
  evidenceId: 'E-1', standard: 'Declared standard', standardVersion: '2026',
  method: 'Instrumental method', sampleId: 'S-1', batchId: 'B-1', laboratoryId: 'L-1',
  laboratoryQualificationRef: 'LQ-1', testDate: '2026-08-11T00:00:00Z',
  reportArtifactSha256: digest, scope: 'screening-evidence-review',
  approvalAttestationId: 'APP-1',
  analytes: [{ analyte: 'X', result: 1, unit: 'mg/kg', limit: 2, limitUnit: 'mg/kg' }],
};
const context = {
  verifiedArtifactDigests: new Set([digest]), verifiedApprovalIds: new Set(['APP-1']),
  allowedScopes: new Set(['screening-evidence-review']), qualifiedLaboratoryRefs: new Set(['LQ-1']),
  nowIso: '2026-08-12T00:00:00Z',
};

describe('regulatory evidence boundary', () => {
  it('only marks evidence ready for human review and never issues a conclusion', () => {
    const result = assessEvidenceForHumanReview(record, context);
    expect(result.status).toBe('READY_FOR_QUALIFIED_HUMAN_REVIEW');
    expect(result.conclusionAllowed).toBe(false);
  });
  it('does not trust an unverified report digest', () => {
    const result = assessEvidenceForHumanReview(record, {...context, verifiedArtifactDigests: new Set<string>()});
    expect(result.status).toBe('NOT_ASSESSED');
    expect(result.reasonCodes).toContain('REPORT_ARTIFACT_NOT_VERIFIED');
  });
  it('rejects incompatible analyte units', () => {
    const result = assessEvidenceForHumanReview({...record, analytes:[{analyte:'X',result:1,unit:'mg/kg',limit:2,limitUnit:'ppm-volume'}]}, context);
    expect(result.status).toBe('INVALID_EVIDENCE');
  });
  it('rejects NaN instead of treating it as zero', () => {
    const result = assessEvidenceForHumanReview({...record, analytes:[{analyte:'X',result:Number.NaN,unit:'mg/kg',limit:2,limitUnit:'mg/kg'}]}, context);
    expect(result.status).toBe('INVALID_EVIDENCE');
  });
});
