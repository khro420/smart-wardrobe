import { test, expect, type Page } from "@playwright/test";

// All data/state reviews in these tests are synthetic API fixtures.
type Options = { eligible?: boolean; outerwear?: boolean; saved?: boolean; stateFailures?: number; saveFailures?: number; conflict?: boolean; prepareFailure?: boolean; phase?: string };
async function fixtures(page: Page, options: Options = {}) {
  const calls: { path: string; method: string; body: Record<string,string> | null }[] = [];
  let saved = options.saved ?? false, stateFailures = options.stateFailures ?? 0, saveFailures = options.saveFailures ?? 0;
  let phase = options.phase ?? "queued";
  await page.addInitScript(() => sessionStorage.setItem("smart_wardrobe_access_token","owner.9999999999.synthetic"));
  await page.route("**/api/v1/**", async route => {
    const request = route.request(), url = new URL(request.url());
    const body = request.method() === "POST" ? request.postDataJSON() : null;
    calls.push({path:url.pathname,method:request.method(),body});
    const json = (value: unknown,status=200) => route.fulfill({status,json:value});
    if (url.pathname.endsWith("/saved-outfit")) {
      if (stateFailures-- > 0) return json({detail:"Temporary status failure"},503);
      return json({saved,outfit_id:saved ? "independent-outfit" : null});
    }
    if (url.pathname.endsWith("/save-as-outfit")) {
      if (options.conflict) return json({detail:"This legacy recommendation was already saved. Open the existing Outfits collection."},409);
      if (saveFailures-- > 0) return json({detail:"Garment is no longer confirmed and available."},409);
      saved = true;
      return json({id:"independent-outfit",name:"Recommended outfit",garment_ids:["original-garment"]},201);
    }
    if (url.pathname.includes("/chats/")) {
      const chatId = url.pathname.split("/").at(-1)!;
      return json({chat_id:chatId,request_text:`Original request ${chatId}`,read_only:true,structured_request:{style:"vintage"},recommendation:{
        id:`recommendation-${chatId}`,chat_id:chatId,status:options.conflict ? "saved" : "available",total_score:.7,
        score_metadata:{weights:[.7,0,.3]},provenance:{scoring_profile:"compatibility_deferred"},
        items:[{garment_id:"original-garment",garment_role:options.outerwear ? "outerwear" : "one_piece",item_order:1,
          name:"Original garment",category:options.outerwear ? "long_sleeve_outwear" : "vest_dress",preferred_media_id:null,
          currently_eligible:options.eligible !== false,snapshot_available:true}],
      }});
    }
    if (url.pathname.endsWith("/visualisations/person-images")) return json([{id:"person",media_id:"personal-media",display_name:"Private base image"}]);
    if (url.pathname.endsWith("/visualisations/prepare")) {
      if (options.prepareFailure) return json({detail:"Source is no longer confirmed and available."},409);
      return json({source_type:"recommendation",source_id:body!.recommendation_id,category:"overall",categories:["overall"],capture_guidance:"Synthetic preparation",items:[{garment_id:"original-garment",source_media_id:"garment-media",name:"Original garment",category:"vest_dress",role:"one_piece",item_order:1}]});
    }
    if (url.pathname.endsWith("/visualisations") && body) return json({id:"visual",status:"queued"},202);
    if (url.pathname.endsWith("/visualisations/visual/cancel")) { phase = "cancelled"; return route.fulfill({status:204}); }
    if (url.pathname.endsWith("/visualisations/visual")) return json({id:"visual",status:phase,source_type:"recommendation",recommendation_id:"recommendation-first",person_image_id:"person",
      output_media_id:phase === "completed" ? "output" : null,progress_percent:phase === "completed" ? 100 : 10,progress_current:0,progress_total:1,
      error_message:phase === "failed" ? "Synthetic inference failure" : null,is_development_fallback:true,notice:"Synthetic fixture only",items:[{garment_id:"original-garment"}],configuration:{},metrics:{}});
    if (url.pathname.includes("/media/")) return route.fulfill({contentType:"image/png",body:Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aZ1kAAAAASUVORK5CYII=","base64")});
    if (url.pathname.endsWith("/wardrobe/outfits")) return json([]);
    if (url.pathname.endsWith("/capabilities")) return json({homepage_enabled:true,assistant_enabled:true});
    return json({detail:"Unavailable synthetic resource"},404);
  });
  return calls;
}

test("historical save uses original recommendation, prevents duplicates and restores saved state",async({page})=>{
  const calls = await fixtures(page);
  await page.goto("/history/first");
  await expect(page.getByText("Original request first",{exact:true})).toBeVisible();
  const button = page.getByRole("button",{name:"Save as outfit",exact:true});
  await expect(button).toBeEnabled();
  await button.dblclick();
  await expect(page.getByRole("button",{name:"Saved as outfit",exact:true})).toBeDisabled();
  await expect(page.getByText("Saved as an independent outfit.",{exact:false})).toBeVisible();
  expect(calls.filter(x=>x.path.endsWith("/save-as-outfit"))).toHaveLength(1);
  expect(calls.find(x=>x.path.endsWith("/save-as-outfit"))!.path).toBe("/api/v1/recommendations/recommendation-first/save-as-outfit");
  await page.reload();
  await expect(page.getByRole("button",{name:"Saved as outfit",exact:true})).toBeDisabled();
  await expect(page.getByText("Original request first",{exact:true})).toBeVisible();
  await expect(page.getByRole("textbox")).toHaveCount(0);
  expect(calls.filter(x=>x.method==="POST" && (x.path.endsWith("/recommendations") || x.path.includes("/chats")))).toHaveLength(0);
});

test("saved-status and save failures are honest and retryable without changing history",async({page})=>{
  const calls=await fixtures(page,{stateFailures:99,saveFailures:1});
  await page.goto("/history/first");
  await expect(page.getByRole("main").getByRole("alert")).toContainText("Temporary status failure");
  await expect(page.getByRole("button",{name:"Save as outfit",exact:true})).toBeDisabled();
  await page.route("**/saved-outfit",route=>route.fulfill({json:{saved:false,outfit_id:null}}));
  await page.getByRole("button",{name:"Retry saved status"}).click();
  await expect(page.getByRole("button",{name:"Save as outfit",exact:true})).toBeEnabled();
  await page.getByRole("button",{name:"Save as outfit",exact:true}).click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText("no longer confirmed");
  await expect(page.getByRole("button",{name:"Saved as outfit",exact:true})).toHaveCount(0);
  await expect(page.getByText("Original request first",{exact:true})).toBeVisible();
  await page.getByRole("button",{name:"Save as outfit",exact:true}).click();
  await expect(page.getByRole("button",{name:"Saved as outfit",exact:true})).toBeDisabled();
  expect(calls.filter(x=>x.path.endsWith("/save-as-outfit"))).toHaveLength(2);
});

test("legacy conflict is shown without inventing a saved outfit",async({page})=>{
  await fixtures(page,{conflict:true});
  await page.goto("/history/first");
  const button=page.getByRole("button",{name:"Save as outfit",exact:true});
  await expect(button).toBeEnabled(); await button.click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText("legacy recommendation");
  await expect(page.getByRole("button",{name:"Saved as outfit",exact:true})).toHaveCount(0);
  await expect(page.getByText("Original request first",{exact:true})).toBeVisible();
});

test("known unavailable snapshot retains cards and original text without usable actions",async({page})=>{
  const calls=await fixtures(page,{eligible:false});
  await page.goto("/history/first");
  await expect(page.getByText("Unavailable for current use")).toBeVisible();
  await expect(page.getByText("Original garment",{exact:true})).toBeVisible();
  await expect(page.getByRole("button",{name:"Save as outfit",exact:true})).toHaveCount(0);
  await expect(page.getByRole("link",{name:"Visualise outfit",exact:true})).toHaveCount(0);
  expect(calls.filter(x=>x.method==="POST")).toHaveLength(0);
});

test("outerwear remains visible and cannot be partially visualised",async({page})=>{
  const calls=await fixtures(page,{outerwear:true});
  await page.goto("/history/first");
  await expect(page.getByText("Visualisation is unavailable for outfits containing outerwear.",{exact:false})).toBeVisible();
  await expect(page.getByRole("link",{name:"Visualise outfit",exact:true})).toHaveCount(0);
  await expect(page.getByRole("button",{name:"Save as outfit",exact:true})).toBeEnabled();
  expect(calls.filter(x=>x.path.includes("/visualisations"))).toHaveLength(0);
});

test("historical visualisation follows existing source preparation and stale rejection creates no job",async({page})=>{
  const calls=await fixtures(page,{prepareFailure:true});
  await page.goto("/history/first");
  await page.getByRole("link",{name:"Visualise outfit",exact:true}).click();
  await expect(page).toHaveURL(/try-on\?recommendation=recommendation-first/);
  await expect(page.getByRole("main").getByRole("alert")).toContainText("no longer confirmed");
  await expect(page.getByRole("button",{name:"Create visualisation",exact:true})).toBeDisabled();
  expect(calls.find(x=>x.path.endsWith("/visualisations/prepare"))!.body).toEqual({recommendation_id:"recommendation-first"});
  expect(calls.filter(x=>x.path.endsWith("/visualisations"))).toHaveLength(0);
});

for (const phase of ["queued","processing","failed","cancelled","completed"]) {
  test(`historical visualisation reuses existing ${phase} handling`,async({page})=>{
    const calls=await fixtures(page,{phase});
    await page.goto("/history/first");
    await page.getByRole("link",{name:"Visualise outfit",exact:true}).click();
    const create=page.getByRole("button",{name:"Create visualisation",exact:true});
    await expect(create).toBeEnabled(); await create.dblclick();
    await expect(page).toHaveURL(/try-on\/result\?id=visual/);
    if (phase === "queued" || phase === "processing") {
      await expect(page.getByRole("button",{name:"Cancel request",exact:true})).toBeVisible();
      await page.getByRole("button",{name:"Cancel request",exact:true}).click();
      await expect(page.getByText("This request was cancelled.")).toBeVisible();
    } else if (phase === "failed") {
      await expect(page.getByRole("main").getByRole("alert")).toContainText("Synthetic inference failure");
      await expect(page.getByRole("button",{name:"Retry same inputs",exact:true})).toBeEnabled();
    } else if (phase === "cancelled") await expect(page.getByText("This request was cancelled.")).toBeVisible();
    else await expect(page.getByRole("button",{name:"Download output",exact:true})).toBeEnabled();
    const creations=calls.filter(x=>x.method==="POST" && x.path.endsWith("/visualisations"));
    expect(creations).toHaveLength(1);
    expect(creations[0].body).toEqual({recommendation_id:"recommendation-first",person_image_id:"person"});
  });
}

test("authentication expiry preserves historical text and disables saving",async({page})=>{
  const calls=await fixtures(page);
  await page.route("**/saved-outfit",route=>route.fulfill({status:401,json:{detail:"Expired"}}));
  await page.goto("/history/first");
  await expect(page.getByRole("main").getByRole("alert")).toContainText("session has expired");
  await expect(page.getByText("Original request first",{exact:true})).toBeVisible();
  await expect(page.getByRole("button",{name:"Save as outfit",exact:true})).toBeDisabled();
  expect(calls.filter(x=>x.path.endsWith("/save-as-outfit"))).toHaveLength(0);
});

test("late save completion from another historical record cannot mark the current record saved",async({page})=>{
  await fixtures(page);
  let release!:()=>void;
  const held = new Promise<void>(resolve=>{release=resolve;});
  await page.route("**/recommendation-first/save-as-outfit",async route=>{
    await held;
    await route.fulfill({status:201,json:{id:"old-outfit",name:"Recommended outfit",garment_ids:["original-garment"]}}).catch(()=>{});
  });
  await page.goto("/history/first");
  const posted=page.waitForRequest(r=>r.url().endsWith("/save-as-outfit") && r.method()==="POST");
  await expect(page.getByRole("button",{name:"Save as outfit",exact:true})).toBeEnabled();
  await page.getByRole("button",{name:"Save as outfit",exact:true}).click(); await posted;
  await page.goto("/history/second"); release();
  await expect(page.getByText("Original request second",{exact:true})).toBeVisible();
  await expect(page.getByRole("button",{name:"Save as outfit",exact:true})).toBeEnabled();
  await expect(page.getByRole("button",{name:"Saved as outfit",exact:true})).toHaveCount(0);
});


test("historical visualisation retry preserves source and reports retry rejection",async({page})=>{
  await fixtures(page,{phase:"failed"});
  await page.goto("/history/first");
  await page.getByRole("link",{name:"Visualise outfit",exact:true}).click();
  await page.getByRole("button",{name:"Create visualisation",exact:true}).click();
  await expect(page.getByRole("button",{name:"Retry same inputs",exact:true})).toBeEnabled();
  let retries=0;
  await page.route("**/api/v1/visualisations",route=>{
    expect(route.request().postDataJSON()).toEqual({recommendation_id:"recommendation-first",person_image_id:"person"});
    retries++;
    return route.fulfill(retries===1 ? {status:409,json:{detail:"The original source is no longer eligible."}} : {status:202,json:{id:"retried-visual",status:"queued"}});
  });
  await page.getByRole("button",{name:"Retry same inputs",exact:true}).click();
  await expect(page.getByRole("main").getByRole("alert").filter({hasText:"original source"})).toBeVisible();
  await expect(page.getByRole("button",{name:"Retry same inputs",exact:true})).toBeEnabled();
  await page.getByRole("button",{name:"Retry same inputs",exact:true}).click();
  await expect(page).toHaveURL(/result\?id=retried-visual/);
  expect(retries).toBe(2);
  await page.goto("/history/first");
  await expect(page.getByText("Original request first",{exact:true})).toBeVisible();
});
