import { test, expect, type Page } from "@playwright/test";
import { createAccountAtCheckout } from "./auth";

// SCRUM-7: promo codes at checkout.
// Cases: agentic-workflows/functional-testing/runs/SCRUM-7/spec.yaml
// Every asserted amount and message comes from that case's `expected`.
// Shared setup: Alans Kitchen (/chef/24), delivery 500 AMD, free from 5,000 AMD.

type Line = { dish: string; price: string; qty?: number };

/** Adds dishes through the dish dialog (no additions), then opens checkout,
 *  signs a fresh customer up and chooses Delivery. */
async function startCheckout(page: Page, lines: Line[], name: string) {
  await page.goto("/chef/24");
  for (const { dish, price, qty = 1 } of lines) {
    await page
      .getByRole("button", { name: new RegExp(`^${escape(dish)} ${price}`) })
      .click();
    const dialog = page.getByRole("dialog", { name: dish });
    await expect(dialog).toBeVisible();
    for (let i = 1; i < qty; i++) {
      await dialog.getByRole("button", { name: "Increase quantity" }).click();
    }
    await dialog.getByRole("button", { name: /^Add to cart/ }).click();
    await expect(dialog).toBeHidden();
  }
  await page.goto("/checkout");
  await createAccountAtCheckout(page, name);
  await page.getByRole("button", { name: /^Delivery/ }).click();
}

function escape(s: string) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

const summary = (page: Page) => page.getByRole("complementary");
const promoField = (page: Page) =>
  page.getByLabel("Promo code", { exact: true });
const applyButton = (page: Page) =>
  page.getByRole("button", { name: "Apply", exact: true });

async function applyCode(page: Page, code: string) {
  await promoField(page).fill(code);
  await applyButton(page).click();
}

/** A negative amount in the order summary, i.e. a discount line. */
const discountAmount = (page: Page, amount?: string) =>
  summary(page).getByText(
    amount ? new RegExp(`^[−-]\\s?${amount} AMD$`) : /^[−-]\s?[\d,]+ AMD$/,
  );

async function expectTotal(page: Page, amount: string) {
  await expect(summary(page)).toContainText(
    new RegExp(`Total\\s*${amount} AMD`),
  );
}

const CURRY_3000: Line = {
  dish: "Chicken curry rice & vegetables",
  price: "3,000 AMD",
};
const DRAGON_2X: Line = { dish: "Dragon Roll", price: "4,000 AMD", qty: 2 };

test("SCRUM-7-TC-01: Promo code field with Apply on checkout; Apply disabled while the field is empty", async ({
  page,
}) => {
  await startCheckout(page, [CURRY_3000], "Promo TC One");

  await expect(promoField(page)).toBeVisible();
  await expect(promoField(page)).toHaveValue("");
  await expect(applyButton(page)).toBeDisabled();

  await promoField(page).fill("SAVE10");
  await expect(applyButton(page)).toBeEnabled();
});

test("SCRUM-7-TC-02: SAVE10 at exactly the 3,000 AMD minimum takes 10% off the items subtotal; delivery added after", async ({
  page,
}) => {
  await startCheckout(page, [CURRY_3000], "Promo TC Two");

  await applyCode(page, "SAVE10");

  await expect(discountAmount(page, "300")).toBeVisible();
  await expectTotal(page, "3,200");
});

test("SCRUM-7-TC-03: SAVE10 with a 2,900 AMD subtotal (100 below the minimum) shows the missing amount", async ({
  page,
}) => {
  await startCheckout(
    page,
    [{ dish: "Yassai curry", price: "2,900 AMD" }],
    "Promo TC Three",
  );

  await applyCode(page, "SAVE10");

  await expect(
    page.getByText("Add 100 AMD more to use this code"),
  ).toBeVisible();
  await expect(discountAmount(page)).toHaveCount(0);
  await expectTotal(page, "3,400");
});

test("SCRUM-7-TC-04: TREAT15 at exactly the 8,000 AMD minimum takes 15% off", async ({
  page,
}) => {
  await startCheckout(page, [DRAGON_2X], "Promo TC Four");

  await applyCode(page, "TREAT15");

  await expect(discountAmount(page, "1,200")).toBeVisible();
  await expectTotal(page, "6,800");
});

test("SCRUM-7-TC-05: TREAT15 with a 6,950 AMD subtotal shows the missing amount with a thousands separator", async ({
  page,
}) => {
  await startCheckout(
    page,
    [
      { dish: "Chicken katsu curry with vegetables", price: "3,350 AMD" },
      { dish: "Pork curry rice & vegetables", price: "3,600 AMD" },
    ],
    "Promo TC Five",
  );

  await applyCode(page, "TREAT15");

  await expect(
    page.getByText("Add 1,050 AMD more to use this code"),
  ).toBeVisible();
  await expect(discountAmount(page)).toHaveCount(0);
});

test("SCRUM-7-TC-06: TREAT15 on 8,050 AMD rounds the 1,207.5 AMD discount to 1,208 AMD", async ({
  page,
}) => {
  await startCheckout(
    page,
    [
      { dish: "Chicken Katsu Curry", price: "3,150 AMD" },
      { dish: "Yassai curry", price: "2,900 AMD" },
      { dish: "Salmon Maki", price: "2,000 AMD" },
    ],
    "Promo TC Six",
  );

  await applyCode(page, "TREAT15");

  await expect(discountAmount(page, "1,208")).toBeVisible();
  await expectTotal(page, "6,842");
});

test("SCRUM-7-TC-07: Expired code OLD15 is rejected", async ({ page }) => {
  await startCheckout(page, [CURRY_3000], "Promo TC Seven");

  await applyCode(page, "OLD15");

  await expect(page.getByText("This code has expired")).toBeVisible();
  await expect(discountAmount(page)).toHaveCount(0);
  await expectTotal(page, "3,500");
});

test("SCRUM-7-TC-08: Unknown code NOPE99 is rejected", async ({ page }) => {
  await startCheckout(page, [CURRY_3000], "Promo TC Eight");

  await applyCode(page, "NOPE99");

  await expect(page.getByText("Code not found")).toBeVisible();
  await expect(discountAmount(page)).toHaveCount(0);
  await expectTotal(page, "3,500");
});

test('SCRUM-7-TC-09: Lower-case code with surrounding spaces (" save10 ") is accepted as SAVE10', async ({
  page,
}) => {
  await startCheckout(page, [CURRY_3000], "Promo TC Nine");

  await applyCode(page, " save10 ");

  await expect(discountAmount(page, "300")).toBeVisible();
  await expectTotal(page, "3,200");
  await expect(page.getByText("Code not found")).toHaveCount(0);
});

test("SCRUM-7-TC-10: Applying TREAT15 after SAVE10 replaces it", async ({
  page,
}) => {
  await startCheckout(page, [DRAGON_2X], "Promo TC Ten");

  await applyCode(page, "SAVE10");
  await expect(discountAmount(page)).toBeVisible();

  await applyCode(page, "TREAT15");

  await expect(discountAmount(page, "1,200")).toBeVisible();
  await expect(discountAmount(page)).toHaveCount(1);
  await expectTotal(page, "6,800");
});

test("SCRUM-7-TC-11: An expired second code (OLD15) does not replace an applied SAVE10", async ({
  page,
}) => {
  await startCheckout(page, [DRAGON_2X], "Promo TC Eleven");

  await applyCode(page, "SAVE10");
  await expect(discountAmount(page)).toBeVisible();

  await applyCode(page, "OLD15");

  await expect(page.getByText("This code has expired")).toBeVisible();
  await expect(discountAmount(page, "800")).toBeVisible();
  await expectTotal(page, "7,200");
});

test("SCRUM-7-TC-12: Removing an applied SAVE10 restores the original total", async ({
  page,
}) => {
  await startCheckout(page, [CURRY_3000], "Promo TC Twelve");

  await applyCode(page, "SAVE10");
  await expect(discountAmount(page)).toBeVisible();

  await page.getByRole("button", { name: "Remove promo code" }).click();

  await expect(discountAmount(page)).toHaveCount(0);
  await expectTotal(page, "3,500");
});

test("SCRUM-7-TC-13: Applied SAVE10 stays but loses its discount when the cart drops below 3,000 AMD", async ({
  page,
}) => {
  await startCheckout(
    page,
    [{ dish: "Oshinko Maki", price: "1,500 AMD", qty: 2 }],
    "Promo TC Thirteen",
  );

  await applyCode(page, "SAVE10");
  await expect(discountAmount(page)).toBeVisible();

  // Checkout has no quantity control; the cart panel on the chef page has one.
  await page.goto("/chef/24");
  await page
    .getByRole("complementary")
    .getByRole("button", { name: "Decrease quantity" })
    .click();
  await page.goto("/checkout");

  await expect(promoField(page)).toHaveValue("SAVE10");
  await expect(
    page.getByText("Add 1,500 AMD more to use this code"),
  ).toBeVisible();
  await expect(discountAmount(page)).toHaveCount(0);
  await expectTotal(page, "2,000");
});

test("SCRUM-7-TC-14: An order placed with SAVE10 is charged the discounted total", async ({
  page,
}) => {
  await startCheckout(page, [CURRY_3000], "Promo TC Fourteen");

  await page.getByLabel("City").fill("Yerevan");
  await page.getByLabel("Street").fill("Barekamutyan");
  await page.getByLabel("Building").fill("14");
  await page.getByLabel("Apartment").fill("37");
  await page
    .getByPlaceholder("Allergies, instructions, gate code...")
    .fill("STLC SCRUM-7 SCRUM-7-TC-14");

  await applyCode(page, "SAVE10");
  await expectTotal(page, "3,200");

  await page.getByRole("button", { name: "Place order" }).click();
  await expect(page).toHaveURL(/\/orders\/success/);
  const orderNumber = new URL(page.url()).searchParams.get("number");
  expect(orderNumber).toBeTruthy();
  await expect(page.getByText("3,200 AMD", { exact: true })).toBeVisible();

  await page.goto("/orders");
  await expect(page.getByText(orderNumber!, { exact: true })).toBeVisible();
  await expect(page.getByText("3,200 AMD", { exact: true })).toBeVisible();
  await expect(page.getByText("3,500 AMD", { exact: true })).toHaveCount(0);
});
