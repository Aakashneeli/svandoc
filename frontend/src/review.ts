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

export type PrimitiveValue = string | number | boolean | null;

export type EditableField = {
  path: string;
  value: PrimitiveValue;
};

export type ExtractionPatchResponse = {
  document_id: string;
  correction_count: number;
  corrected_by: string;
  corrected_at: string;
  structured_payload: Record<string, unknown>;
  confidence_map: Record<string, unknown>;
  review_required: boolean;
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

export async function patchDocumentExtraction(
  apiBaseUrl: string,
  documentId: string,
  corrections: Array<{ field_path: string; new_value: unknown }>,
): Promise<ExtractionPatchResponse> {
  const response = await fetch(`${apiBaseUrl}/api/documents/${documentId}/extraction`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ corrections }),
  });
  const payload = (await response.json()) as EnvelopeResponse<ExtractionPatchResponse>;
  if (!response.ok || !payload.data) {
    throw new Error(payload.error?.message ?? "Unable to save correction.");
  }
  return payload.data;
}

function isPrimitiveValue(value: unknown): value is PrimitiveValue {
  return (
    value === null
    || typeof value === "string"
    || typeof value === "number"
    || typeof value === "boolean"
  );
}

function flattenObjectFields(value: unknown, path: string, output: EditableField[]): void {
  if (isPrimitiveValue(value)) {
    output.push({ path, value });
    return;
  }

  if (Array.isArray(value)) {
    value.forEach((item, index) => {
      const nextPath = path ? `${path}.${index}` : String(index);
      flattenObjectFields(item, nextPath, output);
    });
    return;
  }

  if (value && typeof value === "object") {
    const obj = value as Record<string, unknown>;
    Object.entries(obj).forEach(([key, nested]) => {
      const nextPath = path ? `${path}.${key}` : key;
      flattenObjectFields(nested, nextPath, output);
    });
  }
}

export function flattenEditableFields(payload: Record<string, unknown>): EditableField[] {
  const output: EditableField[] = [];
  flattenObjectFields(payload, "", output);
  return output.filter((item) => item.path.length > 0);
}

export function confidenceForPath(
  confidenceMap: Record<string, unknown> | null | undefined,
  path: string,
): number | null {
  if (!confidenceMap || typeof confidenceMap !== "object") {
    return null;
  }
  const fields = (confidenceMap as { fields?: unknown }).fields;
  if (!fields || typeof fields !== "object") {
    return null;
  }
  const value = (fields as Record<string, unknown>)[path];
  if (typeof value !== "number") {
    return null;
  }
  return value;
}
