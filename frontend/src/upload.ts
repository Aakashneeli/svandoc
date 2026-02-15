export type UploadStatus = "queued" | "uploading" | "completed" | "failed";

export type UploadQueueItem = {
  id: string;
  file: File;
  status: UploadStatus;
  message: string;
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
