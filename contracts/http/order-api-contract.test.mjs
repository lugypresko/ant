import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const here = dirname(fileURLToPath(import.meta.url));
const load = (name) => JSON.parse(readFileSync(join(here, "fixtures", name), "utf8"));
const same = (actual, expected) => expected.every((value) => actual.includes(value));

function validate(value) {
  const idempotency = value.idempotency ?? {};
  const create = value.endpoints?.create_order ?? {};
  const get = value.endpoints?.get_order ?? {};
  const concurrency = value.concurrency ?? {};
  return value.contract_version === "1.0.0"
    && value.media_type === "application/json"
    && idempotency.header === "Idempotency-Key"
    && idempotency.min_length === 8 && idempotency.max_length === 128
    && idempotency.pattern === "^[A-Za-z0-9._:-]+$"
    && idempotency.payload_hash === "sha256-rfc8785-canonical-json"
    && create.method === "POST" && create.path === "/orders" && same(create.responses ?? [], [201, 200, 409, 422])
    && get.method === "GET" && get.path === "/orders/{order_id}" && same(get.responses ?? [], [200, 404])
    && concurrency.equivalent_requests === 8 && concurrency.sqlite_journal_mode === "WAL"
    && concurrency.busy_timeout_ms === 5000 && concurrency.retry_deadline_ms === 5000
    && concurrency.expected_rows === 1 && concurrency.unhandled_lock_errors === 0;
}

test("accepts the frozen order API contract", () => assert.equal(validate(load("valid.json")), true));

for (const name of readdirSync(join(here, "fixtures")).filter((name) => name.startsWith("invalid-"))) {
  test(`rejects ${name}`, () => assert.equal(validate(load(name)), false));
}

test("schema defines request, response, error, idempotency and concurrency contracts", () => {
  const schema = JSON.parse(readFileSync(join(here, "order-api-contract.schema.json"), "utf8"));
  for (const name of ["createOrderRequest", "orderResponse", "errorResponse", "idempotencyPolicy", "concurrencyPolicy"]) {
    assert.ok(schema.$defs[name], `${name} is missing`);
  }
});
