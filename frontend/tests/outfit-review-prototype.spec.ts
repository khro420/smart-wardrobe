import {test,expect,type Page} from "@playwright/test";
import type {Prediction,ReviewView} from "../lib/outfit-review";
const unknown={state:"unknown" as const,values:[]};
const prediction:Prediction={version:"outfit-review-observation-1.0.0",scene:"single_person",people:[{id:"p1",region:{xyxy:[0,0,1000,1000]}}],target_person_id:"p1",footwear_visibility:"not_visible",items:[{id:"g1",person_id:"p1",region:{xyxy:[100,100,800,900]},category:"dress",category_alternatives:[],role:"one_piece",visibility:"visible",unit:"single",colours:{state:"observed",values:["blue"]},pattern:unknown,sleeve_length:unknown,sleeve_state:unknown}],layering:[],identity_questions:[]};
const blank:ReviewView={id:"temporary-fixture",state:"uploaded",image:{width:128,height:192},revision:null,generation:0,prediction:null,original_prediction:null,issues:[],confirmed:false,result:null,error:null,raw_failed_proposal:null,privacy:"Temporary memory only",expires_in_seconds:900};
const png=Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1kAAAAASUVORK5CYII=","base64");

async function setup(page:Page,mode="success"){
  let view=structuredClone(blank),writes=0;
  await page.addInitScript(()=>sessionStorage.setItem("smart_wardrobe_access_token","disposable-browser-fixture"));
  await page.route("**/api/v1/**",async route=>{
    const req=route.request(),path=new URL(req.url()).pathname;
    const send=(json:unknown,status=200)=>route.fulfill({status,json});
    if(!path.includes("outfit-reviews")){
      expect(req.method()).toBe("GET");
      return send(path.includes("activity")?{jobs:[]}:[]);
    }
    if(path.endsWith("/capabilities"))return send({enabled:mode!=="disabled",assets_present:true,ai_feedback:true});
    if(req.method()==="GET"&&path.endsWith("/photo"))return route.fulfill({contentType:"image/png",body:png});
    if(req.method()==="GET")return send(view);
    writes++;
    if(req.method()==="DELETE")return route.fulfill({status:204});
    if(path.endsWith("/analyze")){
      expect(req.postDataJSON().gpu_available).toBe(true);
      if(mode==="failure")view={...view,state:"failed",error:{code:"ModelUnavailable",message:"The pinned model is unavailable."}};
      else {
        const value=structuredClone(prediction);
        if(mode==="numeric"||mode==="normalized"){
          value.version="outfit-review-observation-1.1.0";value.feet_observation="bare_feet_visible";
          value.items[0].style={state:"observed",values:["casual"]};value.items[0].pattern={state:"observed",values:["plain"]};
        }
        if(mode==="socks"){
          value.version="outfit-review-observation-1.1.0";value.feet_observation="uncertain";
          const base=value.items[0];
          value.items=[{...structuredClone(base),id:"jersey",category:"jersey",role:"upper",unit:"unresolved",category_alternatives:["shirt","jacket"],colours:{state:"observed",values:["black","red"]}},
                       {...structuredClone(base),id:"shorts",category:"shorts",role:"lower",colours:{state:"observed",values:["black"]},region:{xyxy:[100,500,800,700]}},
                       {...structuredClone(base),id:"feet",category:"footwear",role:"footwear",unit:"footwear_pair",colours:{state:"observed",values:["white"]},region:{xyxy:[100,700,800,950]}}];
        }
        view={...view,state:"needs_review",revision:"a".repeat(64),prediction:value,original_prediction:structuredClone(value),issues:mode==="conflict"?["g1:category_role_conflict"]:mode==="socks"?["jersey:unresolved_identity","jersey:invalid_category_alternatives","feet:footwear_visibility_conflict"]:[]};
        if(mode==="normalized"){
          const original=structuredClone(value);original.items[0].pattern.values=["plain","plain","plain"];
          view.original_model_response=JSON.stringify(original);
          view.normalization={version:"identical-attribute-label-dedup-1.0.0",changes:[{path:"/items/0/pattern/values",before:["plain","plain","plain"],after:["plain"]}]};
        }
        if(mode==="review-blockers"){
          value.version="outfit-review-observation-1.1.0";value.target_person_id=null;value.feet_observation="uncertain";
          value.items.push({...structuredClone(value.items[0]),id:"false-outer",category:"jacket",role:"outerwear"});
          value.layering=[{over:"false-outer",under:"g1",state:"uncertain"}];
          view.prediction=value;view.original_prediction=structuredClone(value);view.issues=["target_selection_required","g1:wrong_person","false-outer:wrong_person"];
        }
      }
      return send(view,202);
    }
    if(path.endsWith("/inventory")){
      const body=req.postDataJSON();
      if(mode==="socks"){
        expect(body.changes).toHaveLength(3);expect(body.prediction.items[2].category).toBe("socks");expect(body.prediction.items[2].role).toBe("hosiery");expect(body.prediction.items[2].unit).toBe("pair");expect(body.prediction.footwear_visibility).toBe("not_visible");
      }else if(mode==="review-blockers"){
        expect(body.changes).toHaveLength(3);expect(body.selected_target).toBe("p1");expect(body.prediction.items).toHaveLength(1);expect(body.prediction.layering).toEqual([]);
        expect(body.changes.map((c:{operation:string})=>c.operation).sort()).toEqual(["remove_item","review_relations","select_target"]);
      }else{expect(body.changes).toHaveLength(1);expect(body.changes[0].operation).toBe("replace_item");}
      view={...view,prediction:body.prediction,revision:"b".repeat(64),confirmed:false,issues:[]};return send(view);
    }
    if(path.endsWith("/confirm")){
      expect(req.postDataJSON().inventory_reviewed).toBe(true);view={...view,confirmed:true,state:"confirmed"};return send(view);
    }
    if(path.endsWith("/review")){
      expect(view.confirmed).toBe(true);
      expect(req.postDataJSON().use_ai).toBe(true);expect(req.postDataJSON().gpu_available).toBe(true);
      view={...view,state:"completed",result:{occasion:{original_text:req.postDataJSON().occasion},overall_assessment:"Confirmation-based fixture review, not model evaluation.",facts:[{item_id:"g1",text:"User-reviewed dress"}],sections:[{dimension:"colour_coordination",text:"Recorded blue clothing. No fabric claim is made.",item_ids:["g1"]}],strengths:["User-reviewed inventory"],potential_improvements:["Check the venue requirements."],unknown_details:["g1.pattern"],limitations:["Fixture inference; not a model accuracy result."],provenance:{"g1.colours":"user_correction_not_model_verified"},rubric:{message:"Not enough information to provide a reliable score",score:null,dimensions:[{name:"occasion_suitability",weight_percent:40,score:null}]}}};
      if(mode==="numeric"&&view.result){view.result.feedback_source="local_model_grounded_anchors";view.result.rubric.score=75;view.result.rubric.message="Experimental outfit assessment";view.result.rubric.dimensions=[{name:"occasion_suitability",weight_percent:40,score:75},{name:"colour_coordination",weight_percent:25,score:90},{name:"style_consistency",weight_percent:20,score:75},{name:"pattern_layering",weight_percent:15,score:50}];}
      return send(view,202);
    }
    return send(view,201);
  });
  await page.goto("/outfit-review");
  await expect(page.getByRole("heading",{name:"AI Outfit Review",exact:true})).toBeVisible();
  return {writes:()=>writes};
}

async function upload(page:Page){
  await page.getByLabel("Outfit photograph").setInputFiles({name:"disposable.png",mimeType:"image/png",buffer:png});
  await page.getByRole("button",{name:"Upload photo",exact:true}).click();
  await expect(page.getByRole("button",{name:"Analyze Outfit",exact:true})).toBeDisabled();
  await page.getByRole("checkbox",{name:/GPU-intensive games/}).check();
  await page.getByRole("button",{name:"Analyze Outfit",exact:true}).click();
}

test("confirmation-first flow keeps corrections separate and abstains honestly",async({page})=>{
  const fixture=await setup(page);await upload(page);
  await expect(page.getByRole("button",{name:"Review My Outfit",exact:true})).toHaveCount(0);
  await expect(page.getByRole("button",{name:"Confirm Outfit Details",exact:true})).toBeDisabled();
  await page.getByLabel("Garment 1 clothing type",{exact:true}).selectOption("top");
  await page.getByRole("button",{name:"Save my corrections",exact:true}).click();
  await page.getByRole("checkbox",{name:/I reviewed the person/}).check();
  await page.getByRole("button",{name:"Confirm Outfit Details",exact:true}).click();
  await page.getByLabel("Occasion or purpose").fill("I'm going to the library to study.");
  await page.getByRole("checkbox",{name:/GPU availability is confirmed/}).check();
  await page.getByRole("button",{name:"Review My Outfit",exact:true}).click();
  await expect(page.getByText("Not enough information to provide a reliable score",{exact:true})).toBeVisible();
  await expect(page.getByRole("region",{name:"Outfit review result"})).toBeVisible();
  expect(fixture.writes()).toBe(5);
  await page.getByLabel("Garment 1 clothing type",{exact:true}).selectOption("shirt");
  await expect(page.getByRole("region",{name:"Outfit review result"})).toHaveCount(0);
});

test("structural issues prevent confirmation",async({page})=>{
  await setup(page,"conflict");await upload(page);
  await expect(page.getByText(/Confirm the clothing type so its wearing position/)).toBeVisible();
  await expect(page.getByText('g1:category_role_conflict',{exact:true})).not.toBeVisible();
  await page.getByRole("checkbox",{name:/I reviewed the person/}).check();
  await expect(page.getByRole("button",{name:"Confirm Outfit Details",exact:true})).toBeDisabled();
  await expect(page.getByRole("region",{name:"Outfit review result"})).toHaveCount(0);
});

test("unavailable model errors never show completed feedback",async({page})=>{
  await setup(page,"failure");await upload(page);
  await expect(page.getByText("The pinned model is unavailable.",{exact:true})).toBeVisible();
  await expect(page.getByRole("button",{name:"Review My Outfit",exact:true})).toHaveCount(0);
  await expect(page.getByRole("region",{name:"Outfit review result"})).toHaveCount(0);
});

test("disabled backend cannot upload or launch a model",async({page})=>{
  const fixture=await setup(page,"disabled");
  await page.getByLabel("Outfit photograph").setInputFiles({name:"disposable.png",mimeType:"image/png",buffer:png});
  await expect(page.getByRole("button",{name:"Upload photo",exact:true})).toBeDisabled();
  expect(fixture.writes()).toBe(0);
});

test("supported experimental score is displayed without hiding its subjective status",async({page})=>{
  await setup(page,"numeric");await upload(page);
  await page.getByRole('checkbox',{name:/I reviewed the person/}).check();
  await page.getByRole('button',{name:'Confirm Outfit Details',exact:true}).click();
  await page.getByLabel('Occasion or purpose').fill("I'm going to the library to study.");
  await page.getByRole('checkbox',{name:/GPU availability is confirmed/}).check();
  await page.getByRole('button',{name:'Review My Outfit',exact:true}).click();
  await expect(page.getByLabel('Overall outfit score')).toContainText('75');
  await expect(page.getByText('Experimental, subjective rating',{exact:true})).toBeVisible();
});

test("audited label deduplication is explained without exposing technical editing",async({page})=>{
  await setup(page,"normalized");await upload(page);
  await expect(page.getByText(/Repeated identical attribute labels were recorded once/)).toBeVisible();
  await expect(page.getByRole('textbox')).toHaveCount(0);
  await page.getByRole('checkbox',{name:/I reviewed the person/}).check();
  await page.getByRole('button',{name:'Confirm Outfit Details',exact:true}).click();
  await expect(page.getByText('Outfit details confirmed. You can now describe the occasion.',{exact:true})).toBeVisible();
});

test("person selection and false-layer removal resolve real-model review blockers",async({page})=>{
  await setup(page,"review-blockers");await upload(page);
  await page.getByRole('button',{name:'Choose Person 1',exact:true}).click();
  await page.getByRole('article').nth(1).getByRole('button',{name:'Remove this item',exact:true}).click();
  await page.locator('summary').filter({hasText:'Layers and identity questions'}).click();
  await page.getByRole('button',{name:'Remove relationship',exact:true}).click();
  await page.getByRole('button',{name:'Save my corrections',exact:true}).click();
  await page.getByRole('checkbox',{name:/I reviewed the person/}).check();
  await page.getByRole('button',{name:'Confirm Outfit Details',exact:true}).click();
  await expect(page.getByText('Outfit details confirmed. You can now describe the occasion.',{exact:true})).toBeVisible();
});

test("jersey, shorts and socks confirmation hides contracts and preserves original predictions",async({page})=>{
  await page.setViewportSize({width:390,height:844});await setup(page,"socks");await upload(page);
  await expect(page.getByText("Please confirm whether this is one garment or a pair.",{exact:true})).toBeVisible();
  await page.getByRole('article').filter({has:page.getByRole('heading',{name:/1\. Black and Red Jersey/})}).getByRole('button',{name:'Confirm this type',exact:true}).click();
  await page.getByRole('article').filter({has:page.getByRole('heading',{name:/1\. Black and Red Jersey/})}).getByRole('button',{name:'One garment',exact:true}).click();
  await page.getByLabel('Garment 3 clothing type',{exact:true}).selectOption('socks');
  await page.getByRole('article').filter({has:page.getByRole('heading',{name:/3\. White Socks/})}).getByRole('button',{name:'A visible pair',exact:true}).click();
  await page.getByLabel('What can you see around the feet?').selectOption('socks_only_visible');
  await page.getByRole('button',{name:'Save my corrections',exact:true}).click();
  await page.getByRole('checkbox',{name:/I reviewed the person/}).check();
  await page.getByRole('button',{name:'Confirm Outfit Details',exact:true}).click();
  await expect(page.getByText('Outfit details confirmed. You can now describe the occasion.',{exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  await expect(page.getByText('jersey:unresolved_identity',{exact:true})).not.toBeVisible();
});
