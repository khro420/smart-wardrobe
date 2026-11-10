import { test, expect, type Page } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const root=process.env.LANGUAGE_REVIEW_ROOT!;
const seed=JSON.parse(readFileSync(join(root,"../../hands_on_20261107/seed-complete.json"),"utf8")) as {credentials:{email:string;password:string};profiles:{id:string;name:string}[]};
const wearer=seed.profiles.find(p=>p.name!=="Wearer B")!;
const journeys: [string,string,boolean][]=[
 ["social.meal","I'm going out to eat.",true],
 ["everyday.academic_attendance","Need an outfit for uni.",true],
 ["academic.library_study","Gonna do some studying at the library.",true],
 ["academic.group_study","Got a group study session.",true],
 ["professional.office_day","What should I wear to the office?",true],
 ["professional.workplace_meeting","Got a work meeting.",true],
 ["professional.job_interview","I'm the candidate at a job interview; the dress code is smart casual.",false],
 ["academic.presentation","I'm giving a university presentation as a presenter.",false],
 ["ceremony.wedding","I'm going to a wedding, what should I wear?",false],
 ["everyday.shopping","Going shopping.",true],
 ["everyday.casual_outing","Need an outfit for a casual outing.",true],
 ["social.date","Got a date tomorrow.",true],
 ["social.birthday_gathering","Gonna attend a birthday celebration.",true],
 ["social.house_gathering","Gonna visit a friend's house.",true],
 ["leisure.cinema_outing","Going to the movies.",true],
 ["social.cafe_meetup","Having coffee with someone.",true],
 ["leisure.city_sightseeing","Gonna explore city sights.",true],
 ["travel.journey","Need an outfit for travelling by train.",true],
];
type Result={outcome:string;id:string;chat_id:string;request_text:string;items:{garment_id:string;garment_role:string}[];provenance:{general_context:{situation:string}};scoring_display:{kind:string;refinement?:{next_action?:unknown}}};
async function login(page:Page){
 await page.goto("/auth");await page.waitForLoadState("networkidle");
 await page.getByLabel("Email",{exact:true}).fill(seed.credentials.email);await page.getByLabel("Password",{exact:true}).fill(seed.credentials.password);
 await page.locator("form").getByRole("button",{name:"Sign in",exact:true}).click();await expect(page).toHaveURL(/\/$/);
 await page.getByRole("combobox",{name:"Select active wardrobe profile"}).first().selectOption(wearer.id);await page.waitForLoadState("networkidle");
}
async function fresh(page:Page,text:string){await page.goto("/assistant");await page.getByRole("button",{name:"New Chat",exact:true}).click();await page.getByLabel("What would you like to wear?",{exact:true}).fill(text);}
async function send(page:Page,button="Suggest an outfit"){
 const response=page.waitForResponse(r=>r.url().includes("/recommendations?pipeline=integrated")&&r.request().method()==="POST");
 await page.getByRole("button",{name:button,exact:true}).click();return await response;
}
test.beforeEach(async({page})=>{await login(page);});
for(const [sid,text,alternative] of journeys){
 test(`NL ${sid} natural wording, stored explanation and action boundary`,async({page})=>{
  await fresh(page,text);const response=await send(page);expect(response.status()).toBe(201);const first=await response.json() as Result;
  expect(first.outcome).toBe("Selected");expect(first.provenance.general_context.situation).toBe(sid);
  await expect(page.getByRole("heading",{name:"Your outfit recommendation",exact:true})).toBeVisible();
  let child:Result|undefined;
  if(alternative){const next=await send(page,"Suggest another outfit");expect(next.status()).toBe(201);child=await next.json() as Result;expect(child.outcome).toBe("Selected");expect(child.items.filter(i=>i.garment_role!=="outerwear").map(i=>i.garment_id)).not.toEqual(first.items.filter(i=>i.garment_role!=="outerwear").map(i=>i.garment_id));expect(child.request_text).toBe(first.request_text);}
  else {await expect(page.getByRole("button",{name:"Suggest another outfit",exact:true})).toHaveCount(0);expect(first.scoring_display.refinement?.next_action).toBeFalsy();}
  const saved=child??first;await page.goto(`/history/${saved.chat_id}`);await expect(page.getByRole("heading",{name:/Saved recommendation/})).toBeVisible();await page.reload();await expect(page.getByRole("heading",{name:/Saved recommendation/})).toBeVisible();
  writeFileSync(join(root,"browser-results",sid+".json"),JSON.stringify({first,child},null,2));
 });
}
test("NL combined B1 P2 C2, alternative conditions and history",async({page})=>{
 await fresh(page,"I'm going out to eat and want a plain cotton v-neck top.");await page.getByLabel("Use recorded palette colours for compatibility",{exact:true}).check();
 const response=await send(page);expect(response.status()).toBe(201);const body=response.request().postDataJSON() as {preference_profile:string;compatibility_profile:string};expect(body.preference_profile).toBe("attribute_preference_decision_v2");expect(body.compatibility_profile).toBe("recorded_palette_compatibility_v1");
 const first=await response.json() as Result;expect(first.outcome).toBe("Selected");await expect(page.getByRole("region",{name:"Recorded palette compatibility",exact:true})).toBeVisible();
 const next=await send(page,"Suggest another outfit");const child=await next.json() as Result;expect(child.outcome).toBe("Selected");expect(child.request_text).toBe(first.request_text);
 await page.goto(`/history/${child.chat_id}`);await expect(page.getByRole("region",{name:"Recorded palette compatibility",exact:true})).toBeVisible();writeFileSync(join(root,"browser-results","combined.json"),JSON.stringify({first,child},null,2));
});
test("NL ambiguity, soft requests, unsupported feature and negation feedback",async({page})=>{
 for(const [text,message] of [["Not going to class.","Which occasion"],["Office party.","Which activity"],["Something plain, preferably blue.","soft preference"],["Give me another outfit like that, but not the same clothes.","completed recommendation"],["Dinner with a quantum-energy top.","could not represent"]]){
  await fresh(page,text);const response=await send(page);expect(response.status()).toBe(422);await expect(page.getByText(message,{exact:false}).first()).toBeVisible();await expect(page.getByRole("heading",{name:"Your outfit recommendation",exact:true})).toHaveCount(0);
 }
});
