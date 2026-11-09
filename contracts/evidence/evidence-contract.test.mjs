import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const here = new URL("./", import.meta.url);
const load = (name) => JSON.parse(readFileSync(new URL(name, here), "utf8"));
const digest = /^[a-f0-9]{64}$/;
const gitSha = /^[a-f0-9]{40}$/;

function validate(record) {
  const errors = [];
  if (record.contract_version !== "evidence.v1") errors.push("contract_version");
  if (!gitSha.test(record.trial.template_commit) || (record.trial.candidate_commit && !gitSha.test(record.trial.candidate_commit))) errors.push("commit_hash");
  if (!Array.isArray(record.attempts) || record.attempts.length === 0) errors.push("attempts");
  if (!Array.isArray(record.gate_results) || !record.gate_results.some((gate) => gate.mandatory)) errors.push("mandatory_gate");
  for (const gate of record.gate_results ?? []) {
    if (!digest.test(gate.output_sha256)) errors.push("gate_hash");
  }
  if (!digest.test(record.cleanup.evidence_sha256)) errors.push("cleanup_hash");
  if (!digest.test(record.terminal_manifest.manifest_sha256)) errors.push("manifest_hash");
  const terminals = record.journal.filter((entry) => entry.terminal);
  if (terminals.length !== 1 || terminals[0]?.sequence !== record.terminal_manifest.terminal_event_sequence) errors.push("terminal_event");
  for (let index = 0; index < record.journal.length; index += 1) {
    const entry = record.journal[index];
    if (entry.sequence !== index + 1 || !digest.test(entry.event_sha256)) errors.push("journal");
    if (index > 0 && entry.previous_event_sha256 !== record.journal[index - 1].event_sha256) errors.push("hash_chain");
  }
  if (record.terminal_manifest.verdict === "PASSED" && record.gate_results.some((gate) => gate.mandatory && gate.status !== "PASS")) errors.push("false_pass");
  for (const key of ["measured_usd", "estimated_usd", "reserved_usd", "unused_reserved_usd", "late_reported_usd"]) {
    if (typeof record.costs[key] !== "number" || record.costs[key] < 0) errors.push(`cost:${key}`);
  }
  return errors;
}

for (const name of ["pass", "fail", "cancel", "timeout", "recovery"]) {
  test(`${name} evidence fixture is valid`, () => {
    assert.deepEqual(validate(load(`fixtures/${name}.json`)), []);
  });
}

test("missing mandatory gates fails closed", () => {
  assert.ok(validate(load("fixtures/invalid-missing-gate.json")).includes("mandatory_gate"));
});

test("missing gate artifact hash fails closed", () => {
  assert.ok(validate(load("fixtures/invalid-missing-hash.json")).includes("gate_hash"));
});

test("journal allows exactly one terminal event", () => {
  assert.ok(validate(load("fixtures/invalid-multiple-terminal.json")).includes("terminal_event"));
});

test("a passed verdict cannot contain a failed mandatory gate", () => {
  assert.ok(validate(load("fixtures/invalid-false-pass.json")).includes("false_pass"));
});

test("schema defines every required evidence entity", () => {
  const schema = load("evidence-contract.schema.json");
  for (const entity of ["Trial", "Attempt", "GateResult", "BudgetEvent", "CleanupResult", "DeliveryRecord", "JournalEvent", "TerminalManifest"]) {
    assert.ok(schema.$defs[entity], `missing $defs.${entity}`);
  }
});
