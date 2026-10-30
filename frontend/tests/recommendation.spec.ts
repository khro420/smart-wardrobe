import { test, expect, type Page } from "@playwright/test";

const item = { garment_id:"dress",garment_role:"one_piece",item_order:1,name:"Blue dress",category:"vest_dress",preferred_media_id:null,currently_eligible:true,snapshot_available:true };
const recommendation = { id:"rec",chat_id:"chat",status:"available",created_at:"2026-01-01T00:00:00Z",items:[item],total_score:.7,compatibility_score:null,provenance:{scoring_profile:"compatibility_deferred"} };
async function mockApi(page: Page, options: { assistant?: boolean; homepage?: string } = {}) {
  const calls: { path: string; body: Record<string,string> | null; auth: string | undefined }[] = [];
  await page.addInitScript(() => sessionStorage.setItem("smart_wardrobe_access_token","owner.9999999999.synthetic"));
  await page.route("**/api/v1/**",async route => {
    const request = route.request(), url = new URL(request.url());
    const body = request.method() === "POST" ? request.postDataJSON() : null;
    calls.push({ path:url.pathname,body,auth:request.headers().authorization });
    const json = (value: unknown,status=200) => route.fulfill({ status,json:value });
    if (url.pathname.endsWith("/capabilities")) return json({homepage_enabled:true,assistant_enabled:options.assistant !== false});
    if (url.pathname.endsWith("/wardrobe/outfits")) return json([]);
    if (url.pathname.endsWith("/saved-outfit")) return json({saved:false,outfit_id:null});
    if (url.pathname.endsWith("/recommendations/homepage")) return options.homepage ? json({status:options.homepage,complete:false},503) : json({status:"Selected",complete:true,replayed:false,recommendation:{...recommendation,chat_id:null}},201);
    if (url.pathname.endsWith("/recommendations") && body) { await new Promise(resolve => setTimeout(resolve,100)); return json({status:"available",outcome:"Selected",complete:true,replayed:false,recommendation:{...recommendation,request_text:body.request_text}},201); }
    if (url.pathname.endsWith("/chats")) {
      const term = url.searchParams.get("search") ?? "", cursor = url.searchParams.get("cursor");
      if (term === "slow") await new Promise(resolve => setTimeout(resolve,350));
      const other = request.headers().authorization?.startsWith("Bearer other.");
      return json({status:"CompletedChats",items:other ? [] : [{chat_id:cursor ? "second" : "chat",request_text:term || (cursor ? "Second request" : "Original request"),created_at:"2026-01-01T00:00:00Z",completed_at:"now",recommendation_id:"rec",recommendation_status:"available",read_only:true}],total:other ? 0 : 2,limit:50,next_cursor:cursor ? null : "next"});
    }
    if (url.pathname.includes("/chats/")) return json({chat_id:"chat",request_text:"Original request",structured_request:{style:"vintage"},read_only:true,recommendation:{...recommendation,items:[{...item,currently_eligible:false,preferred_media_id:null}]}});
    return json({detail:"Unavailable"},404);
  });
  return calls;
}

test("Homepage flow survives reload, gets a new key on intentional navigation, has no refresh", async ({page}) => {
  const calls = await mockApi(page);
  await page.goto("/");
  await expect(page.getByTestId("recommendation-result")).toHaveCount(1);
  await expect(page.getByRole("button",{name:/refresh recommendation/i})).toHaveCount(0);
  const first = calls.find(c => c.path.endsWith("/homepage"))!.body!.submission_key;
  await page.reload();
  await expect(page.getByTestId("recommendation-result")).toHaveCount(1);
  expect(calls.filter(c => c.path.endsWith("/homepage")).every(c => c.body!.submission_key === first)).toBe(true);
  await page.getByRole("link",{name:"Outfit Assistant",exact:true}).first().click();
  await page.waitForURL("**/assistant");
  await expect(page.getByRole("heading",{name:"Outfit Assistant",exact:true})).toBeVisible();
  await page.getByRole("link",{name:"Home",exact:true}).first().click();
  await page.waitForURL("http://127.0.0.1:3100/");
  await expect(page.getByTestId("recommendation-result")).toBeVisible();
  await expect.poll(() => calls.filter(c => c.path.endsWith("/homepage")).at(-1)!.body!.submission_key).not.toBe(first);
  expect(calls.filter(c => c.path.endsWith("/recommendations"))).toHaveLength(0);
});

test("Assistant single submission, completion, remount restoration and New Chat",async({page}) => {
  const calls = await mockApi(page);
  await page.goto("/assistant");
  await page.getByLabel("What would you like to wear?").fill("Suggest an outfit with vintage style");
  await page.getByRole("button",{name:"Suggest an outfit",exact:true}).dblclick();
  await expect(page.getByTestId("recommendation-result")).toBeVisible();
  await expect(page.getByRole("textbox")).toHaveCount(0);
  await expect(page.getByText("Compatibility was not measured.",{exact:false})).toBeVisible();
  const posts = calls.filter(c => c.path.endsWith("/recommendations") && c.body);
  expect(posts).toHaveLength(1); expect(posts[0].auth).toContain("Bearer owner.");
  await page.reload();
  await expect(page.getByText("Saved recommendation · read-only")).toBeVisible();
  expect(calls.filter(c => c.path.endsWith("/recommendations") && c.body)).toHaveLength(1);
  await page.getByRole("button",{name:"New Chat",exact:true}).click();
  await page.getByLabel("What would you like to wear?").fill("Suggest an outfit");
  await page.getByRole("button",{name:"Suggest an outfit",exact:true}).click();
  await expect(page.getByTestId("recommendation-result")).toBeVisible();
  expect(calls.filter(c => c.path.endsWith("/recommendations") && c.body).at(-1)!.body!.submission_key).not.toBe(posts[0].body!.submission_key);
});

test("Disabled Assistant never posts to legacy pipeline",async({page}) => {
  const calls = await mockApi(page,{assistant:false});
  await page.goto("/assistant");
  await page.getByLabel("What would you like to wear?").fill("Suggest an outfit");
  await page.getByRole("button",{name:"Suggest an outfit",exact:true}).click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText("disabled");
  expect(calls.filter(c => c.path.endsWith("/recommendations") && c.body)).toHaveLength(0);
});

test("Assistant transport retry preserves key and text across a remount",async({page}) => {
  await mockApi(page);
  const submissions: Record<string,string>[] = [];
  await page.route("**/api/v1/recommendations?pipeline=integrated",async route => {
    submissions.push(route.request().postDataJSON());
    if (submissions.length === 1) return route.abort("failed");
    return route.fulfill({status:201,json:{status:"available",outcome:"Selected",complete:true,recommendation}});
  });
  await page.goto("/assistant");
  await page.getByLabel("What would you like to wear?").fill("Suggest an outfit");
  await page.getByRole("button",{name:"Suggest an outfit",exact:true}).click();
  await expect(page.getByRole("button",{name:"Retry same request"})).toBeVisible();
  await page.reload();
  await expect(page.getByTestId("recommendation-result")).toBeVisible();
  expect(submissions).toHaveLength(2);
  expect(submissions[1]).toEqual(submissions[0]);
});

for (const outcome of ["NoMatchingCandidates","InsufficientEvidence","PolicyUnavailable","UnsupportedRequest","WardrobeChanged","PersistenceFailure"]) {
  test(`Assistant preserves controlled ${outcome} without a substitute`,async({page}) => {
    await mockApi(page);
    await page.route("**/api/v1/recommendations?pipeline=integrated",route => route.fulfill({status:outcome === "PersistenceFailure" ? 503 : 422,json:{status:outcome,outcome,complete:false}}));
    await page.goto("/assistant");
    await page.getByLabel("What would you like to wear?").fill("Suggest an outfit");
    await page.getByRole("button",{name:"Suggest an outfit",exact:true}).click();
    await expect(page.getByRole("main").getByRole("alert")).toBeVisible();
    await expect(page.getByRole("textbox")).toHaveCount(0);
    await expect(page.getByTestId("recommendation-result")).toHaveCount(0);
  });
}

test("Homepage structured failure shows no saved substitute",async({page}) => {
  await mockApi(page,{homepage:"ProcessingFailure"}); await page.goto("/");
  await expect(page.getByRole("main").getByRole("alert")).toContainText("No partial outfit");
  await expect(page.getByTestId("recommendation-result")).toHaveCount(0);
});

test("Outerwear stays visible in recorded order and can be visualised",async({page}) => {
  await mockApi(page);
  await page.route("**/api/v1/recommendations/homepage",route => route.fulfill({status:201,json:{status:"Selected",complete:true,recommendation:{...recommendation,items:[{...item,garment_id:"coat",garment_role:"outerwear",name:"Recorded coat",item_order:2},{...item,item_order:1}]}}}));
  await page.goto("/");
  const result = page.getByTestId("recommendation-result");
  await expect(result.getByText("Blue dress",{exact:true})).toBeVisible();
  await expect(result.getByText("Recorded coat",{exact:true})).toBeVisible();
  expect(await result.locator("p.font-semibold").allTextContents()).toEqual(["Blue dress","Recorded coat"]);
  await expect(result.getByRole("link",{name:"Visualise outfit"})).toHaveAttribute("href", "/try-on?recommendation=rec");
});

test("Fresh Homepage save reuses the existing API and refreshes only saved outfits",async({page}) => {
  const calls = await mockApi(page);
  let saves = 0;
  await page.route("**/api/v1/recommendations/rec/save-as-outfit",async route => {
    saves++;
    expect(route.request().postDataJSON()).toEqual({name:"Recommended outfit"});
    return route.fulfill({status:201,json:{id:"saved",name:"Recommended outfit",garment_ids:["dress"]}});
  });
  await page.goto("/");
  await expect(page.getByRole("link",{name:"Visualise outfit",exact:true})).toHaveAttribute("href","/try-on?recommendation=rec");
  await page.getByRole("button",{name:"Save as outfit",exact:true}).click();
  await expect(page.getByRole("button",{name:"Saved as outfit",exact:true})).toBeDisabled();
  expect(saves).toBe(1);
  await expect.poll(() => calls.filter(c => c.path.endsWith("/wardrobe/outfits")).length).toBeGreaterThan(1);
  expect(calls.filter(c => c.path.endsWith("/homepage"))).toHaveLength(1);
});

test("Historical Homepage replay does not claim current eligibility or enable actions",async({page}) => {
  await mockApi(page);
  await page.route("**/api/v1/recommendations/homepage",route => route.fulfill({status:200,json:{status:"Selected",complete:true,replayed:true,recommendation:{...recommendation,items:[{...item,currently_eligible:false}]}}}));
  await page.goto("/");
  await expect(page.getByText("Saved recommendation · read-only")).toBeVisible();
  await expect(page.getByText("Unavailable for current use")).toBeVisible();
  await expect(page.getByRole("button",{name:"Save as outfit",exact:true})).toHaveCount(0);
  await expect(page.getByRole("link",{name:"Visualise outfit",exact:true})).toHaveCount(0);
});

test("Sign-out clears owner-scoped drafts and history reports authentication expiry",async({page}) => {
  await mockApi(page);
  await page.goto("/assistant");
  await page.getByLabel("What would you like to wear?").fill("Private first-owner draft");
  await page.getByRole("button",{name:"Sign out",exact:true}).click();
  await page.waitForURL("**/auth");
  expect(await page.evaluate(() => Object.keys(sessionStorage).filter(key => key.startsWith("smart_wardrobe_interaction:")))).toEqual([]);
  await page.route("**/api/v1/chats?**",route => route.fulfill({status:401,json:{detail:"Authenticate with a valid bearer token."}}));
  await page.goto("/history");
  await expect(page.getByRole("main").getByRole("alert")).toContainText("session has expired");
});

test("History pagination, stale search responses and read-only archival restoration",async({page}) => {
  const calls = await mockApi(page);
  await page.goto("/history");
  await page.getByRole("button",{name:"Load more chats"}).click();
  await expect(page.getByRole("link",{name:"Open completed interaction"})).toHaveCount(2);
  await page.getByLabel("Search original requests").fill("slow"); await page.getByRole("button",{name:"Search history"}).click();
  await page.getByLabel("Search original requests").fill("new"); await page.getByRole("button",{name:"Search history"}).click();
  await expect(page.getByRole("heading",{name:"new",exact:true})).toBeVisible();
  await page.waitForTimeout(450);
  await expect(page.getByRole("heading",{name:"slow",exact:true})).toHaveCount(0);
  const queries = calls.filter(c => c.path.endsWith("/chats")); expect(queries.length).toBeGreaterThan(1);
  await page.getByRole("link",{name:"Open completed interaction"}).click();
  await expect(page.getByText("Unavailable for current use")).toBeVisible();
  await expect(page.getByText("Historical image unavailable")).toBeVisible();
  await expect(page.getByRole("textbox")).toHaveCount(0);
  expect(calls.filter(c => c.path.endsWith("/recommendations") && c.body)).toHaveLength(0);
});

test("Real backend login, Homepage, Assistant, history and garment archival",async({page,request}) => {
  const auth = await request.post("http://127.0.0.1:3101/api/v1/account/login",{data:{email:"browser-owner@example.test",password:"Browser-test-password-123"}});
  expect(auth.ok()).toBeTruthy();
  const {access_token:token} = await auth.json();
  await page.addInitScript(value => sessionStorage.setItem("smart_wardrobe_access_token",value),token);
  await page.goto("/"); await expect(page.getByTestId("recommendation-result")).toBeVisible();
  await page.goto("/assistant");
  await page.getByLabel("What would you like to wear?").fill("Suggest an outfit with vintage style");
  await page.getByRole("button",{name:"Suggest an outfit",exact:true}).click();
  await expect(page.getByTestId("recommendation-result")).toBeVisible();
  await expect(page.getByRole("textbox")).toHaveCount(0);
  const chats = await request.get("http://127.0.0.1:3101/api/v1/chats",{headers:{Authorization:`Bearer ${token}`}});
  const history = await chats.json(); expect(history.total).toBe(1);
  // Profiles can legitimately choose different structures. Archive a selected
  // constituent rather than assuming the seed dress must win every policy.
  const completed = await (await request.get(`http://127.0.0.1:3101/api/v1/chats/${history.items[0].chat_id}`,{headers:{Authorization:`Bearer ${token}`}})).json();
  const archived = await request.delete(`http://127.0.0.1:3101/api/v1/wardrobe/garments/${completed.recommendation.items[0].garment_id}`,{headers:{Authorization:`Bearer ${token}`}});
  expect(archived.status()).toBe(204);
  await page.goto(`/history/${history.items[0].chat_id}`);
  await expect(page.getByText("Unavailable for current use")).toBeVisible();
  await expect(page.getByRole("button",{name:"Save as outfit"})).toHaveCount(0);
  const otherAuth = await request.post("http://127.0.0.1:3101/api/v1/account/login",{data:{email:"browser-other@example.test",password:"Browser-test-password-123"}});
  const other = (await otherAuth.json()).access_token;
  expect((await request.get(`http://127.0.0.1:3101/api/v1/chats/${history.items[0].chat_id}`,{headers:{Authorization:`Bearer ${other}`}})).status()).toBe(404);
});
