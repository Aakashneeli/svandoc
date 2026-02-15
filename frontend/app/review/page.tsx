"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  confidenceForPath,
  fetchDocumentExtraction,
  flattenEditableFields,
  patchDocumentExtraction,
  requestDocumentExport,
  type ExtractionData,
  type ExportArtifactData,
  type ExportFormat,
  type PrimitiveValue,
} from "../../src/review";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function ReviewPage() {
  const searchParams = useSearchParams();
  const [documentIdInput, setDocumentIdInput] = useState(searchParams.get("documentId") ?? "");
  const [documentUrlInput, setDocumentUrlInput] = useState(searchParams.get("documentUrl") ?? "");
  const [activeDocumentId, setActiveDocumentId] = useState(searchParams.get("documentId") ?? "");
  const [activeDocumentUrl, setActiveDocumentUrl] = useState(searchParams.get("documentUrl") ?? "");
  const [extraction, setExtraction] = useState<ExtractionData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [draftPayload, setDraftPayload] = useState<Record<string, unknown>>({});
  const [saveStateByPath, setSaveStateByPath] = useState<Record<string, "idle" | "saving">>({});
  const [saveMessageByPath, setSaveMessageByPath] = useState<Record<string, string>>({});
  const [lowConfidenceThreshold, setLowConfidenceThreshold] = useState(0.8);
  const [showLowConfidenceOnly, setShowLowConfidenceOnly] = useState(false);
  const [exportStateByFormat, setExportStateByFormat] = useState<Record<ExportFormat, "idle" | "running">>({
    json: "idle",
    csv: "idle",
    xlsx: "idle",
  });
  const [exportMessageByFormat, setExportMessageByFormat] = useState<Record<ExportFormat, string>>({
    json: "",
    csv: "",
    xlsx: "",
  });
  const [artifactsByFormat, setArtifactsByFormat] = useState<Partial<Record<ExportFormat, ExportArtifactData>>>({});

  useEffect(() => {
    const initialDocumentId = searchParams.get("documentId");
    const initialDocumentUrl = searchParams.get("documentUrl");
    if (!initialDocumentId) {
      return;
    }

    let cancelled = false;
    setIsLoading(true);
    setErrorMessage("");
    setActiveDocumentId(initialDocumentId);
    setActiveDocumentUrl(initialDocumentUrl ?? "");
    fetchDocumentExtraction(API_BASE_URL, initialDocumentId)
      .then((result) => {
        if (!cancelled) {
          setExtraction(result);
          setDraftPayload(result.structured_payload);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setExtraction(null);
          setDraftPayload({});
          setErrorMessage(error instanceof Error ? error.message : "Unable to load extraction.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [searchParams]);

  async function handleLoadReview() {
    const documentId = documentIdInput.trim();
    if (!documentId) {
      setErrorMessage("Enter a document ID to load review data.");
      return;
    }

    setIsLoading(true);
    setErrorMessage("");
    setActiveDocumentId(documentId);
    setActiveDocumentUrl(documentUrlInput.trim());
    try {
      const result = await fetchDocumentExtraction(API_BASE_URL, documentId);
      setExtraction(result);
      setDraftPayload(result.structured_payload);
    } catch (error) {
      setExtraction(null);
      setDraftPayload({});
      setErrorMessage(error instanceof Error ? error.message : "Unable to load extraction.");
    } finally {
      setIsLoading(false);
    }
  }

  const editableFields = flattenEditableFields(draftPayload).filter((field) => {
    if (!showLowConfidenceOnly) {
      return true;
    }
    const score = confidenceForPath(extraction?.confidence_map, field.path);
    return score !== null && score < lowConfidenceThreshold;
  });

  const lowConfidenceCount = flattenEditableFields(draftPayload).filter((field) => {
    const score = confidenceForPath(extraction?.confidence_map, field.path);
    return score !== null && score < lowConfidenceThreshold;
  }).length;

  function parseFieldInput(rawValue: string, currentValue: PrimitiveValue): PrimitiveValue {
    if (currentValue === null) {
      if (rawValue.trim().toLowerCase() === "null" || rawValue.trim() === "") {
        return null;
      }
      return rawValue;
    }
    if (typeof currentValue === "number") {
      const numeric = Number(rawValue);
      return Number.isFinite(numeric) ? numeric : currentValue;
    }
    if (typeof currentValue === "boolean") {
      return rawValue.trim().toLowerCase() === "true";
    }
    return rawValue;
  }

  function setFieldValue(path: string, value: PrimitiveValue) {
    setDraftPayload((current) => {
      const clone = structuredClone(current) as Record<string, unknown>;
      const tokens = path.split(".");
      let pointer: unknown = clone;
      for (let index = 0; index < tokens.length; index += 1) {
        const token = tokens[index];
        const isLast = index === tokens.length - 1;
        const tokenIndex = Number.parseInt(token, 10);
        const isArrayIndex = Number.isInteger(tokenIndex) && token === String(tokenIndex);

        if (isArrayIndex) {
          if (!Array.isArray(pointer) || tokenIndex < 0 || tokenIndex >= pointer.length) {
            return current;
          }
          if (isLast) {
            pointer[tokenIndex] = value;
            return clone;
          }
          pointer = pointer[tokenIndex];
          continue;
        }

        if (!pointer || typeof pointer !== "object") {
          return current;
        }
        const record = pointer as Record<string, unknown>;
        if (!(token in record)) {
          return current;
        }
        if (isLast) {
          record[token] = value;
          return clone;
        }
        pointer = record[token];
      }
      return current;
    });
  }

  function getFieldValue(path: string): { found: boolean; value: PrimitiveValue } {
    let pointer: unknown = draftPayload;
    for (const token of path.split(".")) {
      const tokenIndex = Number.parseInt(token, 10);
      const isArrayIndex = Number.isInteger(tokenIndex) && token === String(tokenIndex);
      if (isArrayIndex) {
        if (!Array.isArray(pointer) || tokenIndex < 0 || tokenIndex >= pointer.length) {
          return { found: false, value: null };
        }
        pointer = pointer[tokenIndex];
        continue;
      }
      if (!pointer || typeof pointer !== "object" || !(token in (pointer as Record<string, unknown>))) {
        return { found: false, value: null };
      }
      pointer = (pointer as Record<string, unknown>)[token];
    }

    if (
      pointer === null
      || typeof pointer === "string"
      || typeof pointer === "number"
      || typeof pointer === "boolean"
    ) {
      return { found: true, value: pointer };
    }
    return { found: false, value: null };
  }

  async function saveField(path: string) {
    if (!activeDocumentId || !extraction) {
      return;
    }
    const nextFieldValue = getFieldValue(path);
    if (!nextFieldValue.found) {
      return;
    }
    setSaveStateByPath((current) => ({ ...current, [path]: "saving" }));
    setSaveMessageByPath((current) => ({ ...current, [path]: "" }));
    try {
      const result = await patchDocumentExtraction(API_BASE_URL, activeDocumentId, [{ field_path: path, new_value: nextFieldValue.value }]);
      const nextExtraction: ExtractionData = {
        ...extraction,
        structured_payload: result.structured_payload,
        confidence_map: result.confidence_map,
        review_required: result.review_required,
        updated_at: result.corrected_at,
      };
      setExtraction(nextExtraction);
      setDraftPayload(result.structured_payload);
      setSaveMessageByPath((current) => ({ ...current, [path]: "Saved" }));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to save field.";
      setSaveMessageByPath((current) => ({ ...current, [path]: message }));
    } finally {
      setSaveStateByPath((current) => ({ ...current, [path]: "idle" }));
    }
  }

  function isDownloadableUrl(storageUri: string): boolean {
    const normalized = storageUri.toLowerCase();
    return normalized.startsWith("http://") || normalized.startsWith("https://") || normalized.startsWith("/");
  }

  async function runExport(format: ExportFormat) {
    if (!activeDocumentId) {
      setErrorMessage("Load a document before exporting.");
      return;
    }

    setExportStateByFormat((current) => ({ ...current, [format]: "running" }));
    setExportMessageByFormat((current) => ({ ...current, [format]: "" }));
    try {
      const artifact = await requestDocumentExport(API_BASE_URL, activeDocumentId, format);
      setArtifactsByFormat((current) => ({ ...current, [format]: artifact }));
      setExportMessageByFormat((current) => ({
        ...current,
        [format]: isDownloadableUrl(artifact.storage_uri)
          ? "Export ready. Download available."
          : `Export created at ${artifact.storage_uri}`,
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to export.";
      setExportMessageByFormat((current) => ({ ...current, [format]: message }));
    } finally {
      setExportStateByFormat((current) => ({ ...current, [format]: "idle" }));
    }
  }

  return (
    <section className="page">
      <div className="hero">
        <h1>Review</h1>
        <p>Load a document to inspect source and extraction output side-by-side.</p>
        <ul className="hint-list">
          <li>Load by document ID to fetch extraction data from the API.</li>
          <li>Field saves validate path and payload; invalid edits return actionable API messages.</li>
          <li>Run export actions after review to generate JSON, CSV, or XLSX artifacts.</li>
        </ul>
        <div className="review-controls">
          <label className="field">
            Document ID
            <input
              type="text"
              placeholder="e.g. 5e9d7af0-..."
              value={documentIdInput}
              onChange={(event) => setDocumentIdInput(event.target.value)}
            />
          </label>
          <label className="field">
            Document URL (optional)
            <input
              type="url"
              placeholder="https://... or local object URL"
              value={documentUrlInput}
              onChange={(event) => setDocumentUrlInput(event.target.value)}
            />
          </label>
          <button type="button" className="button-like button-accent" onClick={handleLoadReview} disabled={isLoading}>
            {isLoading ? "Loading..." : "Load Review"}
          </button>
        </div>
        {errorMessage ? <p className="alert-banner alert-error">{errorMessage}</p> : null}
      </div>

      <div className="review-grid">
        <article className="panel review-panel">
          <h2>Document</h2>
          <div className="review-meta">
            <span>Document ID</span>
            <strong>{activeDocumentId || "-"}</strong>
          </div>
          {activeDocumentUrl ? (
            <iframe
              title="Document preview"
              className="document-frame"
              src={activeDocumentUrl}
            />
          ) : (
            <p className="empty-note">Provide a document URL to render PDF/image preview.</p>
          )}
        </article>

        <article className="panel review-panel">
          <h2>Extracted Data</h2>
          {extraction ? (
            <>
              <div className="review-meta">
                <span>Type</span>
                <strong>{extraction.doc_type}</strong>
              </div>
              <div className="review-meta">
                <span>Schema</span>
                <strong>{extraction.schema_version}</strong>
              </div>
              <div className="review-meta">
                <span>Review Required</span>
                <strong>{extraction.review_required ? "yes" : "no"}</strong>
              </div>
              <div className="confidence-controls">
                <label className="field">
                  Low confidence threshold
                  <input
                    type="number"
                    min={0}
                    max={1}
                    step={0.05}
                    value={lowConfidenceThreshold}
                    onChange={(event) => setLowConfidenceThreshold(Number(event.target.value))}
                  />
                </label>
                <label className="checkbox-field">
                  <input
                    type="checkbox"
                    checked={showLowConfidenceOnly}
                    onChange={(event) => setShowLowConfidenceOnly(event.target.checked)}
                  />
                  Show low-confidence fields only ({lowConfidenceCount})
                </label>
              </div>
              <div className="inline-edit-list">
                {editableFields.length === 0 ? (
                  <p className="empty-note">No editable fields detected.</p>
                ) : (
                  editableFields.map((field) => {
                    const confidence = confidenceForPath(extraction?.confidence_map, field.path);
                    const isLowConfidence = confidence !== null && confidence < lowConfidenceThreshold;
                    return (
                    <div
                      key={field.path}
                      className="inline-edit-row"
                      data-low-confidence={isLowConfidence ? "yes" : "no"}
                    >
                      <label className="field">
                        {field.path}
                        {confidence !== null ? (
                          <span className="confidence-chip" data-low-confidence={isLowConfidence ? "yes" : "no"}>
                            confidence {confidence.toFixed(2)}
                          </span>
                        ) : null}
                        <input
                          type="text"
                          value={String(field.value ?? "")}
                          onChange={(event) =>
                            setFieldValue(field.path, parseFieldInput(event.target.value, field.value))
                          }
                        />
                      </label>
                      <button
                        type="button"
                        className="button-like"
                        onClick={() => saveField(field.path)}
                        disabled={saveStateByPath[field.path] === "saving"}
                      >
                        {saveStateByPath[field.path] === "saving" ? "Saving..." : "Save"}
                      </button>
                      <span className="inline-edit-message">{saveMessageByPath[field.path] ?? ""}</span>
                    </div>
                  );
                  })
                )}
              </div>

              <div className="panel export-panel">
                <h3>Export Actions</h3>
                <p className="empty-note">Generate and download JSON, CSV, or XLSX artifacts.</p>
                <div className="export-actions">
                  {(["json", "csv", "xlsx"] as ExportFormat[]).map((format) => {
                    const artifact = artifactsByFormat[format];
                    const running = exportStateByFormat[format] === "running";
                    return (
                      <div key={format} className="export-row">
                        <button
                          type="button"
                          className="button-like button-accent"
                          onClick={() => runExport(format)}
                          disabled={running}
                        >
                          {running ? `Exporting ${format.toUpperCase()}...` : `Export ${format.toUpperCase()}`}
                        </button>
                        {artifact && isDownloadableUrl(artifact.storage_uri) ? (
                          <a className="button-like" href={artifact.storage_uri} target="_blank" rel="noreferrer">
                            Download
                          </a>
                        ) : null}
                        <span className="inline-edit-message">{exportMessageByFormat[format]}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
              <pre className="review-json">{JSON.stringify(draftPayload, null, 2)}</pre>
            </>
          ) : (
            <p className="empty-note">No extraction loaded yet.</p>
          )}
        </article>
      </div>
    </section>
  );
}
