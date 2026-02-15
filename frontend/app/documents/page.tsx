"use client";

import { useMemo, useState } from "react";
import { type DocumentListItem, filterDocuments, type DocumentStatus } from "../../src/documents";

const SAMPLE_DOCUMENTS: DocumentListItem[] = [
  { id: "doc-901", filename: "invoice-acme.pdf", vendor: "ACME Industrial", status: "completed", amountTotal: 1200.5, createdAt: "2026-02-15" },
  { id: "doc-902", filename: "receipt-store-7.jpg", vendor: "Store Seven", status: "review_required", amountTotal: 76.23, createdAt: "2026-02-14" },
  { id: "doc-903", filename: "invoice-metro.pdf", vendor: "Metro Logistics", status: "processing", amountTotal: 540.0, createdAt: "2026-02-14" },
  { id: "doc-904", filename: "invoice-novum.pdf", vendor: "Novum Labs", status: "failed", amountTotal: 890.0, createdAt: "2026-02-13" },
  { id: "doc-905", filename: "receipt-cafe-88.png", vendor: "Cafe 88", status: "queued", amountTotal: 18.9, createdAt: "2026-02-12" },
];

const STATUS_FILTERS: Array<"all" | DocumentStatus> = ["all", "queued", "processing", "review_required", "completed", "failed"];

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value);
}

export default function DocumentsPage() {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<"all" | DocumentStatus>("all");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const filtered = useMemo(
    () => filterDocuments(SAMPLE_DOCUMENTS, { query, status, startDate, endDate }),
    [query, status, startDate, endDate],
  );

  return (
    <section className="page">
      <div className="hero">
        <h1>Documents</h1>
        <p>Search by vendor/file metadata and narrow by status or date range.</p>
      </div>

      <div className="panel">
        <h2>Filters</h2>
        <div className="filter-grid">
          <label className="field">
            Search
            <input
              type="text"
              placeholder="Vendor, file name, or document id"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          <label className="field">
            Status
            <select value={status} onChange={(event) => setStatus(event.target.value as "all" | DocumentStatus)}>
              {STATUS_FILTERS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Start date
            <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
          </label>
          <label className="field">
            End date
            <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
          </label>
        </div>
      </div>

      <div className="panel">
        <h2>Results ({filtered.length})</h2>
        {filtered.length === 0 ? (
          <p className="empty-note">No documents match current filters.</p>
        ) : (
          <ul className="document-list">
            {filtered.map((item) => (
              <li key={item.id} className="document-row">
                <div>
                  <div className="upload-file">{item.vendor}</div>
                  <div className="upload-meta">
                    {item.filename}
                    {" | "}
                    {item.id}
                  </div>
                </div>
                <div className="status-badge" data-status={item.status}>
                  {item.status}
                </div>
                <div className="document-amount">{formatCurrency(item.amountTotal)}</div>
                <div className="document-date">{item.createdAt}</div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
