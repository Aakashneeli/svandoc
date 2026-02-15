export type UploadStatus = "queued" | "uploading" | "completed" | "failed";

export type UploadQueueItem = {
  id: string;
  file: File;
  status: UploadStatus;
  message: string;
};

type UploadApiError = {
  code?: string;
  message?: string;
  details?: {
    files?: Array<{
      filename?: string;
      issues?: string[];
      reason?: string;
      document_id?: string;
    }>;
    duplicates?: Array<{
      filename?: string;
      reason?: string;
      document_id?: string;
    }>;
  };
};

export type UploadApiResponse = {
  error?: UploadApiError;
};

export function createUploadQueue(files: FileList | File[]): UploadQueueItem[] {
  const selected = Array.from(files);
  return selected.map((file, index) => ({
    id: `${Date.now()}-${index}-${file.name}`,
    file,
    status: "queued",
    message: "Ready to upload",
  }));
}

export function updateUploadItem(
  items: UploadQueueItem[],
  id: string,
  status: UploadStatus,
  message: string,
): UploadQueueItem[] {
  return items.map((item) => (item.id === id ? { ...item, status, message } : item));
}

export function getUploadFailureMessage(payload: UploadApiResponse, filename: string): string {
  const error = payload.error;
  if (!error) {
    return "Upload failed";
  }

  if (error.code === "VALIDATION_ERROR") {
    const matching = error.details?.files?.find((file) => file.filename === filename);
    if (matching?.issues && matching.issues.length > 0) {
      return matching.issues.join(" ");
    }
  }

  if (error.code === "DUPLICATE_DOCUMENT") {
    const matching = error.details?.duplicates?.find((item) => item.filename === filename);
    if (matching?.reason === "already_exists" && matching.document_id) {
      return `Duplicate upload. Existing document id: ${matching.document_id}`;
    }
    if (matching?.reason === "duplicate_in_request") {
      return "Duplicate file detected in this upload batch.";
    }
  }

  return error.message ?? "Upload failed";
}
