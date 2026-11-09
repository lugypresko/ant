import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const here = new URL("./", import.meta.url);
const load = (name) => JSON.parse(readFileSync(new URL(name, here), "utf8"));
const sha = /^[a-f0-9]{40}$/;

function expectedKey(record) {
  return `delivery:${record.idempotency.trial_id}:${record.idempotency.policy_version}`;
}

function validate(record) {
  const errors = [];
  if (record.contract_version !== "repository-lifecycle.v1") errors.push("contract_version");
  if (record.idempotency_key !== expectedKey(record)) errors.push("idempotency_key");
  if (record.repository.visibility !== "private") errors.push("visibility");
  if (record.repository.default_branch !== "main") errors.push("default_branch");
  if (!record.candidate.feature_branch.startsWith("factory/")) errors.push("feature_branch");
  if (!sha.test(record.candidate.template_commit) || !sha.test(record.candidate.candidate_commit)) errors.push("commit");
  if (record.pull_request && (!record.pull_request.draft || record.pull_request.head_commit !== record.candidate.candidate_commit)) errors.push("pull_request");
  for (const [action, allowed] of Object.entries(record.prohibited_actions)) {
    if (allowed !== false) errors.push(`prohibited:${action}`);
  }
  if (record.reconciliation.remote_conflict && record.status !== "QUARANTINED") errors.push("quarantine");
  return errors;
}

test("repository contract is private, draft-only and idempotent", () => {
  const schema = load("repository-lifecycle.schema.json");
  assert.equal(schema.$id, "https://ant.local/contracts/repository/repository-lifecycle.v1.schema.json");
  assert.deepEqual(validate(load("fixtures/complete.json")), []);
});

test("partial failures prescribe deterministic recovery", () => {
  assert.equal(load("fixtures/failure-after-create.json").reconciliation.next_action, "PUSH_MAIN");
  assert.equal(load("fixtures/failure-after-feature-push.json").reconciliation.next_action, "OPEN_DRAFT_PR");
  assert.equal(load("fixtures/failure-after-pr.json").reconciliation.next_action, "WAIT_FOR_CI");
});

test("public repositories and forbidden actions fail closed", () => {
  assert.ok(validate(load("fixtures/invalid-public.json")).includes("visibility"));
  assert.ok(validate(load("fixtures/invalid-merge.json")).includes("prohibited:merge"));
});

test("remote conflict requires quarantine", () => {
  assert.ok(validate(load("fixtures/invalid-conflict.json")).includes("quarantine"));
});

test("idempotency key is derived from trial and policy", () => {
  assert.ok(validate(load("fixtures/invalid-idempotency.json")).includes("idempotency_key"));
});
