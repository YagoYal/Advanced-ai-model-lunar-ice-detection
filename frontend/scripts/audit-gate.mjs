// CI gate for `npm audit`: fails on any high/critical advisory that is not in
// audit-allowlist.json. Each allowlist entry has a review_by date; once it has
// passed, the gate fails so the exception gets re-checked instead of living
// forever. No dependencies: plain Node.
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";

const BLOCKING = new Set(["high", "critical"]);

function runAudit() {
  try {
    return execFileSync("npm", ["audit", "--json"], {
      encoding: "utf8",
      shell: process.platform === "win32",
      maxBuffer: 64 * 1024 * 1024,
    });
  } catch (err) {
    // npm audit exits non-zero when it finds anything; the JSON is still on stdout.
    if (err.stdout) return err.stdout;
    throw err;
  }
}

const allowlist = JSON.parse(
  readFileSync(new URL("../audit-allowlist.json", import.meta.url), "utf8"),
);
const report = JSON.parse(runAudit());

const today = new Date().toISOString().slice(0, 10);
const allowed = new Map(allowlist.map((e) => [e.id, e]));
const found = new Map(); // GHSA id -> { severity, title, packages:Set }

for (const [pkg, vuln] of Object.entries(report.vulnerabilities ?? {})) {
  for (const via of vuln.via ?? []) {
    if (typeof via !== "object" || !BLOCKING.has(via.severity)) continue;
    const id = (via.url ?? "").split("/").pop() || via.title;
    const entry = found.get(id) ?? { severity: via.severity, title: via.title, packages: new Set() };
    entry.packages.add(pkg);
    found.set(id, entry);
  }
}

let failed = false;

for (const [id, info] of found) {
  const pkgs = [...info.packages].join(", ");
  const exception = allowed.get(id);
  if (!exception) {
    console.error(`BLOCK  ${id} [${info.severity}] ${info.title} (${pkgs})`);
    failed = true;
  } else if (exception.review_by < today) {
    console.error(`EXPIRED ${id}: allowlist review_by ${exception.review_by} has passed — re-check it (${pkgs})`);
    failed = true;
  } else {
    console.log(`allow  ${id} [${info.severity}] until ${exception.review_by}: ${exception.reason}`);
  }
}

for (const id of allowed.keys()) {
  if (!found.has(id)) {
    console.log(`note   ${id} is no longer reported — remove it from audit-allowlist.json`);
  }
}

if (failed) {
  console.error("npm audit gate: FAILED");
  process.exit(1);
}
console.log(`npm audit gate: OK (${found.size} high/critical advisory(ies), all allowlisted)`);
