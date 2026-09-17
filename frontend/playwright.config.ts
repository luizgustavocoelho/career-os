import { defineConfig, devices } from "@playwright/test";
import path from "node:path";
const python =
  process.env.CAREEROS_PYTHON ||
  (process.platform === "win32"
    ? path.resolve("../.venv/Scripts/python.exe")
    : "python");
export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:3011",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        channel: process.platform === "win32" ? "chrome" : undefined,
      },
    },
  ],
  webServer: [
    {
      command: `"${python}" tests/e2e_server.py`,
      cwd: "../backend",
      url: "http://127.0.0.1:8011/api/health",
      timeout: 60_000,
      reuseExistingServer: false,
    },
    {
      command: "npm run dev -- --port 3011",
      url: "http://127.0.0.1:3011/login",
      timeout: 120_000,
      reuseExistingServer: false,
      env: {
        API_INTERNAL_URL: "http://127.0.0.1:8011",
        NEXT_DIST_DIR: ".next-e2e",
        NEXT_TELEMETRY_DISABLED: "1",
      },
    },
  ],
});
