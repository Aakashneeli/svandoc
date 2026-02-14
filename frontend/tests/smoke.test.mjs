import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

test("frontend tsconfig includes src", () => {
  const tsconfig = JSON.parse(readFileSync(new URL("../tsconfig.json", import.meta.url), "utf8"));
  assert.ok(Array.isArray(tsconfig.include));
  assert.ok(tsconfig.include.includes("src/**/*.ts"));
});
