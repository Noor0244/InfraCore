import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for InfraCore Construction ERP System
 * 
 * This configuration:
 * - Points to local development server at http://127.0.0.1:8000
 * - Uses stable selectors (getByRole, getByLabel, getByText)
 * - Includes retry logic for flaky tests
 * - Captures screenshots and videos on failure
 * - Generates detailed HTML and JSON reports
 * - Supports multiple browsers and devices
 */

export default defineConfig({
  // Test directory
  testDir: './tests/e2e',

  // Parallel execution settings
  fullyParallel: false, // Run sequentially for shared state (database)
  
  // Fail on test.only in production
  forbidOnly: !!process.env.CI,
  
  // Retry settings
  retries: process.env.CI ? 2 : 1,
  
  // Single worker to maintain test order and state
  workers: 1,

  // Reporter configuration
  reporter: [
    ['html', { open: 'on-failure' }], // HTML report
    ['json', { outputFile: 'test-results.json' }],
    ['list'], // Console output
  ],

  /**
   * Shared test options
   * These options apply to all browsers and devices
   */
  use: {
    // Base URL for the application
    baseURL: 'http://127.0.0.1:8000',

    // Timeouts
    navigationTimeout: 30000,
    actionTimeout: 10000,

    // Capture diagnostics
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'on-first-retry',

    // Consistent environment
    locale: 'en-US',
    timezoneId: 'America/New_York',
  },


  // Browser configurations
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },

    // Uncomment for mobile testing
    // {
    //   name: 'Mobile Chrome',
    //   use: { ...devices['Pixel 5'] },
    // },
    // {
    //   name: 'Mobile Safari',
    //   use: { ...devices['iPhone 12'] },
    // },
  ],

  // Global timeout for entire test suite
  globalTimeout: 30 * 60 * 1000, // 30 minutes

  // Uncomment to auto-start the development server
  // webServer: {
  //   command: 'uvicorn app.main:app --host 127.0.0.1 --port 8000',
  //   url: 'http://127.0.0.1:8000',
  //   reuseExistingServer: true,
  // },
});
