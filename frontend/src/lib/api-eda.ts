/**
 * EDA-specific API client
 * Handles datasheet analysis, job processing, and design workflows
 */

import { apiClient } from './api-client';

// ============================================================================
// Types
// ============================================================================

export interface AnalyzeRequest {
  user_constraints?: Record<string, number>;
}

export interface AnalyzeResponse {
  job_id: string;
  status: string;
  created_at: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: string;
  created_at: string;
  updated_at: string;
  design?: FinalDesignResponse;
}

export interface FinalDesignResponse {
  job_id: string;
  status: string;
  metadata: {
    device_name?: string;
    datasheet_title?: string;
  };
  design_parameters: {
    V_in?: number;
    V_out?: number;
    I_out_max?: number;
  };
  circuit_design: {
    schematic_nodes: Array<{
      ref: string;
      lib: string;
      value: string;
      pos?: [number, number];
    }>;
    nets: Array<{
      name: string;
      connections: string[];
    }>;
  };
  bom: Array<{
    reference: string;
    part_number?: string;
    manufacturer?: string;
    description?: string;
    value?: string;
    quantity: number;
    package?: string;
  }>;
  download_links: {
    kicad_sch: string;
  };
}

export interface ResumeRequest {
  missing_variables: Record<string, number>;
}

export interface ResumeResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface StreamEvent {
  event: string;
  data: {
    node?: string;
    status?: string;
    message?: string;
    error?: string;
  };
}

// ============================================================================
// EDA API Client
// ============================================================================

/**
 * Upload and analyze a datasheet
 */
export async function analyzeDatasheet(
  file: File,
  userConstraints: Record<string, number> = {}
): Promise<AnalyzeResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('user_constraints', JSON.stringify(userConstraints));

  // Use fetch directly for FormData (api-client uses JSON)
  const response = await fetch('/api/analyze', {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || 'Failed to analyze datasheet');
  }

  return response.json();
}

/**
 * Get job status
 */
export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  return apiClient.get<JobStatusResponse>(`/jobs/${jobId}`);
}

/**
 * Stream real-time job status updates via Server-Sent Events
 * Perfect for human-in-the-loop workflows
 */
export function streamJobStatus(
  jobId: string,
  onEvent: (event: StreamEvent) => void
): EventSource {
  const eventSource = new EventSource(`/api/jobs/${jobId}/stream`);

  eventSource.addEventListener('agent_update', (e) => {
    try {
      const data = JSON.parse(e.data);
      onEvent({ event: 'agent_update', data });
    } catch (error) {
      console.error('Failed to parse SSE event:', error);
    }
  });

  eventSource.addEventListener('error', (e) => {
    try {
      const data = JSON.parse((e as MessageEvent).data);
      onEvent({ event: 'error', data });
    } catch (error) {
      console.error('Failed to parse SSE error:', error);
    }
  });

  eventSource.onerror = () => {
    eventSource.close();
  };

  return eventSource;
}

/**
 * Resume a job with missing variables
 * Human-in-the-loop: user provides missing design parameters
 */
export async function resumeJob(
  jobId: string,
  missingVariables: Record<string, number>
): Promise<ResumeResponse> {
  return apiClient.post<ResumeResponse>(`/jobs/${jobId}/resume`, {
    missing_variables: missingVariables,
  });
}

/**
 * Download schematic file
 */
export function downloadSchematic(jobId: string): void {
  window.open(`/api/jobs/${jobId}/artifacts/schematic.kicad_sch`, '_blank');
}

/**
 * Download BOM (Bill of Materials)
 */
export function downloadBOM(jobId: string): void {
  window.open(`/api/jobs/${jobId}/artifacts/bom.csv`, '_blank');
}
