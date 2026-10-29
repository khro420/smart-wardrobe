import {test,expect} from "@playwright/test";

test("real browser review blocker and controlled recommendation/history boundaries",async({page,request}) => {
  const auth=await request.post("http://127.0.0.1:3101/api/v1/account/login",{data:{email:"load-1@example.test",password:"Isolated-test-password-123"}});
  expect(auth.ok()).toBeTruthy();
  const token=(await auth.json()).access_token,headers={Authorization:`Bearer ${token}`};
  await page.addInitScript(value=>sessionStorage.setItem("smart_wardrobe_access_token",value),token);
  // Exercise the existing browser upload form using an explicitly synthetic image.
  // AI mode is development: this is NOT a CV model accuracy experiment.
  await page.goto("/extract");
  await page.getByLabel("Wardrobe image").setInputFiles("public/logo.png");
  await page.waitForURL("**/extract/results?job=**");
  const jobId=new URL(page.url()).searchParams.get("job")!;
  const reviewed=page.waitForResponse(r=>r.url().endsWith(`/processing/jobs/${jobId}/review`));
  await page.getByRole("button",{name:/accept/i}).first().click();
  const failure=await reviewed;
  expect(failure.status()).toBe(422);
  const payload=failure.request().postDataJSON();
  expect(payload.items[0].attributes).toHaveProperty("neckline");
  expect(payload.items[0].attributes).toHaveProperty("sleeve_length");
  const confirmation=await request.post(`http://127.0.0.1:3101/api/v1/processing/jobs/${jobId}/confirm`,{headers,data:{save_mode:"garments",item_ids:[payload.items[0].item_id]}});
  expect(confirmation.status()).toBe(409);
  console.log("BLOCKED normal onboarding: captured browser review 422 and subsequent API confirmation 409; development processing only.");

  const key=crypto.randomUUID(),body={submission_key:key,request_text:"Suggest an outfit with vintage style"};
  const [a,b]=await Promise.all([request.post("http://127.0.0.1:3101/api/v1/recommendations?pipeline=integrated",{headers,data:body}),request.post("http://127.0.0.1:3101/api/v1/recommendations?pipeline=integrated",{headers,data:body})]);
  const first=await a.json(),second=await b.json();
  expect(first.recommendation.id).toBe(second.recommendation.id);
  const detail=await request.get(`http://127.0.0.1:3101/api/v1/chats/${first.recommendation.chat_id}`,{headers});
  const stored=await detail.json();
  expect(stored.recommendation.score_metadata).toBeTruthy();
  expect(stored.recommendation.provenance.scoring_profile).toBe("compatibility_deferred");
  expect((await (await request.get("http://127.0.0.1:3101/api/v1/chats",{headers})).json()).total).toBe(1);
  const unsupported=await request.post("http://127.0.0.1:3101/api/v1/recommendations?pipeline=integrated",{headers,data:{submission_key:crypto.randomUUID(),request_text:"Recommend a blue top and black trousers outfit"}});
  expect((await unsupported.json()).outcome).toBe("UnsupportedRequest");
  expect((await (await request.get("http://127.0.0.1:3101/api/v1/chats",{headers})).json()).total).toBe(1);
  const requests:string[]=[];
  page.on("request",r=>{if(r.method()==="POST"&&r.url().includes("/recommendations")) requests.push(r.url());});
  await page.goto(`/history/${stored.chat_id}`);
  await expect(page.getByText(body.request_text,{exact:true})).toBeVisible();
  expect(requests).toHaveLength(0);
  expect((await request.get("http://127.0.0.1:3101/api/v1/chats?cursor=tampered",{headers})).status()).toBe(422);
  expect((await request.get("http://127.0.0.1:3101/api/v1/chats",{headers:{Authorization:"Bearer expired.1.invalid"}})).status()).toBe(401);
  const secondLogin=await request.post("http://127.0.0.1:3101/api/v1/account/login",{data:{email:"load-20@example.test",password:"Isolated-test-password-123"}});
  const otherHeaders={Authorization:`Bearer ${(await secondLogin.json()).access_token}`};
  expect((await request.get(`http://127.0.0.1:3101/api/v1/chats/${stored.chat_id}`,{headers:otherHeaders})).status()).toBe(404);
  const firstPage=await (await request.get("http://127.0.0.1:3101/api/v1/chats?search=campus&limit=1",{headers:otherHeaders})).json();
  expect(firstPage.total).toBe(100);expect(firstPage.next_cursor).toBeTruthy();
  const next=await (await request.get(`http://127.0.0.1:3101/api/v1/chats?search=campus&limit=1&cursor=${encodeURIComponent(firstPage.next_cursor)}`,{headers:otherHeaders})).json();
  expect(next.items[0].chat_id).not.toBe(firstPage.items[0].chat_id);
  const garmentId=stored.recommendation.items[0].garment_id;
  expect((await request.patch(`http://127.0.0.1:3101/api/v1/wardrobe/garments/${garmentId}`,{headers,data:{attributes:{style:null}}})).ok()).toBeTruthy();
  await page.goto("/assistant");
  await page.getByLabel("What would you like to wear?").fill("Suggest an outfit with vintage style");
  await page.getByRole("button",{name:"Suggest an outfit",exact:true}).click();
  // Existing Wardrobe normalizes null style to [], losing missing-vs-empty state.
  // Record its current controlled failure; do not repair teammate normalization.
  await expect(page.getByRole("main").getByRole("alert")).toContainText("No outfit meets");
  expect((await request.patch(`http://127.0.0.1:3101/api/v1/wardrobe/garments/${garmentId}`,{headers,data:{primary_colour:null}})).ok()).toBeTruthy();
  await page.getByRole("button",{name:"New Chat",exact:true}).click();
  await page.getByLabel("What would you like to wear?").fill("Suggest an outfit with blue colours");
  await page.getByRole("button",{name:"Suggest an outfit",exact:true}).click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText("insufficient");
  expect((await (await request.get("http://127.0.0.1:3101/api/v1/chats",{headers})).json()).total).toBe(1);
  expect((await request.delete(`http://127.0.0.1:3101/api/v1/wardrobe/garments/${garmentId}`,{headers})).status()).toBe(204);
  await page.goto(`/history/${stored.chat_id}`);
  await expect(page.getByText("Unavailable for current use")).toBeVisible();
  const empty=await request.post("http://127.0.0.1:3101/api/v1/recommendations?pipeline=integrated",{headers,data:{submission_key:crypto.randomUUID(),request_text:"Suggest an outfit"}});
  expect((await empty.json()).outcome).toBe("NoEligibleGarments");
  await page.goto("/");
  await expect(page.getByText(/No confirmed, available garments can be used/)).toBeVisible();
  await expect(page.getByTestId("recommendation-result")).toHaveCount(0);
});
