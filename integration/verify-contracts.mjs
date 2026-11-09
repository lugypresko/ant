import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";

async function schemas(root) {
  const found = [];
  for (const entry of await readdir(root, { withFileTypes: true }).catch(() => [])) {
    const path = join(root, entry.name);
    if (entry.isDirectory()) found.push(...await schemas(path));
    else if (entry.name.endsWith(".schema.json")) found.push(path);
  }
  return found;
}

const ids = new Set();
for (const path of await schemas("contracts")) {
  const document = JSON.parse(await readFile(path, "utf8"));
  if (typeof document.$id !== "string" || document.$id.length === 0) {
    throw new Error(`${path}: schema requires a non-empty $id`);
  }
  if (ids.has(document.$id)) throw new Error(`${path}: duplicate $id ${document.$id}`);
  ids.add(document.$id);
}

console.log(`verified ${ids.size} contract schemas`);
