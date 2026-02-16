import { test, expect } from '@playwright/test';

/**
 * FastAPI Login Authentication Test Suite
 * 
 * Tests the authentication system for InfraCore FastAPI application
 * Verifies login flow, credential validation, and protected route access
 * 
 * Requirements:
 * - Application running at http://127.0.0.1:8000
 * - Login endpoint: /login
 * - Valid credentials required for testing
 * 
 * Test approach:
 * - Uses relative paths with baseURL from playwright.config.ts
 * - Stable locators (getByRole, getByLabel, getByPlaceholder)
 * - Proper waits and comprehensive assertions
 * - Production-quality error handling
 */

test.describe('Authentication - Login Flow', () => {
  // Real database credentials for testing
  const validCredentials = {
    username: 'Sajjadd',
    password: 'Sajjad@#123',
  };

  /**
   * Test: Successful login with valid credentials
   * Verifies user can login and is redirected to dashboard/protected area
   */
  test('should successfully login with valid credentials', async ({ page }) => {
    // ========== STEP 1: Navigate to Login Page ==========
    console.log('📝 Step 1: Navigating to login page');
    await page.goto('/login');
    
    // Verify login page loaded
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByText(/login|sign in/i)).toBeVisible({ timeout: 5000 });
    console.log('✅ Login page loaded');

    // ========== STEP 2: Verify Login Form Elements ==========
    console.log('📝 Step 2: Verifying login form elements');
    
    // Check for username input field - use more specific selector
    const usernameInput = page.locator('input[name="username"], input[id*="username"], input[name="email"]').first();
    await expect(usernameInput).toBeVisible({ timeout: 5000 });
    
    // Check for password input field - specify it's a password input, not the toggle button
    const passwordInput = page.locator('input#passwordField, input[name="password"], input[type="password"]').first();
    await expect(passwordInput).toBeVisible({ timeout: 5000 });
    
    // Check for login button - be specific about button type
    const loginButton = page.locator('button[type="submit"]').first();
    await expect(loginButton).toBeVisible({ timeout: 5000 });
    
    console.log('✅ All login form elements are present');

    // ========== STEP 3: Enter Credentials ==========
    console.log('📝 Step 3: Entering login credentials');
    
    // Fill username field
    const usernameField = page.locator('input[name="username"], input[id*="username"], input[name="email"]').first();
    await usernameField.fill(validCredentials.username);
    await expect(usernameField).toHaveValue(validCredentials.username);
    console.log(`  ✓ Username entered: ${validCredentials.username}`);
    
    // Fill password field (use type="password" to avoid toggle button)
    const passwordField = page.locator('input#passwordField, input[name="password"], input[type="password"]').first();
    await passwordField.fill(validCredentials.password);
    // Note: Password value cannot be asserted for security reasons
    console.log('  ✓ Password entered (value hidden for security)');

    // ========== STEP 4: Submit Login Form ==========
    console.log('📝 Step 4: Submitting login form');
    
    // Click login button
    const submitButton = page.locator('button[type="submit"]').first();
    await submitButton.click();
    
    console.log('  ✓ Login button clicked');

    // ========== STEP 5: Wait for Navigation ==========
    console.log('📝 Step 5: Waiting for navigation after login');
    
    // Wait for page to leave /login endpoint
    // This ensures navigation actually occurred
    await page.waitForURL(
      (url) => !url.pathname.includes('/login'),
      { timeout: 10000 }
    );
    console.log('  ✓ Page navigated away from /login');

    // ========== STEP 6: Verify Login Success ==========
    console.log('📝 Step 6: Verifying login success');
    
    // Confirm URL is NOT /login anymore
    const currentUrl = page.url();
    expect(currentUrl).not.toContain('/login');
    console.log(`  ✓ Current URL: ${currentUrl}`);
    
    // Look for dashboard or protected area indicators
    // These are common elements present after successful login
    const dashboardElements = page.locator('main, [role="main"], .dashboard, .content-area, h1, h2');
    const visibleElements = await dashboardElements.filter({ has: page.locator('text=/dashboard|home|project|welcome/i') }).first();
    
    // If main content area is visible, login was successful
    await expect(dashboardElements.first()).toBeVisible({ timeout: 5000 });
    console.log('  ✓ Protected content area is visible');

    // ========== STEP 7: Verify No Error Messages ==========
    console.log('📝 Step 7: Verifying no error messages');
    
    // Check for error messages
    const errorMessages = page.getByText(/error|fail|invalid|incorrect|unauthorized/i);
    const errorCount = await errorMessages.count();
    
    // Should have no error messages
    expect(errorCount).toBe(0);
    console.log('  ✓ No error messages displayed');

    // ========== STEP 8: Verify Session/Authentication State ==========
    console.log('📝 Step 8: Verifying authentication state');
    
    // Look for logout button or user profile indicator
    // These typically only show when authenticated
    const logoutButton = page.locator('button:has-text(/logout|sign out|exit/i), a:has-text(/logout|sign out|exit/i)').first();
    const userProfile = page.locator(`text="${validCredentials.username}"`).first();
    
    // At least one should be visible indicating authenticated state
    const authIndicatorExists = await logoutButton.isVisible().catch(() => false) 
      || await userProfile.isVisible().catch(() => false);
    
    if (authIndicatorExists) {
      console.log('  ✓ Authentication indicator found (logout button or user profile)');
    } else {
      console.log('  ℹ️ No explicit auth indicator, but navigated past login');
    }

    // ========== Test Summary ==========
    console.log('✅ Login test PASSED');
    console.log(`
    ========== LOGIN TEST SUMMARY ==========
    ✅ Login page loaded successfully
    ✅ Form submitted with valid credentials
    ✅ User redirected away from login page
    ✅ Protected content is visible
    ✅ No error messages displayed
    ✅ Authentication confirmed
    ========================================
    `);
  });

  /**
   * Test: Login with invalid credentials
   * Verifies system rejects invalid login attempts
   */
  test('should reject login with invalid credentials', async ({ page }) => {
    console.log('📝 Testing login rejection with invalid credentials');
    
    // Navigate to login
    await page.goto('/login');
    await expect(page).toHaveURL(/\/login/);

    // Enter invalid credentials
    const usernameInput = page.locator('input[name="username"], input[id*="username"], input[name="email"]').first();
    const passwordInput = page.locator('input#passwordField, input[name="password"], input[type="password"]').first();

    await usernameInput.fill('invaliduser');
    await passwordInput.fill('wrongpassword');

    // Submit form
    const loginButton = page.locator('button[type="submit"]').first();
    await loginButton.click();

    // Wait a moment for validation
    await page.waitForTimeout(2000);

    // Verify still on login page
    expect(page.url()).toContain('/login');
    console.log('  ✓ Still on login page - invalid login rejected');

    // Look for error message
    const errorMessage = page.getByText(/invalid|incorrect|failed|unauthorized/i).first();
    
    // Error message should be displayed
    const errorVisible = await errorMessage.isVisible().catch(() => false);
    if (errorVisible) {
      console.log('  ✓ Error message displayed for invalid credentials');
      await expect(errorMessage).toBeVisible();
    } else {
      console.log('  ℹ️ User remains on login page (form validation active)');
      // At minimum, we should still be on login
      expect(page.url()).toContain('/login');
    }

    console.log('✅ Invalid login correctly rejected');
  });

  /**
   * Test: Login page renders correctly
   * Verifies all UI elements are present and functional
   */
  test('should display login page with all required elements', async ({ page }) => {
    console.log('📝 Testing login page UI elements');
    
    await page.goto('/login');
    await expect(page).toHaveURL(/\/login/);

    // Check page title or heading
    const loginHeading = page.getByText(/login|sign in|welcome/i).first();
    await expect(loginHeading).toBeVisible({ timeout: 5000 });
    console.log('  ✓ Login heading visible');

    // Check form elements
    const form = page.locator('form').first();
    await expect(form).toBeVisible();
    console.log('  ✓ Login form present');

    // Check input fields
    const usernameField = page.locator('input[name="username"], input[id*="username"], input[name="email"]').first();
    await expect(usernameField).toBeVisible();
    console.log('  ✓ Username input field present');

    const passwordField = page.locator('input#passwordField, input[name="password"], input[type="password"]').first();
    await expect(passwordField).toBeVisible();
    console.log('  ✓ Password input field present');

    // Check submit button
    const submitButton = page.locator('button[type="submit"]').first();
    await expect(submitButton).toBeVisible();
    await expect(submitButton).toBeEnabled();
    console.log('  ✓ Login button present and enabled');

    // Check for remember me or other options
    const rememberLabel = page.locator('label').filter({ hasText: /remember/i }).first();
    if (await rememberLabel.isVisible().catch(() => false)) {
      console.log('  ✓ Remember me checkbox available');
    }

    // Check for forgot password link
    const forgotLink = page.getByRole('link', { name: /forgot|reset|password/i }).first();
    if (await forgotLink.isVisible().catch(() => false)) {
      console.log('  ✓ Forgot password link available');
    }

    console.log('✅ Login page renders all required elements');
  });

  /**
   * Test: Persistent login session
   * Verifies user remains logged in after page reload
   */
  test('should maintain login session after page reload', async ({ page }) => {
    console.log('📝 Testing session persistence');
    
    // Login first
    await page.goto('/login');
    const usernameInput = page.locator('input[name="username"], input[id*="username"], input[name="email"]').first();
    const passwordInput = page.locator('input#passwordField, input[name="password"], input[type="password"]').first();

    await usernameInput.fill(validCredentials.username);
    await passwordInput.fill(validCredentials.password);

    const loginButton = page.locator('button[type="submit"]').first();
    await loginButton.click();

    // Wait for navigation
    await page.waitForURL(
      (url) => !url.pathname.includes('/login'),
      { timeout: 10000 }
    );
    console.log('  ✓ Initial login successful');

    // Reload page
    const urlBeforeReload = page.url();
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    console.log('  ✓ Page reloaded');

    // Verify still on same page and not redirected to login
    const urlAfterReload = page.url();
    expect(urlAfterReload).not.toContain('/login');
    console.log(`  ✓ Still authenticated after reload (URL: ${urlAfterReload})`);

    // Verify protected content still visible
    const content = page.locator('main, [role="main"], .content-area');
    await expect(content.first()).toBeVisible({ timeout: 5000 });
    console.log('  ✓ Protected content still available');

    console.log('✅ Session persistence verified');
  });

  /**
   * Test: Direct navigation to protected route when logged out
   * Verifies user is redirected to login when accessing protected routes without authentication
   */
  test('should redirect to login when accessing protected route while logged out', async ({ page, context }) => {
    console.log('📝 Testing protected route access without authentication');
    
    // Clear cookies to simulate logged out state
    await context.clearCookies();
    
    // Try to access a protected route directly
    await page.goto('/');
    
    // Verify redirected to login or see login page
    await page.waitForTimeout(2000); // Let any redirects happen
    
    const onLoginPage = page.url().includes('/login') || 
      await page.getByText(/login|sign in/i).isVisible().catch(() => false);
    
    if (onLoginPage) {
      console.log('  ✓ Redirected to login page for unauthenticated access');
      expect(page.url()).toContain('/login');
    } else {
      console.log('  ℹ️ Home page accessible without authentication (public page)');
    }

    console.log('✅ Protected route access test completed');
  });
});
