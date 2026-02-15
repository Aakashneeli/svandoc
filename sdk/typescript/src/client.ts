export type UploadResponse = {
  document_ids: string[];
  job_ids: string[];
};

export type ExportResponse = {
  artifact_id: string;
  document_id: string;
  format: string;
  storage_uri: string;
};

type Envelope<T> = {
  status: "success" | "error";
  data: T;
};

export class SvanDocClient {
  private readonly apiBaseUrl: string;
  private readonly apiKey: string;

  constructor(args: { apiBaseUrl: string; apiKey: string }) {
    this.apiBaseUrl = args.apiBaseUrl.replace(/\/+$/, "");
    this.apiKey = args.apiKey;
  }

  private async request<T>(path: string, init: RequestInit): Promise<T> {
    const response = await fetch(`${this.apiBaseUrl}${path}`, {
      ...init,
      headers: {
        "x-api-key": this.apiKey,
        ...(init.headers ?? {}),
      },
    });
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }
    const payload = (await response.json()) as Envelope<T>;
    return payload.data;
  }

  async uploadDocument(file: Blob, filename = "document.pdf"): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("files", file, filename);
    return this.request<UploadResponse>("/api/public/documents/upload", {
      method: "POST",
      body: formData,
    });
  }

  async getJob(jobId: string): Promise<Record<string, unknown>> {
    return this.request<Record<string, unknown>>(`/api/public/jobs/${jobId}`, {
      method: "GET",
    });
  }

  async getExtraction(documentId: string): Promise<Record<string, unknown>> {
    return this.request<Record<string, unknown>>(`/api/public/documents/${documentId}/extraction`, {
      method: "GET",
    });
  }

  async exportDocument(documentId: string, format: string): Promise<ExportResponse> {
    return this.request<ExportResponse>(`/api/public/documents/${documentId}/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ format }),
    });
  }
}
