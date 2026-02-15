export type ExtractionData = {
  document_id: string;
  schema_version: string;
  doc_type: string;
  review_required: boolean;
  raw_ocr_text: string;
  structured_payload: Record<string, unknown>;
  confidence_map: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
};

type EnvelopeError = {
  message?: string;
};

type EnvelopeResponse<TData> = {
  data?: TData;
  error?: EnvelopeError;
};

export async function fetchDocumentExtraction(
  apiBaseUrl: string,
  documentId: string,
): Promise<ExtractionData> {
  const response = await fetch(`${apiBaseUrl}/api/documents/${documentId}/extraction`, {
    method: "GET",
  });
  const payload = (await response.json()) as EnvelopeResponse<ExtractionData>;
  if (!response.ok || !payload.data) {
    throw new Error(payload.error?.message ?? "Unable to load extraction.");
  }
  return payload.data;
}

