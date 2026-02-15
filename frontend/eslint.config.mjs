import js from "@eslint/js";
import tseslint from "typescript-eslint";

export default [
  {
    ignores: ["node_modules/**", "dist/**", ".next/**"],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["app/**/*.ts", "app/**/*.tsx", "components/**/*.ts", "components/**/*.tsx", "tests/**/*.mjs"],
    rules: {
      "no-console": "off",
    },
  },
];
