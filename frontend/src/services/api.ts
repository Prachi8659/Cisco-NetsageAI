import axios from 'axios';
import type { 
  Case, 
  CaseCreateInput, 
  PktFile, 
  PktAnalysisResult,
  CiscoEvidence,
  CiscoEvidenceCreateInput,
  RuleEngineResult,
  AiDiagnosisResult,
  DiagnosisComparisonResult,
  HumanReviewRecord,
  HumanReviewCreateInput,
  VerificationResponse 
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const client = axios.create({
  baseURL: API_BASE_URL,
});

export const apiService = {
  // Cases API
  async getCases(category?: string): Promise<Case[]> {
    const params = category ? { category } : {};
    const res = await client.get<Case[]>('/cases', { params });
    return res.data;
  },

  async getCaseById(id: number | string): Promise<Case> {
    const res = await client.get<Case>(`/cases/${id}`);
    return res.data;
  },

  async createCase(data: CaseCreateInput): Promise<Case> {
    const res = await client.post<Case>('/cases', data);
    return res.data;
  },

  async updateCase(id: number | string, data: Partial<CaseCreateInput & { status: string }>): Promise<Case> {
    const res = await client.patch<Case>(`/cases/${id}`, data);
    return res.data;
  },

  async deleteCase(id: number | string): Promise<void> {
    await client.delete(`/cases/${id}`);
  },

  // .pkt Upload & Download API
  async uploadPktFile(caseId: number | string, file: File): Promise<PktFile> {
    const formData = new FormData();
    formData.append('file', file);

    const res = await client.post<PktFile>(`/cases/${caseId}/pkt`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },

  async getPktMetadata(caseId: number | string): Promise<PktFile> {
    const res = await client.get<PktFile>(`/cases/${caseId}/pkt`);
    return res.data;
  },

  getPktDownloadUrl(caseId: number | string): string {
    return `${API_BASE_URL}/cases/${caseId}/pkt/download`;
  },

  async deletePktFile(caseId: number | string): Promise<void> {
    await client.delete(`/cases/${caseId}/pkt`);
  },

  async analyzePktFile(caseId: number | string): Promise<PktAnalysisResult> {
    const res = await client.post<PktAnalysisResult>(`/cases/${caseId}/pkt/analyze`);
    return res.data;
  },

  // Cisco Show-Command Evidence API
  async getEvidence(caseId: number | string): Promise<CiscoEvidence[]> {
    const res = await client.get<CiscoEvidence[]>(`/cases/${caseId}/evidence`);
    return res.data;
  },

  async getEvidenceById(caseId: number | string, evidenceId: number | string): Promise<CiscoEvidence> {
    const res = await client.get<CiscoEvidence>(`/cases/${caseId}/evidence/${evidenceId}`);
    return res.data;
  },

  async createEvidence(caseId: number | string, data: CiscoEvidenceCreateInput): Promise<CiscoEvidence> {
    const res = await client.post<CiscoEvidence>(`/cases/${caseId}/evidence`, data);
    return res.data;
  },

  async deleteEvidence(caseId: number | string, evidenceId: number | string): Promise<void> {
    await client.delete(`/cases/${caseId}/evidence/${evidenceId}`);
  },

  async parseEvidence(caseId: number | string, evidenceId: number | string): Promise<any> {
    const res = await client.post(`/cases/${caseId}/evidence/${evidenceId}/parse`);
    return res.data;
  },

  // Python Rule-Based Fault Detection API
  async diagnoseWithRules(caseId: number | string): Promise<RuleEngineResult> {
    const res = await client.post<RuleEngineResult>(`/cases/${caseId}/diagnose/rules`);
    return res.data;
  },

  // AI-Assisted Network Diagnosis API
  async diagnoseWithAi(caseId: number | string): Promise<AiDiagnosisResult> {
    const res = await client.post<AiDiagnosisResult>(`/cases/${caseId}/diagnose/ai`);
    return res.data;
  },

  // AI vs Python Diagnosis Comparison API
  async compareDiagnosis(caseId: number | string): Promise<DiagnosisComparisonResult> {
    const res = await client.post<DiagnosisComparisonResult>(`/cases/${caseId}/diagnose/compare`);
    return res.data;
  },

  // Human-in-the-Loop Review & Remediation Verification API
  async getCaseReviews(caseId: number | string): Promise<HumanReviewRecord[]> {
    const res = await client.get<HumanReviewRecord[]>(`/cases/${caseId}/reviews`);
    return res.data;
  },

  async submitHumanReview(caseId: number | string, data: HumanReviewCreateInput): Promise<HumanReviewRecord> {
    const res = await client.post<HumanReviewRecord>(`/cases/${caseId}/reviews`, data);
    return res.data;
  },

  async confirmRemediation(caseId: number | string, reviewId: number | string, remediationNotes?: string): Promise<HumanReviewRecord> {
    const res = await client.post<HumanReviewRecord>(`/cases/${caseId}/reviews/${reviewId}/confirm-remediation`, {
      remediation_notes: remediationNotes,
    });
    return res.data;
  },

  async verifyRemediation(caseId: number | string, reviewId: number | string): Promise<VerificationResponse> {
    const res = await client.post<VerificationResponse>(`/cases/${caseId}/reviews/${reviewId}/verify`);
    return res.data;
  },
};
