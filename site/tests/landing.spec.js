import { expect, test } from "@playwright/test";

test("the guide presents and filters the current installed model inventory", async ({
  page,
}, testInfo) => {
  const consoleErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  await page.goto("/");

  await expect(page.locator("main h1")).toContainText(
    "Every local model on this Mac, in one guide.",
  );
  await expect(page.getByText("23", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Qwen3 Coder 30B A3B" }).first()).toBeVisible();
  await expect(page.getByText("98.3", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Text", { exact: true }).first()).toBeVisible();

  await page.getByRole("button", { name: "Image input" }).click();
  await expect(page.getByText(/of 23 installed builds/)).toBeVisible();
  await expect(
    page.locator("#inventory").getByRole("heading", { name: "Qwen3.6 35B A3B" }),
  ).toBeVisible();
  await expect(
    page.locator("#inventory").getByRole("heading", { name: "Whisper Large v3 Turbo" }),
  ).toHaveCount(0);

  await page.getByRole("button", { name: "All capabilities" }).click();
  await page.getByRole("button", { name: "Ollama", exact: true }).click();
  await page.getByPlaceholder("Model, task, capability, or alias").fill("local-helper-fast");
  await expect(
    page.locator("#inventory").getByRole("heading", { name: "Qwen3.5 9B", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("1 of 23 installed builds")).toBeVisible();

  await page.getByText("Details and source").click();
  await expect(page.getByText(/aliases: local-helper-fast/)).toBeVisible();
  await expect(page.getByRole("link", { name: "Open the exact model page ↗" })).toBeVisible();

  await expect(page.getByRole("heading", { name: "Old evidence stays visible." })).toBeVisible();
  await page.locator("#inventory").screenshot({
    path: testInfo.outputPath("inventory-filtered.png"),
  });
  await page.locator("#aliases").screenshot({
    path: testInfo.outputPath("aliases.png"),
  });
  await page.locator("#historical").screenshot({
    path: testInfo.outputPath("historical.png"),
  });

  await page.getByPlaceholder("Model, task, capability, or alias").fill("");
  await page.getByRole("button", { name: "All runtimes" }).click();
  await expect(page.getByText("23 of 23 installed builds")).toBeVisible();
  await page.locator(".hero").screenshot({
    path: testInfo.outputPath("hero.png"),
  });
  expect(consoleErrors).toEqual([]);

  await page.screenshot({
    path: testInfo.outputPath("model-guide.png"),
    fullPage: true,
  });
});
