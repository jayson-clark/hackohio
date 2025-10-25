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
   * Chat with the graph
   */
  async chat(message: string, graph: GraphData, conversationHistory: Array<{ role: string; content: string }> = []) {
    const response = await api.post('/api/chat', {
      message,
      graph,
      conversation_history: conversationHistory,
    });
    return response.data as {
      answer: string;
      citations: string[];
      relevant_nodes: string[];
      relevant_edges: [string, string][];
      tool_calls: string[];
    };
  },

  /**
   * Generate hypotheses
   */
  async generateHypotheses(graph: GraphData, focusEntity?: string, maxResults = 10) {
    const response = await api.post('/api/hypotheses', {
      graph,
      focus_entity: focusEntity,
      max_results: maxResults,
    });
    return response.data as {
      hypotheses: Array<{
        title: string;
        explanation: string;
        entities: string[];
        evidence_sentences: string[];
        edge_pairs: [string, string][];
        confidence: number;
      }>;
    };
  },

  /**
   * NER preview for raw text
   */
  async nerPreview(text: string, minOccurrences = 2, returnRaw = false) {
    const response = await api.post('/api/ner/preview', {
      text,
      min_occurrences: minOccurrences,
      return_raw: returnRaw,
    });
    return response.data as {
      sentences: Array<{ sentence_id: number; sentence: string; entities: any[] }>;
      unique_entities: Record<string, { original_name: string; type: string; count: number }>;
      raw_sentences?: Array<{ sentence_id: number; sentence: string; entities: any[] }>;
    };
  },

  /**
   * Export current graph as project
   */
  async exportProject(graph: GraphData, projectName: string) {
    return {
      project_name: projectName,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      graph,
      sources: [],
      settings: {},
    };
  },

  /**
   * Import project
   */
  async importProject(projectData: any) {
    const response = await api.post('/api/projects/import', {
      project_data: projectData,
      merge_with_existing: false,
    });
    return response.data;
  },

  /**
   * Discover papers from PubMed
   */
  async discoverPapers(query: string, maxResults = 10) {
    const response = await api.post('/api/discover/papers', {
      query,
      max_results: maxResults,
      auto_merge: false,
      source: 'pubmed',
    });
    return response.data as {
      papers: Array<{
        id: string;
        title: string;
        abstract: string;
        authors: string[];
        journal: string;
        year?: number;
        url: string;
      }>;
      status: string;
    };
  },

  /**
   * Process discovered papers
   */
  async processDiscoveredPapers(papers: any[]) {
    const response = await api.post('/api/discover/papers/process', papers);
    return response.data;
  },

  /**
   * Discover clinical trials
   */
  async discoverTrials(condition: string, maxResults = 20) {
    const response = await api.post('/api/discover/trials', {
      condition,
      max_results: maxResults,
    });
    return response.data as {
      trials: Array<{
        nct_id: string;
        title: string;
        condition: string;
        interventions: string[];
        phase: string;
        status: string;
        sponsor: string;
        brief_summary: string;
        url: string;
      }>;
      graph?: GraphData;
    };
  },

  /**
   * Health check
   */
  async healthCheck(): Promise<{ status: string; version: string }> {
    const response = await api.get('/');
    return response.data;
  },
};

