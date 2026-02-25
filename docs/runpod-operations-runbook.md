# RunPod Inference Operations Runbook

Last updated: 2026-02-25

This runbook defines operational procedures for svanDoc RunPod-hosted OCR inference.

## Scope

1. Primary OCR endpoint (`dots.ocr`) and fallback OCR endpoint (`chandra`).
2. Environment contract and rollout readiness checks.
3. Scaling, cost, secret rotation, and incident handling.

## Environment Contract

Required variables for managed environments:

1. `VLLM_BASE_URL` (RunPod OpenAI-compatible URL for `OCR_DEFAULT_MODEL`).
2. `VLLM_FALLBACK_BASE_URL` (RunPod OpenAI-compatible URL for `OCR_FALLBACK_MODEL`).
3. `VLLM_API_KEY` (RunPod API token; never commit to source control).
4. `RUNPOD_ENDPOINT_ID_PRIMARY` and `RUNPOD_ENDPOINT_ID_FALLBACK` (ops references).
5. `OCR_DEFAULT_MODEL=rednote-hilab/dots.ocr`.
6. `OCR_FALLBACK_MODEL=datalab-to/chandra`.
7. Hosted retry policy:
   - `VLLM_TIMEOUT_SECONDS=45`
   - `VLLM_MAX_RETRIES=3`
   - `VLLM_RETRY_BACKOFF_SECONDS=1`
   - `VLLM_RETRY_MAX_BACKOFF_SECONDS=20`
8. Queue fail-closed policy:
   - `PROCESSING_MAX_RETRIES=3`
   - `PROCESSING_RETRY_BACKOFF_SECONDS=5`

## Endpoint Lifecycle

### Provision

1. Create two RunPod serverless endpoints:
   - Primary endpoint serving `rednote-hilab/dots.ocr`.
   - Fallback endpoint serving `datalab-to/chandra`.
2. Capture endpoint IDs and generated OpenAI-compatible base URLs.
3. Save endpoint IDs in `RUNPOD_ENDPOINT_ID_PRIMARY` and `RUNPOD_ENDPOINT_ID_FALLBACK`.

### Activate

1. Configure managed env vars (`VLLM_*`, `OCR_*`) before API/worker rollout.
2. Run inference smoke before traffic cutover:
   - `powershell -NoProfile -ExecutionPolicy Bypass -File backend/scripts/inference-smoke.ps1`
3. Require `result_code=SMOKE_OK` and `overall_success=true`.

### Update

1. For model/version changes, create replacement endpoint first.
2. Smoke-validate replacement endpoint out of band.
3. Swap `VLLM_BASE_URL` or `VLLM_FALLBACK_BASE_URL` via config-only deploy.
4. Keep prior endpoint available until post-deploy smoke passes.

### Decommission

1. Remove endpoint from active env config.
2. Verify no active references in deployment config and runbooks.
3. Archive final health/cost evidence before deletion.

## Scaling Guidance

1. Track `queue_depth` and job latency from `/metrics`.
2. Scale endpoint capacity when either condition persists for 10+ minutes:
   - Queue depth above alert threshold.
   - P95 processing latency above SLA target.
3. Scale both primary and fallback paths; fallback must remain warm enough for routed jobs.
4. After scaling changes, rerun inference smoke and one upload -> extraction smoke.

## Cost Controls

1. Keep fallback endpoint sized for burst/recovery, not primary steady-state load.
2. Review per-endpoint cost and invocation rates daily during launch week.
3. Use scheduled downscaling when non-business-hour traffic is consistently low.
4. Keep retry settings bounded (`VLLM_MAX_RETRIES`, `PROCESSING_MAX_RETRIES`) to prevent runaway retries.
5. Alert on repeated fallback routing spikes because they often increase cost and signal quality drift.

## Secret Rotation

Rotate `VLLM_API_KEY` at least quarterly or immediately after suspected exposure.

1. Create a new RunPod API key.
2. Store key in managed secret store (do not write to tracked files).
3. Deploy API and worker with the new key.
4. Run inference smoke and one end-to-end upload -> export smoke.
5. Revoke the previous key only after successful validation.
6. Record rotation timestamp and owner in release notes.

## Incident and Rollback Procedures

### Common Signals

1. Inference smoke fails with endpoint/model/completion failure codes.
2. Queue backlog rises while `job.failed` events increase.
3. Worker logs show repeated inference timeout/transport failures.

### Incident Response

1. Confirm scope:
   - Primary only.
   - Fallback only.
   - Both endpoints.
2. If one endpoint is unhealthy, route config to known-good endpoint/model pair when safe.
3. If both endpoints are unhealthy, keep fail-closed policy active and allow retry/dead-letter handling.
4. Communicate status with active failure codes and ETA.

### Rollback

1. Revert to last known-good endpoint URL and API key.
2. Redeploy worker and API with reverted env vars.
3. Re-run inference smoke and managed smoke path.
4. Keep incident timeline, root cause, and mitigations in postmortem notes.

## Deploy Gate Automation

The release gate is enforced by:

1. Local/ops command:
   - `powershell -NoProfile -ExecutionPolicy Bypass -File backend/scripts/runpod-readiness-gate.ps1`
2. CI workflow:
   - `.github/workflows/runpod-readiness-gate.yml`

Both paths fail closed when RunPod readiness checks fail.

## Release Checklist (RunPod Ops)

1. RunPod endpoint URLs and IDs are set and non-placeholder.
2. `VLLM_API_KEY` present in secret store and recently validated.
3. Inference smoke passes for primary and fallback targets.
4. Managed upload -> queue -> extraction -> review -> export smoke passes.
5. Rollback endpoint config values are documented and ready.
6. RunPod readiness gate command/workflow passes with evidence artifact.
