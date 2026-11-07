# Pilot hypotheses: process first

## Primary hypothesis

With the same worker model, requirement, tools, and total run budget, decentralized colony organization changes the observable work process relative to a single agent and a centrally orchestrated SDLC team. Better final code is not required for this hypothesis to receive support.

## Pilot arms

- \`single\`: one worker receives the complete requirement and works alone.
- \`central_sdlc\`: a central controller assigns work through explicit requirements, design, test, implementation, and verification phases.
- \`colony\`: homogeneous ants choose work from shared repository, test, commit, and pool signals; no controller assigns tasks or roles.

\`central_free\` and \`cells\` remain optional extension arms, not part of the initial three-arm pilot.

## Observable process measures

- Selected work and the environmental signals that preceded the decision.
- First meaningful artifact type: tests or production code.
- Calls and time until the first test.
- Work sequence and test-failure → edit → retest cycles.
- Rewrites, task handoffs, artifact overlap, and pool updates.
- Repeated per-agent behavior that may suggest specialization. Role labels are heuristic and require trace review.

A test-first sequence is an observed behavior, not a success criterion by itself.

## Secondary outcomes

- Held-out business acceptance result and acceptance cases passed.
- Worker calls, tokens, elapsed time, integration failures, and failure categories.

## Interpretation

Repeated, distinguishable colony traces support the process hypothesis even if acceptance quality is unchanged. If the colony repeatedly follows the same work pattern as the controls, that is evidence against the hypothesis for this model, task, and implementation.

## Limits

- The turn-based pilot does not measure parallel speedup, concurrent edit conflicts, failure resilience, or dynamic agent activation.
- One invoice-intake requirement estimates repeatability on that requirement only.
- Model training priors remain present in every arm. The study tests whether organization changes behavior; it does not establish that agents are free of human software-development norms.
