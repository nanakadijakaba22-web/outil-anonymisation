/**
 * API Client for Annoy Backend
 * Type-safe client for all backend endpoints
 */

const API_URL = `${process.env.NEXT_PUBLIC_API_URL || ""}${process.env.URL_STR || "/api/v1"}`;

// Types
export interface Dataset {
  id: string;
  filename: string;
  file_size: number;
  row_count: number;
  column_count: number;
  upload_date: string;
  is_anonymized: boolean;
  risk_score: number | null;
  is_loi25_compliant: boolean;
  columns?: ColumnInfo[];
}

export interface ColumnInfo {
  name: string;
  position: number;
  data_type: string;
  sensitivity_type: string | null;
  category: string | null;
  confidence: number | null;
  null_count: number;
  unique_count: number;
  sample_values: any[] | null;
}

export interface DatasetPreview {
  dataset_id: string;
  columns: string[];
  sample_rows: Record<string, any>[];
  total_rows: number;
}

export interface ColumnClassification {
  column_name: string;
  sensitivity_type:
  | "direct_identifier"
  | "quasi_identifier"
  | "sensitive"
  | "non_sensitive";
  category:
  | "Personnel"
  | "Origine ethnique ou raciale"
  | "Santé"
  | "Financier"
  | "BIOMETRIQUE"
  | "GENETIQUE"
  | "VIE SEXUELLE"
  | "ORIENTATION SEXUELLE"
  | "RELIGION"
  | "PHILOSOPHIE"
  | "POLITIQUE"
  | "ETHNIQUE"
  | "RACIALE"
  | "ASSURANCE"
  | "Autre";
  confidence: number;
  justification: string;
  risk_score?: number; // Optionnel - Risque de ré-identification (0-100)
  suggested_config?: AnonymizationConfig;
}

export interface DetectionReport {
  dataset_id: string;
  columns: Record<string, ColumnClassification>;
  overall_risk_score: number;
  summary: {
    direct_identifier: number;
    quasi_identifier: number;
    sensitive: number;
    non_sensitive: number;
  };
}

export interface ColumnSensitivityUpdate {
  sensitivity_type:
  | "direct_identifier"
  | "quasi_identifier"
  | "sensitive"
  | "non_sensitive";
  category?:
  | "Personnel"
  | "Origine ethnique ou raciale"
  | "Santé"
  | "Financier"
  | "BIOMETRIQUE"
  | "GENETIQUE"
  | "VIE SEXUELLE"
  | "ORIENTATION SEXUELLE"
  | "RELIGION"
  | "PHILOSOPHIE"
  | "POLITIQUE"
  | "ETHNIQUE"
  | "RACIALE"
  | "ASSURANCE"
  | "Autre";
  justification?: string;
}

export interface BulkSensitivityUpdate {
  updates: Record<string, ColumnSensitivityUpdate>;
}

export interface AnonymizationConfig {
  column_name: string;
  technique:
  | "masking"
  | "generalization"
  | "suppression"
  | "differential_privacy";
  params: Record<string, any>;
}

export interface TransformationDetail {
  column_name: string;
  technique: string;
  params: Record<string, any>;
  values_affected: number;
  sample_transformations: Array<{
    original: string;
    anonymized: string;
  }> | null;
}

export interface AnonymizationResponse {
  job_id: string;
  anonymized_dataset_id: string;
  transformations: TransformationDetail[];
  processing_time_seconds: number;
  status: "pending" | "processing" | "completed" | "failed";
}

export interface RiskScore {
  score: number;
  level: "faible" | "moyen" | "élevé";
  justification: string;
  affected_columns: string[];
}

export interface RiskAssessment {
  dataset_id: string;
  assessed_at: string;
  individualization: RiskScore;
  correlation: RiskScore;
  inference: RiskScore;
  overall_score: number;
  overall_level: "faible" | "moyen" | "élevé";
  is_loi25_compliant: boolean;
  recommendations: string[];
  details: any | null;
}

// API Client Class
class AnnoyAPIClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_URL) {
    this.baseUrl = baseUrl;
  }

  // Helper method for handling responses
  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const text = await response.text();
        if (text) {
          const error = JSON.parse(text);
          if (error.detail) {
            // FastAPI sometimes returns detail as an array of validation errors or an object
            if (typeof error.detail === 'string') {
              errorMessage = error.detail;
            } else if (typeof error.detail === 'object') {
              errorMessage = error.detail.message || JSON.stringify(error.detail);
            }
          }
        }
      } catch (e) {
        // Ignorer l'erreur de parsing et garder le message par défaut
        console.error("Erreur de parsing dans handleResponse:", e);
      }
      throw new Error(errorMessage);
    }
    return response.json();
  }

  // Datasets endpoints
  async uploadDataset(file: File): Promise<Dataset> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${this.baseUrl}/datasets/upload`, {
      method: "POST",
      body: formData,
    });

    return this.handleResponse<Dataset>(response);
  }

  async getDataset(datasetId: string): Promise<Dataset> {
    const response = await fetch(`${this.baseUrl}/datasets/${datasetId}`);
    return this.handleResponse<Dataset>(response);
  }

  async getDatasetPreview(
    datasetId: string,
    nRows: number = 10,
    options?: { signal?: AbortSignal },
  ): Promise<DatasetPreview> {
    const response = await fetch(
      `${this.baseUrl}/datasets/${datasetId}/preview?n_rows=${nRows}`,
      options,
    );
    return this.handleResponse<DatasetPreview>(response);
  }

  async deleteDataset(datasetId: string): Promise<void> {
    await fetch(`${this.baseUrl}/datasets/${datasetId}`, {
      method: "DELETE",
    });
  }

  // Detection endpoint
  async detectSensitiveData(datasetId: string): Promise<DetectionReport> {
    const response = await fetch(
      `${this.baseUrl}/datasets/${datasetId}/detect`,
      {
        method: "POST",
      },
    );
    console.log("Response from detect endpoint:", response);
    return this.handleResponse<DetectionReport>(response);
  }

  // Column sensitivity update endpoints
  async updateColumnSensitivity(
    datasetId: string,
    columnName: string,
    update: ColumnSensitivityUpdate,
  ): Promise<ColumnInfo> {
    const response = await fetch(
      `${this.baseUrl}/datasets/${datasetId}/columns/${encodeURIComponent(columnName)}/sensitivity`,
      {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(update),
      },
    );
    return this.handleResponse<ColumnInfo>(response);
  }

  async updateColumnsSensitivityBulk(
    datasetId: string,
    bulkUpdate: BulkSensitivityUpdate,
  ): Promise<ColumnInfo[]> {
    const response = await fetch(
      `${this.baseUrl}/datasets/${datasetId}/columns/sensitivity/bulk`,
      {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(bulkUpdate),
      },
    );
    return this.handleResponse<ColumnInfo[]>(response);
  }

  // Anonymization endpoints
  async anonymizeDataset(
    datasetId: string,
    config: AnonymizationConfig[],
  ): Promise<AnonymizationResponse> {
    const response = await fetch(
      `${this.baseUrl}/datasets/${datasetId}/anonymize`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(config),
      },
    );
    return this.handleResponse<AnonymizationResponse>(response);
  }

  /**
   * Lance l'anonymisation automatique complète selon la Loi 25
   * Applique automatiquement les techniques optimales pour chaque type de données
   */
  async autoAnonymizeDataset(datasetId: string): Promise<AnonymizationResponse> {
    const response = await fetch(
      `${this.baseUrl}/datasets/${datasetId}/auto-anonymize`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      },
    );
    return this.handleResponse<AnonymizationResponse>(response);
  }

  getDownloadUrl(datasetId: string): string {
    return `${this.baseUrl}/datasets/${datasetId}/download`;
  }

  async downloadDataset(datasetId: string): Promise<Blob> {
    const response = await fetch(this.getDownloadUrl(datasetId));
    if (!response.ok) {
      throw new Error(`Failed to download: ${response.statusText}`);
    }
    return response.blob();
  }

  // Risk assessment endpoint
  async assessRisk(datasetId: string): Promise<RiskAssessment> {
    const response = await fetch(
      `${this.baseUrl}/datasets/${datasetId}/risk-assessment`,
    );
    return this.handleResponse<RiskAssessment>(response);
  }

  // Generate and download PDF compliance report
  async downloadComplianceReport(datasetId: string): Promise<Blob> {
    const response = await fetch(
      `${this.baseUrl}/datasets/${datasetId}/report`,
    );
    if (!response.ok) {
      throw new Error(`Failed to generate report: ${response.statusText}`);
    }
    return response.blob();
  }
}

// Export singleton instance
export const api = new AnnoyAPIClient();

// Export the class for testing/custom instances
export default AnnoyAPIClient;
