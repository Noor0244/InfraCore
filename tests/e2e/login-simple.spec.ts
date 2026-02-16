import { test, expect } from '@playwright/test';

/**
 * Simple login test with fixed selectors
 * This test is designed to work with the FastAPI login page
 */

test('Simple Login Test', async ({ page }) => {
  // Navigate to login page
  await page.goto('/login');
  
  // Verify login page loaded
  await expect(page).toHaveURL(/\/login/);
  console.log('✅ Login page loaded');

  // Get form elements using specific selectors
  console.log('📝 Looking for form elements...');
  
  // Find username input - use attribute selector
  const usernameInput = page.locator('input[name="username"]');
  console.log('Username input locator:', usernameInput);
  
  // Find password input - use type selector to avoid toggle button
  const passwordInput = page.locator('input[type="password"]');
  console.log('Password input locator:', passwordInput);
  
  // Find submit button
  const submitButton = page.locator('button[type="submit"]');
  console.log('Submit button locator:', submitButton);
  
  // Verify elements exist and are visible
  await expect(usernameInput).toBeVisible({ timeout: 5000 });
  console.log('✅ Username input visible');
  
  await expect(passwordInput).toBeVisible({ timeout: 5000 });
  console.log('✅ Password input visible');
  
  await expect(submitButton).toBeVisible({ timeout: 5000 });
  console.log('✅ Submit button visible');
  
  // Enter credentials
  console.log('📝 Entering credentials...');
  await usernameInput.fill('Sajjadd');
  console.log('✅ Username entered');
  
  await passwordInput.fill('Sajjad@#123');
  console.log('✅ Password entered');
  
  // Submit form
  console.log('📝 Submitting form...');
  await submitButton.click();
  console.log('✅ Form submitted');
  
  // Wait for navigation away from login
  console.log('📝 Waiting for navigation...');
  try {
    await page.waitForURL(
      (url) => !url.pathname.includes('/login'),
      { timeout: 10000 }
    );
    console.log('✅ Navigated away from login');
    console.log('📍 Current URL:', page.url());
  } catch (e) {
    console.log('❌ Still on login page or navigation timeout');
    console.log('📍 Current URL:', page.url());
    throw e;
  }
  
  // Verify login success - check for visible content
  const mainContent = page.locator('main, [role="main"], body');
  await expect(mainContent.first()).toBeVisible({ timeout: 5000 });
  console.log('✅ Main content visible');
  
  // Verify no errors
  const errorCount = await page.locator('text=/error|fail|invalid/i').count();
  expect(errorCount).toBe(0);
  console.log('✅ No error messages');
  
  console.log('🎉 Login test PASSED!');
});
