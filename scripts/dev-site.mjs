import { spawnSync } from "node:child_process";
import { join } from "node:path";

const root = process.cwd();
const node = process.execPath;
const build = spawnSync(node, [join(root, "scripts", "build-site.mjs")], { cwd: root, stdio: "inherit" });
if (build.error) throw build.error;
if (build.status !== 0) process.exit(build.status ?? 1);

const wrangler = join(root, "node_modules", "wrangler", "bin", "wrangler.js");
const env = { ...process.env, XDG_CONFIG_HOME: join(root, ".wrangler", "config") };
const preview = spawnSync(node, [wrangler, "pages", "dev", "dist", "--ip", "127.0.0.1", "--port", "8788"], {
  cwd: root,
  env,
  stdio: "inherit",
});
if (preview.error) throw preview.error;
process.exit(preview.status ?? 1);
