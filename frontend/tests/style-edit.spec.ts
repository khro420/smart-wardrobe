import { test, expect, type Page, type APIRequestContext } from "@playwright/test";

async function login(page: Page, request: APIRequestContext) {
  const response = await request.post("http://127.0.0.1:3101/api/v1/account/login", {data:{email:"browser-owner@example.test",password:"Browser-test-password-123"}});
  expect(response.ok()).toBeTruthy();
  const {access_token: token} = await response.json();
  await page.addInitScript(value => sessionStorage.setItem("smart_wardrobe_access_token",value),token);
  await page.goto("/wardrobe");
  return {Authorization:`Bearer ${token}`};
}

async function upload(page: Page, request: APIRequestContext, headers: Record<string,string>) {
  const data = await page.evaluate(() => {
    const canvas=document.createElement("canvas");canvas.width=256;canvas.height=256;
    const context=canvas.getContext("2d")!;context.fillStyle="blue";context.fillRect(0,0,256,256);
    return canvas.toDataURL("image/png").split(",")[1];
  });
  const result=await request.post("http://127.0.0.1:3101/api/v1/processing/jobs",{headers,multipart:{file:{name:"synthetic-style.png",mimeType:"image/png",buffer:Buffer.from(data,"base64")}}});
  expect(result.status()).toBe(202);
  const id=(await result.json()).id;
  await expect.poll(async () => {
    const job=await (await request.get(`http://127.0.0.1:3101/api/v1/processing/jobs/${id}`,{headers})).json();
    return job.status;
  }).toBe("review_required");
  return await (await request.get(`http://127.0.0.1:3101/api/v1/processing/jobs/${id}`,{headers})).json();
}

for (const initial of [null, [], ["vintage","classic"], "vintage"]) {
  test(`actual wardrobe edit preserves style ${JSON.stringify(initial)} and explicit transitions`,async({page,request})=>{
    const headers=await login(page,request);
    const job=await upload(page,request,headers);const item=job.items[0].id;
    const reviewed=await request.post(`http://127.0.0.1:3101/api/v1/processing/jobs/${job.id}/review`,{headers,data:{items:[{item_id:item,decision:"accepted",category:"vest_dress",attributes:{style:initial,custom_tags:["ordinary preserved note"],fit:["regular","loose"],material:["cotton","linen"]}}]}});
    expect(reviewed.status()).toBe(200);
    const confirmed=await request.post(`http://127.0.0.1:3101/api/v1/processing/jobs/${job.id}/confirm`,{headers,data:{save_mode:"garments",item_ids:[item]}});
    expect(confirmed.status()).toBe(201);const gid=(await confirmed.json()).garment_ids[0];
    const read=async()=>{
      const result=await request.get("http://127.0.0.1:3101/api/v1/wardrobe/garments",{headers});
      return (await result.json()).find((g:{id:string})=>g.id===gid);
    };
    const before=await read();
    await page.reload();
    const card=page.locator(`[data-garment-id="${gid}"]`);
    const edit=async()=>{await card.getByRole("button",{name:"Edit",exact:true}).click();return card.getByRole("form");};
    let form=await edit();
    // Saving an untouched form uses an empty PATCH, preserving exact raw state.
    let response=page.waitForResponse(r=>r.url().endsWith(`/garments/${gid}`)&&r.request().method()==="PATCH");
    await form.getByRole("button",{name:"Save changes",exact:true}).click();
    expect((await response).request().postDataJSON()).toEqual({});
    expect((await read()).attributes).toEqual(before.attributes);
    await page.reload();form=await edit();
    await form.getByLabel("Primary colour",{exact:true}).fill("white");
    response=page.waitForResponse(r=>r.url().endsWith(`/garments/${gid}`)&&r.request().method()==="PATCH");
    await form.getByRole("button",{name:"Save changes",exact:true}).click();
    expect((await response).request().postDataJSON()).toEqual({primary_colour:"white"});
    let current=await read();
    expect(current.attributes.style).toEqual(initial);
    expect(current.attributes.custom_tags).toEqual(["ordinary preserved note"]);
    expect(current.attributes.fit).toEqual(["regular","loose"]);
    expect(current.attributes.material).toEqual(["cotton","linen"]);
    await page.reload();form=await edit();
    // Blank CSV is not interpreted as an instruction to erase evidence.
    await form.getByLabel("Styles (comma-separated)",{exact:true}).fill("   ");
    await form.getByRole("button",{name:"Save changes",exact:true}).click();
    await expect(page.getByText("Enter style tags, or explicitly choose Unknown or No assigned tags.",{exact:true})).toBeVisible();
    expect((await read()).attributes.style).toEqual(initial);
    for (const [mode,value] of [["empty",[]],["unknown",null],["values",["classic","vintage"]]] as const) {
      await form.getByRole("combobox",{name:"Style evidence",exact:true}).selectOption(mode);
      if(mode==="values") await form.getByLabel("Styles (comma-separated)",{exact:true}).fill("classic, vintage");
      response=page.waitForResponse(r=>r.url().endsWith(`/garments/${gid}`)&&r.request().method()==="PATCH");
      await form.getByRole("button",{name:"Save changes",exact:true}).click();
      expect((await response).status()).toBe(200);
      current=await read();expect(current.attributes.style).toEqual(value);
      expect(current.style_tags).toEqual(value);
      await page.reload();form=await edit();
    }
  });
}

for (const choice of ["__keep","__empty","__unknown"]) {
  test(`actual review and confirmation preserve explicit style choice ${choice}`,async({page,request})=>{
    const headers=await login(page,request);const job=await upload(page,request,headers);const item=job.items[0].id;
    // Existing multi-style annotation is reviewed again through the real UI.
    expect((await request.post(`http://127.0.0.1:3101/api/v1/processing/jobs/${job.id}/review`,{headers,data:{items:[{item_id:item,decision:"accepted",category:"vest_dress",attributes:{style:["vintage","classic"]}}]}})).status()).toBe(200);
    await page.goto(`/extract/results?job=${job.id}`);
    const candidate=page.getByRole("article",{name:/Candidate/}).first();
    await candidate.getByText("Edit details and review image",{exact:true}).click();
    await candidate.getByRole("combobox",{name:"Style",exact:true}).selectOption(choice);
    const response=page.waitForResponse(r=>r.url().endsWith("/review")&&r.request().method()==="POST");
    await candidate.getByRole("button",{name:/Accept/}).click();
    const result=await response;expect(result.status()).toBe(200);
    const attrs=result.request().postDataJSON().items[0].attributes;
    if(choice==="__keep") expect(attrs).not.toHaveProperty("style");
    else expect(attrs.style).toEqual(choice==="__empty"?[]:null);
    const confirm=page.waitForResponse(r=>r.url().endsWith("/confirm")&&r.request().method()==="POST");
    await page.getByRole("button",{name:"Save selected garments",exact:true}).click();
    const saved=await confirm;expect(saved.status()).toBe(201);
    await page.waitForURL("**/wardrobe");await page.reload();
    const garments=await (await request.get("http://127.0.0.1:3101/api/v1/wardrobe/garments",{headers})).json();
    const garment=garments.find((g:{processing_item_id:string})=>g.processing_item_id===item);
    expect(garment).toBeTruthy();
    expect(garment.attributes.style).toEqual(choice==="__keep"?["vintage","classic"]:choice==="__empty"?[]:null);
  });
}
