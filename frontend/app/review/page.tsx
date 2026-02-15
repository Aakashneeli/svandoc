"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  fetchDocumentExtraction,
  flattenEditableFields,
  patchDocumentExtraction,
  type ExtractionData,
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

  const editableFields = flattenEditableFields(draftPayload);

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

  function getFieldValue(path: string): PrimitiveValue | null {
    let pointer: unknown = draftPayload;
    for (const token of path.split(".")) {
      const tokenIndex = Number.parseInt(token, 10);
      const isArrayIndex = Number.isInteger(tokenIndex) && token === String(tokenIndex);
      if (isArrayIndex) {
        if (!Array.isArray(pointer) || tokenIndex < 0 || tokenIndex >= pointer.length) {
          return null;
        }
        pointer = pointer[tokenIndex];
        continue;
      }
      if (!pointer || typeof pointer !== "object" || !(token in (pointer as Record<string, unknown>))) {
        return null;
      }
      pointer = (pointer as Record<string, unknown>)[token];
    }

    if (
      pointer === null
      || typeof pointer === "string"
      || typeof pointer === "number"
      || typeof pointer === "boolean"
    ) {
      return pointer;
    }
    return null;
  }

  async function saveField(path: string) {
    if (!activeDocumentId || !extraction) {
      return;
    }
    const nextValue = getFieldValue(path);
    if (nextValue === null && nextValue !== getFieldValue(path)) {
      return;
    }
    setSaveStateByPath((current) => ({ ...current, [path]: "saving" }));
    setSaveMessageByPath((current) => ({ ...current, [path]: "" }));
    try {
      const result = await patchDocumentExtraction(API_BASE_URL, activeDocumentId, [{ field_path: path, new_value: nextValue }]);
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

  return (
    <section className="page">
      <div className="hero">
        <h1>Review</h1>
        <p>Load a document to inspect source and extraction output side-by-side.</p>
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
        {errorMessage ? <p className="review-error">{errorMessage}</p> : null}
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
              <div className="inline-edit-list">
                {editableFields.length === 0 ? (
                  <p className="empty-note">No editable fields detected.</p>
                ) : (
                  editableFields.map((field) => (
                    <div key={field.path} className="inline-edit-row">
                      <label className="field">
                        {field.path}
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
                  ))
                )}
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
