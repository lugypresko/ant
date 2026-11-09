import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const load = (name) => JSON.parse(readFileSync(new URL(name, import.meta.url), "utf8"));

function errors(policy) {
  const result = [];
  if (policy.contract_version !== "1.0.0") result.push("contract_version");
  const profiles = policy.profiles ?? {};
  if (!profiles.execution || !profiles.verification) result.push("profiles");
  if (profiles.execution?.id === profiles.verification?.id) result.push("profile-separation");

  for (const capability of policy.capabilities ?? []) {
    if (!capability.owner || !["controller", "adapter", "sandbox"].includes(capability.owner)) {
      result.push(`unowned-capability:${capability.id ?? "unknown"}`);
    }
  }

  const requiredDenies = ["dns", "direct-ip", "redirect", "ipv6", "cloud-metadata", "private-network"];
  for (const denied of requiredDenies) {
    if (!policy.egress?.deny?.includes(denied)) result.push(`egress:${denied}`);
  }
  if (!Array.isArray(policy.protected_paths) || policy.protected_paths.length === 0) result.push("protected_paths");
  if (policy.secrets?.delivery !== "short-lived-broker") result.push("secret-delivery");
  if (policy.secrets?.redact_logs !== true || policy.secrets?.redact_artifacts !== true) result.push("secret-redaction");
  return result;
}

test("security schema has a stable identity and required policy surfaces", () => {
  const schema = load("./security-policy.schema.json");
  assert.equal(schema.$schema, "https://json-schema.org/draft/2020-12/schema");
  assert.equal(schema.$id, "https://ant.local/contracts/security/security-policy.schema.json");
  assert.deepEqual(schema.required, [
    "contract_version", "profiles", "capabilities", "protected_paths", "egress", "secrets"
  ]);
});

test("valid fixture separates execution and verification and owns every capability", () => {
  assert.deepEqual(errors(load("./fixtures/valid-policy.json")), []);
});

for (const [fixture, expected] of [
  ["invalid-unowned-capability.json", "unowned-capability:shell.exec"],
  ["invalid-shared-profile.json", "profile-separation"],
  ["invalid-egress.json", "egress:cloud-metadata"],
  ["invalid-secret-delivery.json", "secret-delivery"]
]) {
  test(`rejects ${fixture}`, () => {
    assert.ok(errors(load(`./fixtures/${fixture}`)).includes(expected));
  });
}
