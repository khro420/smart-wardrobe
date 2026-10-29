import {test,expect} from "@playwright/test";
import {mkdirSync,writeFileSync} from "node:fs";
import {resolve} from "node:path";

test("repeated real HTTP and production-browser baseline",async({page,request}) => {
  const records: unknown[] = [];
  const summarize = (values:number[]) => {
    const ordered=[...values].sort((a,b)=>a-b),middle=Math.floor(values.length/2);
    return {samples:values,median:values.length%2?ordered[middle]:(ordered[middle-1]+ordered[middle])/2,min:ordered[0],max:ordered.at(-1),...(values.length>=20?{p95:ordered[Math.ceil(values.length*.95)-1]}:{})};
  };
  const output = resolve("../storage/verification/phase5f/latency.json");
  mkdirSync(resolve(output,".."),{recursive:true});
  for (const size of [20,50,100,200]) {
    const auth = await request.post("http://127.0.0.1:3101/api/v1/account/login",{data:{email:`load-${size}@example.test`,password:"Isolated-test-password-123"}});
    expect(auth.ok()).toBeTruthy();
    const token = (await auth.json()).access_token;
    const headers = {Authorization:`Bearer ${token}`};
    for (const flow of ["homepage","assistant","history","authenticated_capabilities"]) {
      const times:number[]=[];
      for (let trial=-1;trial<20;trial++) {
        const start = performance.now();
        const response = flow === "history" ? await request.get("http://127.0.0.1:3101/api/v1/chats?search=campus&limit=50",{headers}) : flow === "authenticated_capabilities" ? await request.get("http://127.0.0.1:3101/api/v1/recommendations/capabilities",{headers}) : await request.post(`http://127.0.0.1:3101/api/v1/recommendations${flow === "homepage"?"/homepage":"?pipeline=integrated"}`,{headers,data:{submission_key:crypto.randomUUID(),...(flow === "assistant"?{request_text:"Suggest an outfit with vintage style"}:{})}});
        const value = await response.json();
        const seconds = (performance.now()-start)/1000;
        expect(response.ok(),JSON.stringify(value)).toBeTruthy();
        if (flow === "assistant") {
          expect(value.outcome).toBe("Selected");
          const counts = [Math.floor(size*.4),Math.floor(size*.4),Math.floor(size*.1)];
          expect(value.recommendation.provenance.scored_count).toBe((counts[0]*counts[1]+counts[2])*(1+size-counts.reduce((a,b)=>a+b,0)));
        }
        if (flow === "homepage") expect(value.status).toBe("Selected");
        if (flow === "history") expect(value.total).toBe(100);
        if (trial>=0) times.push(seconds);
      }
      records.push({size,flow,layer:"real HTTP API; one warm-up excluded",...summarize(times)});
      writeFileSync(output,JSON.stringify({records},null,2));
      console.log(JSON.stringify(records.at(-1)));
    }
    for (const flow of ["homepage","assistant","history"]) {
      const times:number[]=[],render:number[]=[];
      for (let trial=-1;trial<5;trial++) {
        await page.goto("/auth");
        await page.evaluate(value => {sessionStorage.clear();sessionStorage.setItem("smart_wardrobe_access_token",value);},token);
        if (flow === "homepage") {
          const response = page.waitForResponse(r=>r.url().includes("/recommendations/homepage")&&r.request().method()==="POST");
          await page.goto("/",{waitUntil:"load"});
          const loaded=performance.now();
          await response;
          const received=performance.now();
          await expect(page.getByTestId("recommendation-result")).toBeVisible();
          if(trial>=0){times.push((performance.now()-loaded)/1000);render.push((performance.now()-received)/1000);}
        } else if (flow === "assistant") {
          await page.goto("/assistant");
          await page.getByLabel("What would you like to wear?").fill("Suggest an outfit with vintage style");
          const response=page.waitForResponse(r=>r.url().includes("pipeline=integrated")&&r.request().method()==="POST");
          const start=performance.now();
          await page.getByRole("button",{name:"Suggest an outfit",exact:true}).click();
          await response;
          const received=performance.now();
          await expect(page.getByTestId("recommendation-result")).toBeVisible();
          if(trial>=0){times.push((performance.now()-start)/1000);render.push((performance.now()-received)/1000);}
        } else {
          await page.goto("/history");
          await page.getByLabel("Search original requests").fill("campus");
          const response=page.waitForResponse(r=>r.url().includes("/chats?")&&r.url().includes("search=campus"));
          const start=performance.now();
          await page.getByRole("button",{name:"Search history",exact:true}).click();
          await response;
          const received=performance.now();
          await expect(page.getByRole("main").getByRole("status")).toContainText("100 completed");
          if(trial>=0){times.push((performance.now()-start)/1000);render.push((performance.now()-received)/1000);}
        }
      }
      records.push({size,flow,layer:"production Chromium; one warm-up excluded; no p95 claim from five trials",...summarize(times),response_to_visible:summarize(render)});
      writeFileSync(output,JSON.stringify({records},null,2));
      console.log(JSON.stringify(records.at(-1)));
    }
  }
});
