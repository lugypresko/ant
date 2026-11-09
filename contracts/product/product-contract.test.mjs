import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const here = dirname(fileURLToPath(import.meta.url));
const load = (name) => JSON.parse(readFileSync(join(here, "fixtures", name), "utf8"));
const sha = /^[0-9a-f]{40}$/;

function validate(value) {
  return value.contract_version === "1.0.0"
    && /^INTENT-[0-9]+$/.test(value.business_intent?.id ?? "")
    && typeof value.business_intent?.summary === "string" && value.business_intent.summary.length > 0
    && Array.isArray(value.acceptance_criteria) && value.acceptance_criteria.length > 0
    && value.acceptance_criteria.every((criterion) => /^REQ-[0-9]+$/.test(criterion.id)
      && criterion.statement.length > 0 && criterion.check_ids?.length > 0)
    && sha.test(value.local_output?.repository_template_sha ?? "")
    && sha.test(value.local_output?.candidate_sha ?? "")
    && value.local_output?.verified === true
    && value.remote_delivery?.mode === "draft_pull_request"
    && value.remote_delivery?.visibility === "private"
    && value.remote_delivery?.merge_allowed === false
    && value.remote_delivery?.deploy_allowed === false;
}

test("accepts the frozen M0 product contract", () => assert.equal(validate(load("valid.json")), true));

for (const name of readdirSync(join(here, "fixtures")).filter((name) => name.startsWith("invalid-"))) {
  test(`rejects ${name}`, () => assert.equal(validate(load(name)), false));
}

test("schema exposes the four public product definitions", () => {
  const schema = JSON.parse(readFileSync(join(here, "product-contract.schema.json"), "utf8"));
  assert.deepEqual(Object.keys(schema.$defs).sort(), ["acceptanceCriterion", "businessIntent", "candidateCommit", "deliveryResult"]);
});
