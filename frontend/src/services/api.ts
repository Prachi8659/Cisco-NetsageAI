import axios from 'axios';
import type { Case, CaseCreateInput, PktFile, PktAnalysisResult } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
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
};
