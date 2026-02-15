export default function HomePage() {
  return (
    <section className="page">
      <div className="hero">
        <h1>svanDoc MVP Shell</h1>
        <p>Upload documents, track extraction status, review low-confidence fields, and export clean outputs.</p>
        <div className="chip-row">
          <span className="chip">Invoice + Receipt Focus</span>
          <span className="chip">Human-in-the-loop Review</span>
          <span className="chip">JSON / CSV / XLSX Export</span>
        </div>
      </div>
    </section>
  );
}
