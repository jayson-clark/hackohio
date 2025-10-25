import axios from 'axios';
import { GraphData, ProcessingStatus, GraphAnalytics } from '@/types';

const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const apiService = {
  /**
   * Upload PDFs and start processing
   */
  async uploadPDFs(
    files: File[],
    projectName?: string,
    enableLLM = false
  ): Promise<ProcessingStatus> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    const params = new URLSearchParams();
    if (projectName) params.append('project_name', projectName);
    params.append('enable_llm', String(enableLLM));

    const response = await api.post<ProcessingStatus>(
      `/api/process?${params.toString()}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  },

  /**
   * Check processing status
   */
  async getStatus(jobId: string): Promise<ProcessingStatus> {
    const response = await api.get<ProcessingStatus>(`/api/status/${jobId}`);
    return response.data;
  },

  /**
   * Filter graph data
   */
  async filterGraph(
    graphData: GraphData,
    minDegree = 1,
    entityTypes?: string[],
    topN?: number
  ): Promise<GraphData> {
    const response = await api.post<GraphData>('/api/graph/filter', graphData, {
      params: {
        min_degree: minDegree,
        entity_types: entityTypes?.join(','),
        top_n: topN,
      },
    });

    return response.data;
  },

  /**
   * Compute analytics for a graph
   */
  async computeAnalytics(graphData: GraphData): Promise<GraphAnalytics> {
    const response = await api.post<GraphAnalytics>('/api/analytics', graphData);
    return response.data;
  },

  /**
   * Health check
   */
  async healthCheck(): Promise<{ status: string; version: string }> {
    const response = await api.get('/');
    return response.data;
  },
};

