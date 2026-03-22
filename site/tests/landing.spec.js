import { expect, test } from "@playwright/test";

test("landing page presents the core lab story and start path", async ({ page }, testInfo) => {
  const consoleErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text());
    }
  });

  await page.goto("/");

  await expect(page.locator("main h1")).toContainText(
    "Build, test, and ship a serious local LLM workstation.",
  );

  await expect(page.locator("#models h2")).toContainText(
    "Use the model that matches the job, not the one that sounds biggest.",
  );

  await expect(page.locator("#models").getByText("mistral-small:22b", { exact: true })).toBeVisible();
  await expect(page.locator("#models").getByText("qwen2.5-coder:14b", { exact: true })).toBeVisible();

  const startLink = page.getByRole("link", { name: "Run the lab" });
  await startLink.click();
  await expect(page.locator("#start")).toBeInViewport();

  await expect(page.getByText("./scripts/start-ollama.sh")).toBeVisible();
  await expect(page.getByRole("link", { name: "Open via OrbStack" })).toHaveAttribute(
    "href",
    "http://open-webui-lab.orb.local",
  );
  await expect(page.getByRole("link", { name: "Use localhost fallback" })).toHaveAttribute(
    "href",
    "http://localhost:3001",
  );
  await expect(page.getByText("This only works on the Mac that is actually running the lab.")).toBeVisible();
  expect(consoleErrors).toEqual([]);

  await page.waitForTimeout(500);
  await page.screenshot({
    path: testInfo.outputPath("landing.png"),
    fullPage: true,
  });
});
