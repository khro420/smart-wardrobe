import { test,expect,type Page,type APIRequestContext } from "@playwright/test";

const values=[...["campus","work","casual_outing","shopping","dinner","party","date","travel"].map(value=>({field:"occasion",value})),...["casual","smart_casual"].map(value=>({field:"formality",value}))];
const label=(field:string,value:string)=>`${field==="occasion"?"Occasion":"Formality"}: ${value.replaceAll("_"," ").replace(/^./,c=>c.toUpperCase())}`;
async function setup(page:Page,request:APIRequestContext,tags:string[],style:null|[] = null) {
  const auth=await request.post("http://127.0.0.1:3101/api/v1/account/login",{data:{email:"browser-owner@example.test",password:"Browser-test-password-123"}});
  expect(auth.ok()).toBeTruthy();const {access_token:token}=await auth.json();const headers={Authorization:`Bearer ${token}`};
  await page.addInitScript(value=>sessionStorage.setItem("smart_wardrobe_access_token",value),token);
  await page.goto("/wardrobe");
  const image=await page.evaluate(()=>{const c=document.createElement("canvas");c.width=256;c.height=256;const x=c.getContext("2d")!;x.fillStyle="blue";x.fillRect(0,0,256,256);return c.toDataURL("image/png").split(",")[1];});
  const upload=await request.post("http://127.0.0.1:3101/api/v1/processing/jobs",{headers,multipart:{file:{name:"synthetic-suitability.png",mimeType:"image/png",buffer:Buffer.from(image,"base64")}}});
  expect(upload.status()).toBe(202);const jobId=(await upload.json()).id;
  const readJob=async()=>await(await request.get(`http://127.0.0.1:3101/api/v1/processing/jobs/${jobId}`,{headers})).json();
  await expect.poll(async()=>(await readJob()).status).toBe("review_required");const item=(await readJob()).items[0].id;
  expect((await request.post(`http://127.0.0.1:3101/api/v1/processing/jobs/${jobId}/review`,{headers,data:{items:[{item_id:item,decision:"accepted",category:"vest_dress",attributes:{style,custom_tags:tags}}]}})).status()).toBe(200);
  const confirmed=await request.post(`http://127.0.0.1:3101/api/v1/processing/jobs/${jobId}/confirm`,{headers,data:{save_mode:"garments",item_ids:[item]}});
  expect(confirmed.status()).toBe(201);const gid=(await confirmed.json()).garment_ids[0];
  const read=async()=>{const rows=await(await request.get("http://127.0.0.1:3101/api/v1/wardrobe/garments",{headers})).json();return rows.find((g:{id:string})=>g.id===gid);};
  await page.reload();
  const card=page.locator(`[data-garment-id="${gid}"]`);
  const edit=async()=>{await card.getByRole("button",{name:"Edit",exact:true}).click();return card.getByRole("form");};
  const save=async()=>{const response=page.waitForResponse(r=>r.url().endsWith(`/garments/${gid}`)&&r.request().method()==="PATCH");await card.getByRole("button",{name:"Save changes",exact:true}).click();const result=await response;expect(result.status()).toBe(200);return result;};
  return {gid,headers,read,card,edit,save};
}

for(const [index,{field,value}] of values.entries()) {
  test(`persisted ${field} ${value}: Unknown Allow Deny and preservation`,async({page,request})=>{
    const initialStyle=index%2===0?null:[] as [];
    const f=await setup(page,request,["ordinary note"],initialStyle);let form=await f.edit();
    for(const item of values) await expect(form.getByRole("combobox",{name:label(item.field,item.value),exact:true})).toHaveValue("unknown");
    const select=()=>form.getByRole("combobox",{name:label(field,value),exact:true});
    expect(await select().locator("option").allTextContents()).toEqual(["Unknown","Allow","Deny"]);
    // Unchanged save does not manufacture [] or tags.
    let response=await f.save();expect(response.request().postDataJSON()).toEqual({});
    await page.reload();form=await f.edit();
    for(const choice of ["allow","deny","unknown"]) {
      await select().selectOption(choice);response=await f.save();
      expect(response.request().headers()["if-match"]).toBeTruthy();
      const row=await f.read();
      expect(row.custom_tags).toEqual(choice==="unknown"?["ordinary note"]:["ordinary note",`rec:v1:${field}:${value}:${choice}`]);
      expect(row.attributes.style).toEqual(initialStyle);
      await page.reload();form=await f.edit();await expect(select()).toHaveValue(choice);
      expect(await form.getByLabel("Tags",{exact:true}).inputValue()).toBe("ordinary note");
    }
  });
}

test("conflict and malformed annotations stay unresolved until explicit correction",async({page,request})=>{
  const tags=["ordinary note","rec:v1:occasion:campus:allow","rec:v1:occasion:campus:deny","rec:v1:occasion:work:allow","rec:v1:formality:casual:allow","rec:v2:occasion:date:allow"];
  const f=await setup(page,request,tags,[]);let form=await f.edit();
  await expect(form.getByText(/Saved Allow and Deny conflict/)).toBeVisible();
  await expect(form.getByText(/Unrecognised saved suitability annotations are preserved/)).toBeVisible();
  await expect(form.getByRole("combobox",{name:"Occasion: Campus",exact:true})).toHaveValue("unknown");
  expect(await form.getByLabel("Tags",{exact:true}).inputValue()).toBe("ordinary note");
  await f.save();expect((await f.read()).custom_tags).toEqual(tags);
  await page.reload();form=await f.edit();
  await form.getByRole("button",{name:"Clear conflict for Occasion: Campus",exact:true}).click();await f.save();
  const afterClear=tags.filter(t=>!t.startsWith("rec:v1:occasion:campus:"));expect((await f.read()).custom_tags).toEqual(afterClear);
  await page.reload();form=await f.edit();
  await form.getByRole("button",{name:"Remove unrecognised annotation 1",exact:true}).click();await f.save();
  const corrected=afterClear.filter(t=>!t.startsWith("rec:v2:"));expect((await f.read()).custom_tags).toEqual(corrected);
  await page.reload();form=await f.edit();
  await expect(form.getByRole("combobox",{name:"Occasion: Work",exact:true})).toHaveValue("allow");
  await expect(form.getByRole("combobox",{name:"Formality: Casual",exact:true})).toHaveValue("allow");
  await form.getByLabel("Primary colour",{exact:true}).fill("#123456");await f.save();
  const row=await f.read();expect(row.primary_colour).toBe("#123456");expect(row.custom_tags).toEqual(corrected);expect(row.attributes.style).toEqual([]);
});

test("stale browser edit is rejected without losing another session's declaration",async({page,request})=>{
  const f=await setup(page,request,["ordinary note"]);let form=await f.edit();
  await form.getByRole("combobox",{name:"Occasion: Campus",exact:true}).selectOption("allow");
  const old=await f.read();
  const other=await request.patch(`http://127.0.0.1:3101/api/v1/wardrobe/garments/${f.gid}`,{headers:{...f.headers,"If-Match":old.tag_edit.revision},data:{attributes:{custom_tags:["ordinary note","rec:v1:occasion:work:allow"]}}});
  expect(other.status()).toBe(200);
  const response=page.waitForResponse(r=>r.url().endsWith(`/garments/${f.gid}`)&&r.request().method()==="PATCH");
  await form.getByRole("button",{name:"Save changes",exact:true}).click();expect((await response).status()).toBe(409);
  await expect(page.getByText(/Tags changed in another session/)).toBeVisible();
  expect((await f.read()).custom_tags).toEqual(["ordinary note","rec:v1:occasion:work:allow"]);
  await page.reload();form=await f.edit();
  await expect(form.getByRole("combobox",{name:"Occasion: Work",exact:true})).toHaveValue("allow");
  await form.getByRole("combobox",{name:"Occasion: Campus",exact:true}).selectOption("allow");await f.save();
  expect((await f.read()).custom_tags).toEqual(["ordinary note","rec:v1:occasion:work:allow","rec:v1:occasion:campus:allow"]);
});
