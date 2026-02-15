# Template Learning (Opt-in)

Last updated: 2026-02-16

## Overview

Template learning captures repeated user corrections for template-applied documents and turns them into suggestions for future template applications.

## Opt-in controls

Per-request header:
- `x-template-learning-opt-in: true|false`

Default fallback:
- `TEMPLATE_LEARNING_DEFAULT_OPT_IN=0`

If neither header nor default enables learning, correction events are stored normally but no learning rules are recorded.

## Learning rule scope

Rules are scoped by:
1. `team_id`
2. `template_id`
3. `field_path`
4. `corrected_value`

Repeated corrections increment `correction_count` and refresh `last_seen_at`.

## Suggestion behavior

When a template is applied:
1. Mapping runs from canonical extraction payload.
2. Learned rules with `correction_count >= 2` are emitted as `template_output.learned_suggestions`.
3. If a mapped source path is missing, the learned value is used as fallback in `mapped_fields`.
