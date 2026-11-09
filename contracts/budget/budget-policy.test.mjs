import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const load = (name) => JSON.parse(readFileSync(new URL(name, import.meta.url), "utf8"));
const requiredCosts = ["agent", "repair", "integration", "verification", "delivery"];

function errors(policy) {
  const result = [];
  if (policy.contract_version !== "1.0.0") result.push("contract_version");
  if (!(policy.hard_limit_usd > 0)) result.push("hard_limit_usd");
  if (!(policy.token_limit > 0)) result.push("token_limit");
  if (!(policy.wall_clock_deadline_seconds > 0)) result.push("deadline");
  if (policy.max_total_attempts !== 3) result.push("max_total_attempts");
  for (const component of requiredCosts) {
    if (!policy.cost_components?.includes(component)) result.push(`cost:${component}`);
  }
  if (policy.require_reservation_before_operation !== true) result.push("reservation-required");
  if (policy.late_usage?.may_increase_remaining_budget !== false) result.push("late-usage-increase");
  if (policy.late_usage?.record_after_terminal !== true) result.push("late-usage-terminal");
  for (const reason of ["cancellation", "exhaustion"]) {
    const actions = policy.terminal_actions?.[reason] ?? [];
    for (const action of ["block-new-operations", "revoke-credentials", "terminate-process-tree", "cleanup-trial-resources"]) {
      if (!actions.includes(action)) result.push(`terminal:${reason}:${action}`);
    }
  }
  for (const event of policy.events ?? []) {
    if (event.amount_usd < 0 || event.tokens < 0) result.push(`event-negative:${event.type}`);
    if (event.type === "RESERVED" && !(event.amount_usd > 0 || event.tokens > 0)) {
      result.push("reservation-empty");
    }
  }
  return result;
}

test("budget schema covers reservation and late usage events", () => {
  const schema = load("./budget-policy.schema.json");
  assert.equal(schema.$id, "https://ant.local/contracts/budget/budget-policy.schema.json");
  assert.deepEqual(schema.$defs.budgetEvent.properties.type.enum, [
    "RESERVED", "RECONCILED", "RELEASED", "EXHAUSTED", "LATE_USAGE_RECORDED"
  ]);
});

test("valid policy enforces all paid components and three total attempts", () => {
  assert.deepEqual(errors(load("./fixtures/valid-policy.json")), []);
});

for (const [fixture, expected] of [
  ["invalid-negative-limit.json", "hard_limit_usd"],
  ["invalid-attempt-count.json", "max_total_attempts"],
  ["invalid-missing-verification-cost.json", "cost:verification"],
  ["invalid-operation-without-reservation.json", "reservation-required"],
  ["invalid-late-usage.json", "late-usage-increase"],
  ["invalid-negative-reserved-event.json", "event-negative:RESERVED"],
  ["invalid-empty-reserved-event.json", "reservation-empty"],
  ["invalid-cancellation-actions.json", "terminal:cancellation:revoke-credentials"],
  ["invalid-exhaustion-actions.json", "terminal:exhaustion:cleanup-trial-resources"]
]) {
  test(`rejects ${fixture}`, () => {
    assert.ok(errors(load(`./fixtures/${fixture}`)).includes(expected));
  });
}
