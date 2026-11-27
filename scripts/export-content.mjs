import { readdirSync, existsSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

export function exportContent() {
  const root = process.cwd();
  const candidates = process.env.PYTHON ? [process.env.PYTHON] : [];

  if (process.platform === "win32") {
    const localPrograms = process.env.LOCALAPPDATA && join(process.env.LOCALAPPDATA, "Programs", "Python");
    if (localPrograms && existsSync(localPrograms)) {
      const installs = readdirSync(localPrograms)
        .filter((name) => /^Python\d+$/.test(name))
        .sort((a, b) => Number(b.slice(6)) - Number(a.slice(6)))
        .map((name) => join(localPrograms, name, "python.exe"));
      candidates.push(...installs);
    }
    candidates.push("py", "python3", "python");
  } else {
    candidates.push("python3", "python");
  }

  for (const command of candidates) {
    const result = spawnSync(command, ["export_content.py"], { cwd: root, stdio: "inherit" });
    if (!result.error && result.status === 0) return true;
    if (!result.error && result.status !== 0) process.exit(result.status ?? 1);
    if (result.error && !["ENOENT", "EACCES"].includes(result.error.code)) {
      console.error(`Could not run the content exporter with ${command}: ${result.error.message}`);
    }
  }

  console.error("Python 3 is required to prepare the course files. Install Python or set PYTHON to its executable path.");
  process.exit(1);
}

if (import.meta.url === new URL(`file://${process.argv[1].replaceAll("\\", "/")}`).href) exportContent();
