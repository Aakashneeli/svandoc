# Frontend Package

This package hosts the Next.js web application.

## Planned responsibilities

1. Upload UI for invoice/receipt documents.
2. Processing status and document library views.
3. Side-by-side extraction review and correction interface.
4. Export actions for JSON, CSV, and XLSX.

## Planned stack

- Next.js
- TypeScript
- Tailwind CSS

## Developer tooling

Install dependencies:

```powershell
npm.cmd --prefix frontend install
```

Run checks:

```powershell
npm.cmd --prefix frontend run typecheck
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run test
```

## Current status

`T-037` is complete: base app-shell routes and navigation are in place.
