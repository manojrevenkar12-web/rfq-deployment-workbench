import { expect, type Page, test } from "@playwright/test";

/** Fails the test on any script error; 4xx answers the console handles on purpose are not errors. */
function watchErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (m) => {
    if (m.type() === "error" && !m.text().includes("status of 4")) errors.push(m.text());
  });
  return errors;
}

async function noSideways(page: Page) {
  const wide = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(wide).toBeLessThanOrEqual(1);
}

test("from the portfolio to a customer's process and back", async ({ page }) => {
  const errors = watchErrors(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Deployments" })).toBeVisible();
  await expect(page.getByRole("region", { name: /Held-out set v1/ })).toBeVisible();
  await noSideways(page);
  await page
    .getByRole("region", { name: "Customers" })
    .getByRole("link", { name: "Voltaro Ladetechnik GmbH" })
    .click();
  await expect(page.getByRole("heading", { level: 1, name: "Voltaro Ladetechnik GmbH" })).toBeVisible();
  await page
    .getByRole("navigation", { name: "Customer views" })
    .getByRole("link", { name: "Process" })
    .click();
  await expect(page.getByRole("img", { name: /The average tender today/ })).toBeVisible();
  await page.getByText("With the agents in scope").click();
  await expect(page.getByRole("img", { name: /with the agents in scope/ })).toBeVisible();
  await expect(page.getByRole("region", { name: "Effort per activity since go-live" })).toBeVisible();
  await noSideways(page);
  expect(errors).toEqual([]);
});

test("a sales engineer reviews a red flag and downloads the compliance matrix", async ({ page }) => {
  const errors = watchErrors(page);
  await page.goto("/c/voltaro/tenders");
  const table = page.getByRole("region", { name: "Tenders", exact: true });
  await expect(table).toBeVisible();
  await table.getByRole("link").first().click();
  await expect(page.getByRole("heading", { name: "Requirements" })).toBeVisible();
  await page.getByLabel("Reviewing as").fill("E2E Reviewer");
  const group = page.getByRole("group", { name: /^Review / }).first();
  await group.getByRole("button", { name: "Confirm" }).click();
  await expect(page.getByText("Confirmed by E2E Reviewer").first()).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download compliance matrix" }).click();
  expect((await download).suggestedFilename()).toMatch(/-compliance\.xlsx$/);
  await page.reload();
  await expect(page.getByText("Confirmed by E2E Reviewer").first()).toBeVisible();
  expect(errors).toEqual([]);
});

test("the value case follows the scope", async ({ page }) => {
  const errors = watchErrors(page);
  await page.goto("/c/gleiswerk/value");
  const statement = page.getByText(/hours a year come back/).first();
  await expect(statement).toBeVisible();
  const before = await statement.textContent();
  await page.getByRole("checkbox", { name: /Requirements/ }).uncheck();
  await expect(statement).not.toHaveText(before ?? "");
  await page.getByRole("button", { name: "Back to the agreed case" }).click();
  await expect(statement).toHaveText(before ?? "");
  await noSideways(page);
  expect(errors).toEqual([]);
});

test("an unknown address says so", async ({ page }) => {
  await page.goto("/c/nobody");
  await expect(page.getByRole("alert")).toContainText("no customer nobody");
  await page.goto("/somewhere/else");
  await expect(page.getByRole("heading", { name: "There is nothing at this address" })).toBeVisible();
});
