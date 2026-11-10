import { test, expect, type Page } from "@playwright/test";
const base = process.env.SW_SUBTYPE_URL ?? "";
if (!base) throw new Error("Set SW_SUBTYPE_URL to an owned disposable fixture server.");
const token = process.env.SW_SETUP_TOKEN ?? "";
const male = "99cc52e8-473e-4192-b6d9-a6fa3227d45c", female = "94f3e9af-86ce-48a1-b21d-c0612526dde3";
async function setup(page: Page,wearer: string) {
  expect(token).not.toBe("");
  await page.addInitScript(({ token,wearer }) => { sessionStorage.setItem("smart_wardrobe_access_token",token); sessionStorage.setItem("smart_wardrobe_profile_id",wearer); },{token,wearer});
  await page.goto(base+"/assistant");
  await page.getByRole("combobox",{name:"Select active wardrobe profile"}).first().selectOption(wearer);
  await page.goto(base+"/assistant"); await page.getByRole("button",{name:"New Chat",exact:true}).click();
}
async function submit(page: Page,text: string) {
  await page.getByLabel("What would you like to wear?",{exact:true}).fill(text);
  const pending=page.waitForResponse(r => r.url().includes("/recommendations?pipeline=integrated") && r.request().method()==="POST");
  await page.getByRole("button",{name:"Suggest an outfit",exact:true}).click();return pending;
}
for (const [wearer,noun,kind] of [[male,"T-shirt","t_shirt"],[female,"blouse","blouse"]]) {
  test(`${kind}: exact type, alternative and immutable history`,async ({page}) => {
    await setup(page,wearer);const response=await submit(page,`I want a ${noun}.`);expect(response.status()).toBe(201);const root=await response.json();
    expect(root.provenance.attribute_selection.intent.conditions.groups.some((g: {conditions: {attribute:string;values:string[]}[]}) => g.conditions.some(c=>c.attribute==="verified_subtype" && c.values.includes(kind)))).toBe(true);
    await expect(page.getByRole("region",{name:"Captured garment types"})).toContainText(noun);
    const pending=page.waitForResponse(r=>r.url().includes("/recommendations?pipeline=integrated") && r.request().method()==="POST");await page.getByRole("button",{name:"Suggest another outfit",exact:true}).click();const childResponse=await pending;expect(childResponse.status()).toBe(201);const child=await childResponse.json();
    expect(child.id).not.toBe(root.id);expect(child.provenance.attribute_selection.intent).toEqual(root.provenance.attribute_selection.intent);
    await page.goto(base+"/history/"+child.chat_id);await expect(page.getByRole("region",{name:"Captured garment types"})).toContainText(noun);
  });
}
test('male explicit blouse gives a visible policy conflict',async ({page})=>{
  await setup(page,male);const response=await submit(page,"I want a blouse for shopping.");expect(response.status()).toBe(409);
  await expect(page.getByText(/Blouses are not permitted for the selected male wearer/).first()).toBeVisible();
});
test('shared wardrobe type review exposes category-compatible choices and retained audit',async ({page})=>{
  await setup(page,female);await page.goto(base+"/wardrobe");
  const card=page.locator('[data-garment-id="1ce62602-5a30-4f14-81e3-a83b96201648"]');await expect(card).toContainText('Garment type: Blouse');
  await card.getByRole('button',{name:/Edit/}).first().click();
  const review=card.getByRole('region',{name:'Garment type review'});await expect(review.getByLabel('Reviewed garment type')).toHaveValue('blouse');
  await expect(review.getByLabel('Reviewed garment type').locator('option')).toHaveCount(6);
  await review.getByText('Type review history',{exact:true}).click();await expect(review).toContainText('Approved frozen synthetic owner declaration');
});
