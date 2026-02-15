import test from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";

test("frontend tsconfig includes app router sources", () => {
  const tsconfig = JSON.parse(readFileSync(new URL("../tsconfig.json", import.meta.url), "utf8"));
  assert.ok(Array.isArray(tsconfig.include));
  assert.ok(tsconfig.include.includes("**/*.tsx"));
  assert.ok(tsconfig.include.includes("next-env.d.ts"));
});

test("next app shell routes exist", () => {
  const requiredFiles = [
    "../app/layout.tsx",
    "../app/page.tsx",
    "../app/upload/page.tsx",
    "../app/documents/page.tsx",
    "../app/review/page.tsx",
    "../components/nav.tsx",
  ];
  for (const relativePath of requiredFiles) {
    assert.equal(existsSync(new URL(relativePath, import.meta.url)), true, `missing ${relativePath}`);
  }
});

test("navigation links include base routes", () => {
  const nav = readFileSync(new URL("../components/nav.tsx", import.meta.url), "utf8");
  assert.match(nav, /href:\s*"\/"/);
  assert.match(nav, /href:\s*"\/upload"/);
  assert.match(nav, /href:\s*"\/documents"/);
  assert.match(nav, /href:\s*"\/review"/);
});

test("upload page supports single and batch file selectors", () => {
  const uploadPage = readFileSync(new URL("../app/upload/page.tsx", import.meta.url), "utf8");
  assert.match(uploadPage, /Add Single File/);
  assert.match(uploadPage, /Add Batch/);
  assert.match(uploadPage, /Per-file status/);
  assert.match(uploadPage, /multiple/);
});

test("documents page includes search and filter controls", () => {
  const documentsPage = readFileSync(new URL("../app/documents/page.tsx", import.meta.url), "utf8");
  assert.match(documentsPage, /Search by vendor\/file metadata/);
  assert.match(documentsPage, /Start date/);
  assert.match(documentsPage, /End date/);
  assert.match(documentsPage, /status/);
  assert.match(documentsPage, /filterDocuments/);
});

test("review page renders side-by-side review and extraction loading", () => {
  const reviewPage = readFileSync(new URL("../app/review/page.tsx", import.meta.url), "utf8");
  assert.match(reviewPage, /Load a document to inspect source and extraction output side-by-side/);
  assert.match(reviewPage, /Load Review/);
  assert.match(reviewPage, /Document URL \(optional\)/);
  assert.match(reviewPage, /Extracted Data/);
  assert.match(reviewPage, /fetchDocumentExtraction/);
  assert.match(reviewPage, /inline-edit-list/);
  assert.match(reviewPage, /patchDocumentExtraction/);
  assert.match(reviewPage, /Saving\.\.\.|Save/);
});
