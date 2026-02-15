import { SvanDocClient } from "../src/client.mjs";

const apiBaseUrl = process.env.SVANDOC_API_BASE_URL || "http://localhost:8000";
const apiKey = process.env.SVANDOC_API_KEY || "";
if (!apiKey) {
  throw new Error("SVANDOC_API_KEY is required.");
}

const client = new SvanDocClient({ apiBaseUrl, apiKey });
const upload = await client.uploadDocument(new Blob(["%PDF-1.7 sample quickstart"]), "sample-invoice.pdf");
const documentId = upload.document_ids[0];
const jobId = upload.job_ids[0];

const job = await client.getJob(jobId);
const extraction = await client.getExtraction(documentId);
const artifact = await client.exportDocument(documentId, "json");

console.log("upload.document_id", documentId);
console.log("job.status", job.status);
console.log("extraction.doc_type", extraction.doc_type);
console.log("export.storage_uri", artifact.storage_uri);
