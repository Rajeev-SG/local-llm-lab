import { defineConfig, devices } from "@playwright/test";

const localPreviewUrl = "http://127.0.0.1:4273";
const baseURL = process.env.PLAYWRIGHT_BASE_URL || localPreviewUrl;
const useLocalPreview = !process.env.PLAYWRIGHT_BASE_URL;

export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  use: {
    baseURL,
    trace: "on-first-retry",
  },
  webServer: useLocalPreview
    ? {
        command: "pnpm preview --host 127.0.0.1 --port 4273",
        url: localPreviewUrl,
        reuseExistingServer: false,
        timeout: 30_000,
      }
    : undefined,
  projects: [
    {
      name: "desktop",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 1400 },
      },
    },
    {
      name: "mobile",
      use: devices["Pixel 7"],
    },
  ],
});
