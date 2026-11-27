import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { exportContent } from "./export-content.mjs";

const root = process.cwd();
exportContent();

const vite = join(root, "node_modules", "vite", "bin", "vite.js");
const build = spawnSync(process.execPath, [vite, "build", "--configLoader", "native"], { cwd: root, stdio: "inherit" });
if (build.error) throw build.error;
process.exit(build.status ?? 1);
