import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const workspace = readFileSync(new URL("../pnpm-workspace.yaml", import.meta.url), "utf8");
const status = JSON.parse(readFileSync(new URL("./status.json", import.meta.url), "utf8"));

test("workspace discovers factory and experiment packages", () => {
  assert.match(workspace, /factory\/\*/);
  assert.match(workspace, /experiments\/\*/);
});

test("status board contains every planned work package", () => {
  const expected = [
    "WP-000", "WP-010", "WP-011", "WP-012", "WP-013", "WP-014", "WP-015",
    "WP-100", "WP-110", "WP-120", "WP-130", "WP-140",
    "WP-200", "WP-210", "WP-220", "WP-230",
    "WP-300", "WP-310", "WP-320", "WP-400", "WP-410", "WP-500", "WP-510", "WP-520"
  ];

  assert.deepEqual(Object.keys(status.work_packages).sort(), expected.sort());
  assert.ok(Object.values(status.work_packages).every((value) => value === "pending"));
});
