# Experiment 5: Can an ant colony turn a business need into software?

## Research question

Given one open business requirement and a fixed worker model, can a colony of code-only ants produce a working software service through an emergent work process, and how does its outcome and process compare with centralized development?

This is a new end-to-end experiment. Experiment 4 measures decomposition coverage and isolated coding tasks; it does not establish that a system can be built from a business requirement.

## Pilot requirement

> Operations receives invoice data from suppliers. They need to know which invoices were accepted, which need correction and why, and be confident that no valid invoice disappeared or was processed twice. Build a small service that supports this workflow.

The requirement intentionally leaves the internal architecture, storage choice, validation design, and order of work open. The task is synthetic and contains no customer data.

## Arms

The Pool is common infrastructure, not an experimental arm. Each run receives a clean, isolated workspace and the same basic file, shell, and test tools.

| Arm | Organization | Purpose |
| --- | --- | --- |
| `colony` | Code-only ants select and route work through shared state and pheromone signals. No development phases are prescribed. | Test emergent work organization. |
| `cells` | Four locally coordinated cells work through the shared pool. No global phase sequence is prescribed. | Test whether local specialization changes outcome or process. |
| `central_sdlc` | A central controller uses the same worker model and tools, with explicit requirements, design, test, implementation, and verification phases. | Compare against an explicit human-style SDLC process. |
| `central_free` (recommended control) | A central controller uses the same worker model and tools without prescribed phases. | Separate the effect of decentralization from the effect of prescribing SDLC. |

Run the first three arms if the pilot budget is tight. Include `central_free` in the main comparison if the initial pilot remains within the free quota.

## Fairness and safety controls

- Freeze one model ID and provider for all arms in a comparison. Record the exact model, provider, date, and runtime versions.
- Give every arm the same worker-call, token, and wall-clock ceilings, same tools, same starting repository, and same test feedback.
- The worker API is identical across arms. Only the organizational policy and context passed by that policy may differ.
- Do not route to another provider on errors. Stop when the provider free quota is reached; never enable billing or use a paid fallback.
- Give the agents the business requirement and the public interface contract. Keep evaluator cases and expected outputs hidden from the workers.
- Rotate arm order within each run block. A block contains one run per arm, reducing bias from provider or time-of-day changes.
- Store no API keys in traces, checkpoints, prompts, source files, or result artifacts. Log prompt/response content only in the synthetic sandbox; otherwise store hashes and metadata.

## Acceptance contract

Before model runs, an evaluator who is not implementing the arms must freeze an executable acceptance suite. It should test observable business outcomes, not code style or SDLC compliance. At minimum:

1. Valid invoice records are accounted for after ingestion.
2. Invalid records are identified with a useful reason and can be corrected.
3. Reprocessing the same input does not silently create duplicate invoices.
4. Mixed valid and invalid records do not cause valid records to disappear.
5. The service can be started from its documented instructions in a clean environment.

The team must freeze a minimal launch/input/output contract so the same evaluator can drive every implementation. That contract is an experimental boundary, not a prescribed internal architecture. Publish the contract before runs; keep concrete fixtures, expected results, and edge cases hidden until evaluation. Record the evaluator version and checksum.

## Measures

**Primary outcome:** proportion of runs that pass every critical business acceptance case under the fixed run budget.

**Secondary outcomes:** acceptance cases passed, worker calls and tokens, elapsed time, retry count, integration failures, and failure category. Report calls and time separately; equal call budgets do not imply equal elapsed time.

**Process outcomes:** whether the first meaningful artifact was a test or production code; time and calls until the first test; order of artifact types; number of rewrites; merge/integration conflicts; and how work moved through the pool. A test-first trace is an observed behavior, not a success criterion by itself.

## Trace schema

Append one JSONL event per decision or effect. Required fields:

```json
{
  "run_id": "stable run identifier",
  "arm": "colony | cells | central_sdlc | central_free",
  "seed": 1,
  "tick": 1,
  "event_id": "monotonic event identifier",
  "actor_id": "ant, cell, or controller identifier",
  "event_type": "decision | worker_call | artifact_write | test_run | test_result | pool_update | stop",
  "artifact_path": "relative path or null",
  "artifact_kind": "test | production | config | docs | other | null",
  "task_id": "work item or null",
  "parent_event_id": "causal parent or null",
  "worker_call_index": 0,
  "input_hash": "sha256 or null",
  "output_hash": "sha256 or null",
  "tokens_in": 0,
  "tokens_out": 0,
  "duration_ms": 0,
  "test_status": "pass | fail | not_run | null"
}
```

Also save the final source tree, evaluator report, run configuration, and a trace manifest. Use relative paths; redact secrets before writing any event.

## Replication and analysis

Start with 3 pilot runs per arm. If the harness works and the call distribution fits the free quota, run 30 replications per arm for this requirement. Randomize arm order within blocks and use distinct run seeds. Report raw per-run results, pass-rate confidence intervals, and paired within-block differences. Do not treat the LLM's sampling as deterministic merely because the harness has a seed.

Thirty repetitions of one requirement estimate repeatability on that requirement only. A claim about general ability requires follow-up requirements with different business workflows.

## Work plan

1. **Freeze task and evaluator:** finalize the public requirement, minimal launch contract, hidden fixtures, critical-case list, and evaluator checksum.
2. **Build runner and trace:** isolated workspaces, four arm policies, hard call/token/time ceilings, provider lock, and append-only JSONL traces.
3. **Dry run at $0:** use a deterministic fake worker to validate run scheduling, workspace isolation, trace completeness, stop conditions, and evaluator invocation. This validates plumbing only, not software-building ability.
4. **Pilot:** after a fresh secret is configured in the local environment and free quota is confirmed, run 3 seeds per arm. Review traces and adjust only infrastructure defects; then freeze the protocol again.
5. **Main run:** run up to 30 seeds per arm in randomized blocks. Resume only with the same provider/model and protocol checksum. Stop before quota exhaustion and continue in the next free-quota window.
6. **Blind evaluation and report:** run the frozen evaluator without arm labels, classify failures, analyze outcomes, and publish traces/results with secrets removed.

## Interpretation limits

Using one model in all arms controls model identity for the comparison; it does not remove knowledge the model acquired from code or software-development traces. Research systems have explicitly trained models on developer activity sequences, so training data is a real possible influence, but that fact cannot be generalized to every model. This experiment tests whether orchestration changes the process and the delivered result with a fixed worker. It does not prove that ants independently understand natural-language business intent or invent programming knowledge.

The pilot is not ready for live calls until the evaluator contract is frozen and a new, unexposed API key is configured. A previously disclosed key must not be reused.
