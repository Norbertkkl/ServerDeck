#!/usr/bin/env node
const { spawn, execSync } = require("child_process");
const path = require("path");
const fs = require("fs");
const os = require("os");

function resolvePython() {
  const candidates = ["python3", "python"];
  for (const cmd of candidates) {
    try {
      const ver = execSync(`${cmd} --version 2>&1`, { stdio: "pipe" }).toString();
      if (ver.toLowerCase().includes("python 3")) return cmd;
    } catch (_) {}
  }
  return null;
}

const pyCmd = resolvePython();
if (!pyCmd) {
  console.error("Error: Python 3 is required to run ServerDeck. Please install python3.");
  process.exit(1);
}

const rootDir = path.resolve(__dirname, "..");
const isWin = process.platform === "win32";

function findExistingVenv() {
  const candidates = [
    path.join(rootDir, ".venv"),
    path.join("/opt", "serverdeck", "venv")
  ];
  for (const c of candidates) {
    const p = isWin
      ? path.join(c, "Scripts", "python.exe")
      : path.join(c, "bin", "python3");
    if (fs.existsSync(p)) {
      try {
        execSync(`"${p}" -c "import psutil, yaml"`, { stdio: "pipe" });
        return p;
      } catch (_) {}
    }
  }
  return null;
}

function getVenvDir() {
  const localVenv = path.join(rootDir, ".venv_npm");
  try {
    fs.accessSync(rootDir, fs.constants.W_OK);
    return localVenv;
  } catch (_) {
    const userState = path.join(os.homedir(), ".local", "state", "serverdeck");
    fs.mkdirSync(userState, { recursive: true });
    return path.join(userState, "venv_npm");
  }
}

let venvPy = findExistingVenv();

if (!venvPy) {
  const venvDir = getVenvDir();
  venvPy = isWin
    ? path.join(venvDir, "Scripts", "python.exe")
    : path.join(venvDir, "bin", "python3");

  if (!fs.existsSync(venvPy)) {
    console.log("Setting up ServerDeck runtime environment (first run only)...");
    try {
      execSync(`${pyCmd} -m venv --system-site-packages "${venvDir}"`, { stdio: "inherit" });
    } catch (err) {
      console.error("Failed to initialize virtual environment:", err.message);
      process.exit(1);
    }
  }

  let hasDeps = false;
  try {
    execSync(`"${venvPy}" -c "import psutil, yaml"`, { stdio: "pipe" });
    hasDeps = true;
  } catch (_) {}

  if (!hasDeps) {
    try {
      const pipCmd = isWin
        ? path.join(venvDir, "Scripts", "pip.exe")
        : path.join(venvDir, "bin", "pip");
      const reqFile = path.join(rootDir, "requirements.txt");
      execSync(`"${pipCmd}" install -q -r "${reqFile}"`, { stdio: "inherit" });
    } catch (err) {
      console.warn("Notice: Could not install packages via pip, falling back to system dependencies.");
    }
  }
}

const appEntry = path.join(rootDir, "app.py");
const child = spawn(venvPy, [appEntry, ...process.argv.slice(2)], {
  stdio: "inherit",
  env: { ...process.env, PYTHONUNBUFFERED: "1" }
});

child.on("exit", (code) => {
  process.exit(code !== null ? code : 0);
});
