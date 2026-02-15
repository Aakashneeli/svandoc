"use client";

import { useMemo, useState } from "react";
import {
  createUploadQueue,
  getUploadFailureMessage,
  type UploadApiResponse,
  type UploadQueueItem,
  updateUploadItem,
} from "../../src/upload";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function UploadPage() {
  const [queue, setQueue] = useState<UploadQueueItem[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [errorBanner, setErrorBanner] = useState("");

  const queuedCount = useMemo(
    () => queue.filter((item) => item.status === "queued" || item.status === "failed").length,
    [queue],
  );

  function appendFiles(files: FileList | null) {
    if (!files || files.length === 0) {
      return;
    }
    setQueue((current) => [...current, ...createUploadQueue(files)]);
  }

  async function uploadSingle(item: UploadQueueItem) {
    setQueue((current) => updateUploadItem(current, item.id, "uploading", "Uploading..."));
    const form = new FormData();
    form.append("files", item.file);
    form.append("doc_type_hint", "invoice");

    try {
      const response = await fetch(`${API_BASE_URL}/api/documents/upload`, {
        method: "POST",
        body: form,
      });
      const payload = (await response.json()) as UploadApiResponse;
      if (!response.ok) {
        const message = getUploadFailureMessage(payload, item.file.name);
        setQueue((current) => updateUploadItem(current, item.id, "failed", message));
        setErrorBanner(`Upload error for ${item.file.name}: ${message}`);
        return;
      }
      setQueue((current) => updateUploadItem(current, item.id, "completed", "Uploaded"));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Network error";
      setQueue((current) => updateUploadItem(current, item.id, "failed", message));
      setErrorBanner(`Upload error for ${item.file.name}: ${message}`);
    }
  }

  async function uploadAll() {
    if (isUploading || queuedCount === 0) {
      return;
    }
    setErrorBanner("");
    setIsUploading(true);
    const snapshot = [...queue];
    for (const item of snapshot) {
      if (item.status === "completed") {
        continue;
      }
      // Sequential upload keeps per-file status updates stable and easier to inspect.
      await uploadSingle(item);
    }
    setIsUploading(false);
  }

  return (
    <section className="page">
      <div className="hero">
        <h1>Upload</h1>
        <p>Select one file or a batch. Each file tracks its own status through the upload flow.</p>
        <ul className="hint-list">
          <li>Accepted file types: PDF, PNG, JPG/JPEG, TIFF, HEIC.</li>
          <li>Validation checks file type, size, and page count before processing.</li>
          <li>Correct invalid files and retry failed rows directly from this page.</li>
        </ul>
        <div className="upload-actions">
          <label className="button-like">
            Add Single File
            <input
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif,.heic"
              onChange={(event) => appendFiles(event.target.files)}
              hidden
            />
          </label>
          <label className="button-like">
            Add Batch
            <input
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif,.heic"
              multiple
              onChange={(event) => appendFiles(event.target.files)}
              hidden
            />
          </label>
          <button type="button" className="button-like button-accent" onClick={uploadAll} disabled={isUploading || queuedCount === 0}>
            {isUploading ? "Uploading..." : `Upload ${queuedCount} File${queuedCount === 1 ? "" : "s"}`}
          </button>
        </div>
        {errorBanner ? <p className="alert-banner alert-error">{errorBanner}</p> : null}
      </div>

      <div className="panel">
        <h2>Per-file status</h2>
        {queue.length === 0 ? (
          <p className="empty-note">No files selected yet.</p>
        ) : (
          <ul className="upload-list">
            {queue.map((item) => (
              <li key={item.id} className="upload-row">
                <div>
                  <div className="upload-file">{item.file.name}</div>
                  <div className="upload-meta">
                    {(item.file.size / 1024).toFixed(1)} KB
                    {" | "}
                    {item.file.type || "unknown type"}
                  </div>
                </div>
                <div className="status-badge" data-status={item.status}>
                  {item.status}
                </div>
                <div className="upload-message">{item.message}</div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
