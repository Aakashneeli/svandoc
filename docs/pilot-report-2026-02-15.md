# Pilot Report (2026-02-15)

## Scope

Pilot cohort size: 6 users from target SME personas (`owner`, `bookkeeper`, `ops_admin`, `finance_admin`).

Workflow tested:
1. Upload
2. Review and correction
3. Export

Dataset source:
1. `datasets/pilot/v1/pilot_sessions.csv`

Metrics computation:
1. `backend/scripts/pilot-metrics.ps1`
2. `svandoc_backend.pilot_metrics`

## Summary Metrics

1. Total pilot sessions: 6
2. Completed upload -> review -> export: 5
3. Completion rate: 83.33%
4. Median time-to-value (first successful export): 410 seconds (6 minutes 50 seconds)
5. Average time-to-value (completed sessions): 425 seconds (7 minutes 5 seconds)
6. Average corrections in completed sessions: 1.8 fields

## Observations

1. Completion rate exceeds MVP usability threshold of 80%.
2. Non-completion case was process-oriented (file naming expectation), not extraction failure.
3. Most corrections were minor formatting or amount-field adjustments.

## Follow-up Inputs for v1.1 Hardening

1. Strengthen upload guidance for naming and accepted formats at intake step.
2. Improve low-confidence explanation text in review panel.
3. Add fast correction shortcuts for common amount/date edits.

