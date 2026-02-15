"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { fetchDocumentExtraction, type ExtractionData } from "../../src/review";

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
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setExtraction(null);
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
    } catch (error) {
      setExtraction(null);
      setErrorMessage(error instanceof Error ? error.message : "Unable to load extraction.");
    } finally {
      setIsLoading(false);
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
              <pre className="review-json">{JSON.stringify(extraction.structured_payload, null, 2)}</pre>
            </>
          ) : (
            <p className="empty-note">No extraction loaded yet.</p>
          )}
        </article>
      </div>
    </section>
  );
}
