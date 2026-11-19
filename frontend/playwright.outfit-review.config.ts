import {defineConfig} from "@playwright/test";
export default defineConfig({
  testDir:"./tests",testMatch:"outfit-review-prototype.spec.ts",workers:1,timeout:60000,
  use:{baseURL:"http://localhost:3000",headless:true,launchOptions:{args:["--disable-gpu"]}},
  // Reuse the existing frontend; every API request is intercepted by the tests.
  // No additional backend/frontend or live recommendation requests are created.
  outputDir:process.env.SMART_WARDROBE_REVIEW_TEST_OUTPUT??"../.outfit-review-browser-results",
});
