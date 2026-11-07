# Experiment 5: Can an ant colony turn a business need into software?

## Research question

Given the same worker model, requirement, tools, and total run budget, does decentralized ant-style organization change the observable software work process relative to a single agent and a centrally orchestrated team? Better final software is not required for the primary process hypothesis to receive support.

This experiment complements Experiment 4, which measures decomposition coverage and isolated coding tasks; it tests an end-to-end open business requirement.

## Pilot requirement

> Operations receives invoice data from suppliers. They need to know which invoices were accepted, which need correction and why, and be confident that no valid invoice disappeared or was processed twice. Build a small service that supports this workflow.

The requirement leaves architecture, storage, validation design, and work sequence open. The task is synthetic and contains no customer data.

## Arms

The initial pilot uses three arms:

| Arm | Organization | Purpose |
| --- | --- | --- |
| \`single\` | One worker receives the full requirement and works alone. | Single-agent baseline. |
| \`central_sdlc\` | A central controller delegates to workers through explicit requirements, design, test, implementation, and verification phases. | Centralized, human-style process. |
| \`colony\` | Homogeneous ants select work from shared repository, test, commit, and pool signals. No controller assigns tasks or roles. | Test self-organized work selection and stigmergic coordination. |

Optional extension arms are \`central_free\` (central controller without prescribed phases) and \`cells\` (four locally coordinated cells). They are excluded from the first pilot to keep its run matrix small. Adding them later requires a protocol revision before collection.

## Fairness and safety controls

- Freeze one model ID and provider for all arms in a comparison. Record model, provider, date, and runtime versions.
- Give every arm the same total worker-call, token, and wall-clock ceilings, tools, starting repository, and test feedback. The budget is shared across planner and workers.
- Keep the worker tool API identical. Only organizational policy and the context supplied by that policy may differ.
- Do not route to another provider on errors. Never enable billing or use a paid fallback. Stop when the selected provider's free quota is reached.
- Give agents the requirement and public interface contract. Keep evaluator cases and expected outputs hidden.
- Rotate arm order within each run block.
- Never store API keys in traces, checkpoints, prompts, source files, or result artifacts. Use synthetic content only.

## Acceptance contract

Before model runs, freeze an executable evaluator for business outcomes, not code style or SDLC compliance. At minimum it checks:

1. Valid invoice records are accounted for after ingestion.
2. Invalid records are identified with a useful reason and can be corrected.
3. Reprocessing the same input does not silently create duplicate invoices.
4. Mixed valid and invalid records do not cause valid records to disappear.
5. The service starts from documented instructions in a clean environment.

Freeze a minimal launch/input/output contract so the same evaluator can drive every implementation. Keep concrete fixtures, expected results, and edge cases hidden until evaluation. Record evaluator version and checksum.

## Measures

**Primary outcome: work-process difference.** Compare the trace distributions across \`single\`, \`central_sdlc\`, and \`colony\`:

- work-selection decisions and their observed environmental signals;
- first meaningful artifact type and order of test versus production artifacts;
- calls and time until the first test;
- test-failure → artifact-write → retest cycles;
- rewrites, task handoffs, shared-file overlap, and pool updates;
- repeated per-agent behavior that may suggest specialization.

A test-first trace is an observed behavior, not a success criterion by itself. Role or specialization labels are heuristic and must be reviewed against the raw traces.

**Secondary outcomes: delivered result and efficiency.**

- Held-out business acceptance pass rate and acceptance cases passed;
- worker calls, tokens, elapsed time, integration failures, and failure categories.

Report process and outcome measures separately. No quality win is assumed.

## Trace schema

Append one JSONL event per decision or effect. Required fields:

\`\`\`json
{
  "run_id": "stable run identifier",
  "arm": "single | central_sdlc | colony | central_free | cells",
  "seed": 1,
  "tick": 1,
  "event_id": "monotonic event identifier",
  "actor_id": "ant, cell, worker, or controller identifier",
  "event_type": "decision | worker_call | artifact_write | test_run | test_result | pool_update | direct_message | stop",
  "task_id": "work item or null",
  "selected_action": "chosen next action or null",
  "decision_basis": ["prior event IDs or artifact paths that informed the decision"],
  "parent_event_id": "causal parent or null",
  "artifact_path": "relative path or null",
  "artifact_kind": "test | production | config | docs | other | null",
  "worker_call_index": 0,
  "input_hash": "sha256 or null",
  "output_hash": "sha256 or null",
  "tokens_in": 0,
  "tokens_out": 0,
  "duration_ms": 0,
  "test_status": "pass | fail | not_run | null"
}
\`\`\`

Use relative paths and redact secrets before writing events. Record token usage on worker-call events only to avoid double-counting. Save the final source tree, evaluator report, run configuration, and trace manifest. \`analyze_traces.py\` summarizes process fields from this schema; it does not replace blind acceptance evaluation.

## Replication and analysis

Start with 3 randomized blocks across the three pilot arms. If the harness works and fits the free quota, expand only after reviewing traces and freezing the protocol. Thirty repetitions of one requirement estimate repeatability on that requirement only; general claims require different business workflows.

Report raw per-run results and paired within-block differences. Do not treat model sampling as deterministic merely because the harness has a seed.

## Work plan

1. Freeze the task, public contract, hidden evaluator, critical cases, and evaluator checksum.
2. Build the runner and append-only trace using the schema above.
3. Dry-run at $0 with deterministic fake workers. This validates plumbing only.
4. Run 3 pilot blocks after confirming the provider's free quota; do not enable billing.
5. Freeze the protocol again before any larger run.
6. Evaluate final builds blind and report process and outcome measures separately.

## Interpretation limits

The same model across arms controls model identity, not its training priors. This study tests whether organization changes behavior and delivered results; it does not establish that agents are free of human software-development norms or independently understand business intent.

The turn-based pilot does not measure effective parallelism, concurrent edit conflicts, failure resilience, or dynamic agent activation.
