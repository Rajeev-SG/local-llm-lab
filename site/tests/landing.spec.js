import { expect, test } from "@playwright/test";

test("landing page presents the core lab story and start path", async ({ page }, testInfo) => {
  const consoleErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text());
    }
  });

  await page.goto("/");

  await expect(
    page.getByRole("heading", {
      name: "Build, test, and ship a serious local LLM workstation.",
    }),
  ).toBeVisible();

  await expect(
    page.getByRole("heading", { name: "Use the model that matches the job, not the one that sounds biggest." }),
  ).toBeVisible();

  await expect(page.locator("#models").getByText("mistral-small:22b", { exact: true })).toBeVisible();
  await expect(page.locator("#models").getByText("qwen2.5-coder:14b", { exact: true })).toBeVisible();

  const startLink = page.getByRole("link", { name: "Run the lab" });
  await startLink.click();
  await expect(page.locator("#start")).toBeInViewport();

  await expect(page.getByText("./scripts/start-ollama.sh")).toBeVisible();
  expect(consoleErrors).toEqual([]);

  await page.waitForTimeout(500);
  await page.screenshot({
    path: testInfo.outputPath("landing.png"),
    fullPage: true,
  });
});
