import { test, expect } from '@playwright/test';

/**
 * Login Authentication Tests
 * Uses specific attribute selectors to avoid strict mode violations
 */

test.describe('Authentication', () => {
  const credentials = {
    username: 'Sajjadd',
    password: 'Sajjad@#123',
  };

  test('Login with valid credentials', async ({ page }) => {
    await page.goto('/login');
    await expect(page).toHaveURL(/\/login/);

    // Use specific selectors based on actual form structure
    await page.locator('input[name="username"]').fill(credentials.username);
    await page.locator('input[id="passwordField"]').fill(credentials.password);
    await page.locator('button[type="submit"]').click();

    // Wait for navigation away from login
    await page.waitForURL(
      (url) => !url.pathname.includes('/login'),
      { timeout: 15000 }
    );

    // Verify logged in
    expect(page.url()).not.toContain('/login');
    console.log('✅ Login successful');
  });

  test('Reject invalid credentials', async ({ page }) => {
    await page.goto('/login');
    
    await page.locator('input[name="username"]').fill('wronguser');
    await page.locator('input[id="passwordField"]').fill('wrongpass');
    await page.locator('button[type="submit"]').click();

    await page.waitForTimeout(3000);

    expect(page.url()).toContain('/login');
    console.log('✅ Invalid credentials rejected');
  });

  test('Login page elements visible', async ({ page }) => {
    await page.goto('/login');

    await expect(page.locator('form')).toBeVisible();
    await expect(page.locator('input[name="username"]')).toBeVisible();
    await expect(page.locator('input[id="passwordField"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();

    console.log('✅ All login elements present');
  });

  test('Session persists after reload', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.locator('input[name="username"]').fill(credentials.username);
    await page.locator('input[id="passwordField"]').fill(credentials.password);
    await page.locator('button[type="submit"]').click();

    await page.waitForURL(
      (url) => !url.pathname.includes('/login'),
      { timeout: 15000 }
    );

    // Reload
    await page.reload();
    await page.waitForLoadState('networkidle');

    expect(page.url()).not.toContain('/login');
    console.log('✅ Session persisted');
  });
});
