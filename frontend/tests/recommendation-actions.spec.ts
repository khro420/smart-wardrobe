import { test, expect } from "@playwright/test";

// Synthetic image; actual browser upload/review/confirmation APIs, development AI.
const image = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAQAAAAEACAIAAADTED8xAAACvUlEQVR4nO3TMQEAIAzAsIFypCNjRxMFfXpm3kDV3Q6ATQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMQJoBSDMAaQYgzQCkGYA0A5BmANIMwJR9wzwCgDzi8ToAAAAASUVORK5CYII=", "base64");
for (const category of ["short_sleeve_top", "trousers"]) {
  test(`real backend upload, corrected review and confirmation: ${category}`, async ({page,request}) => {
    const auth = await request.post("http://127.0.0.1:3101/api/v1/account/login", {data:{email:"browser-owner@example.test",password:"Browser-test-password-123"}});
    expect(auth.ok()).toBeTruthy();
    const {access_token:token} = await auth.json();
    await page.addInitScript(value => sessionStorage.setItem("smart_wardrobe_access_token",value), token);
    await page.goto("/extract");
    await page.getByLabel("Wardrobe image").setInputFiles({name:"synthetic-garment.png",mimeType:"image/png",buffer:image});
    await page.waitForURL("**/extract/results?job=**");
    const candidate = page.getByRole("article",{name:/Candidate/}).first();
    await expect(candidate).toBeVisible();
    await candidate.getByText("Edit details and review image",{exact:true}).click();
    await candidate.getByLabel("Category",{exact:true}).selectOption(category);
    await candidate.getByLabel("Garment name").fill(`Browser corrected ${category}`);
    await candidate.getByLabel("Style").selectOption("vintage");
    await candidate.getByLabel("Material").selectOption("");
    const reviewed = page.waitForResponse(r=>r.url().endsWith("/review") && r.request().method()==="POST");
    await candidate.getByRole("button",{name:/Accept/}).click();
    const response = await reviewed;
    expect(response.status()).toBe(200);
    const attributes = response.request().postDataJSON().items[0].attributes;
    expect(attributes).not.toHaveProperty("neckline");
    expect(attributes).not.toHaveProperty("sleeve_length");
    expect(attributes.style).toBe("vintage");
    expect(attributes.material).toBeNull();
    const confirmed = page.waitForResponse(r=>r.url().endsWith("/confirm") && r.request().method()==="POST");
    await page.getByRole("button",{name:"Save selected garments",exact:true}).click();
    expect((await confirmed).status()).toBe(201);
    await page.waitForURL("**/wardrobe");
    const garments = await request.get("http://127.0.0.1:3101/api/v1/wardrobe/garments",{headers:{Authorization:`Bearer ${token}`}});
    expect((await garments.json()).some((g:{name:string;category:string})=>g.name===`Browser corrected ${category}` && g.category===category)).toBe(true);
  });
}

test("real backend save is repeatable and retains historical recommendation status",async({page,request})=>{
  const auth = await request.post("http://127.0.0.1:3101/api/v1/account/login",{data:{email:"browser-owner@example.test",password:"Browser-test-password-123"}});
  const {access_token:token} = await auth.json(); const headers={Authorization:`Bearer ${token}`};
  await page.addInitScript(value => sessionStorage.setItem("smart_wardrobe_access_token",value),token);
  const responsePromise=page.waitForResponse(r=>r.url().endsWith("/recommendations/homepage") && r.request().method()==="POST");
  await page.goto("/");
  const response=await responsePromise;
  const record=(await response.json()).recommendation;
  const submission=response.request().postDataJSON();
  const url=`http://127.0.0.1:3101/api/v1/recommendations/${record.id}/save-as-outfit`;
  const saved=page.waitForResponse(r=>r.url().endsWith("/save-as-outfit") && r.request().method()==="POST");
  await page.getByRole("button",{name:"Save as outfit",exact:true}).click();
  const first=await saved; expect(first.status()).toBe(201);
  const firstResult=await first.json();
  const second=await request.post(url,{headers,data:{name:"Recommended outfit"}});
  expect(await second.json()).toEqual(firstResult);
  const state=await request.get(`http://127.0.0.1:3101/api/v1/recommendations/${record.id}/saved-outfit`,{headers});
  expect((await state.json()).saved).toBe(true);
  const replay=await request.post("http://127.0.0.1:3101/api/v1/recommendations/homepage",{headers,data:submission});
  expect((await replay.json()).recommendation).toEqual(record);
  await expect(page.getByRole("button",{name:"Saved as outfit",exact:true})).toBeDisabled();
  await page.reload();
  await expect(page.getByRole("heading",{name:/Saved recommendation.*read-only/})).toBeVisible();
  await expect(page.getByRole("button",{name:"Save as outfit",exact:true})).toHaveCount(0);
  // Release this test's active outfit dependency before the existing archival test.
  expect((await request.delete(`http://127.0.0.1:3101/api/v1/wardrobe/outfits/${firstResult.id}`,{headers})).status()).toBe(204);
});
