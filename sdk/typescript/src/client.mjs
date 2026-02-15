export class SvanDocClient {
  constructor({ apiBaseUrl, apiKey }) {
    this.apiBaseUrl = (apiBaseUrl || "").replace(/\/+$/, "");
    this.apiKey = apiKey;
  }

  async request(path, init) {
    const response = await fetch(`${this.apiBaseUrl}${path}`, {
      ...init,
      headers: {
        "x-api-key": this.apiKey,
        ...(init?.headers || {}),
      },
    });
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }
    const payload = await response.json();
    return payload.data;
  }

  async uploadDocument(file, filename = "document.pdf") {
    const formData = new FormData();
    formData.append("files", file, filename);
    return this.request("/api/public/documents/upload", {
      method: "POST",
      body: formData,
    });
  }

  async getJob(jobId) {
    return this.request(`/api/public/jobs/${jobId}`, { method: "GET" });
  }

  async getExtraction(documentId) {
    return this.request(`/api/public/documents/${documentId}/extraction`, { method: "GET" });
  }

  async exportDocument(documentId, format) {
    return this.request(`/api/public/documents/${documentId}/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ format }),
    });
  }
}
