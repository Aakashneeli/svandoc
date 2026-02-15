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
