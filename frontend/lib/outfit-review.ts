import { ApiError, getAccessToken } from "./api";

export type Fact = {state: "observed" | "uncertain" | "unknown"; values: string[]};
export type Box = {xyxy: [number,number,number,number]};
export type ReviewItem = {id:string; person_id:string; region:Box; category:string; category_alternatives:string[]; role:string; visibility:string; unit:string; colours:Fact; pattern:Fact; sleeve_length:Fact; sleeve_state:Fact;style?:Fact};
export type Prediction = {version:string; scene:string; people:{id:string;region:Box}[]; target_person_id:string|null; footwear_visibility:string;feet_observation?:string; items:ReviewItem[]; layering:{over:string;under:string;state:string}[]; identity_questions:{items:[string,string];relation:string}[]};
export type Feedback = {occasion:{original_text:string};feedback_source?:string;overall_assessment:string; facts:{item_id:string;text:string}[]; sections:{dimension:string;text:string;item_ids:string[]}[]; strengths:string[]; potential_improvements:string[];suggestions?:string[]; unknown_details:string[]; limitations:string[]; provenance:Record<string,string>; rubric:{message:string;score:number|null;dimensions:{name:string;weight_percent:number;score:number|null;explanation?:string;anchor?:string;status?:string}[]}};
export type ReviewView = {id:string; state:string; image:{width:number;height:number}; revision:string|null; generation:number; prediction:Prediction|null; original_prediction:Prediction|null;original_model_response?:string|null;normalization?:{version:string;changes:{path:string;before:string[];after:string[]}[]}|null; issues:string[]; confirmed:boolean; result:Feedback|null; error:{code:string;message:string}|null; raw_failed_proposal:string|null; privacy:string; expires_in_seconds:number};
export const CATEGORIES = ["unknown","top","shirt","t_shirt","jersey","sweater","jacket","coat","dress","skirt","shorts","trousers","jeans","footwear","socks"];
export const ROLES:Record<string,string> = {top:"upper",shirt:"upper",t_shirt:"upper",jersey:"upper",sweater:"upper",jacket:"outerwear",coat:"outerwear",dress:"one_piece",skirt:"lower",shorts:"lower",trousers:"lower",jeans:"lower",footwear:"footwear",socks:"hosiery",unknown:"unknown"};
export const FACTS:Record<string,string[]> = {colours:"black white grey blue navy teal green olive khaki brown tan beige red orange yellow pink purple multicoloured silver gold".split(" "),pattern:["plain","striped","checked","floral","graphic","patterned"],sleeve_length:["sleeveless","short","elbow","three_quarter","long"],sleeve_state:["rolled","not_rolled"],style:["casual","sporty","formal","smart_casual","classic","minimal","streetwear","vintage"]};
const base = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";
export async function reviewRequest<T>(path:string, init:RequestInit={}):Promise<T> {
  const token=getAccessToken(); if(!token) throw new Error("Sign in before using AI Outfit Review.");
  const headers=new Headers(init.headers); headers.set("Authorization",`Bearer ${token}`);
  const response=await fetch(`${base}/outfit-reviews${path}`,{...init,headers,cache:"no-store"});
  if(!response.ok){const body=await response.json().catch(()=>null); throw new ApiError(typeof body?.detail?.message==="string"?body.detail.message:typeof body?.detail==="string"?body.detail:"Outfit review could not be completed.",response.status);}
  return response.status===204?undefined as T:response.json();
}
export async function reviewPhoto(id:string, signal:AbortSignal) {
  const token=getAccessToken();
  if(!token) throw new Error("Sign in to view this private photo.");
  const response=await fetch(`${base}/outfit-reviews/${encodeURIComponent(id)}/photo`,{headers:{Authorization:`Bearer ${token}`},cache:"no-store",signal});
  if(!response.ok) throw new Error("The temporary photo is unavailable or expired.");
  return response.blob();
}
export const jsonAction=(method:string,body:unknown):RequestInit=>({method,headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
export function correctionChanges(before:Prediction,after:Prediction,reason:string,selectedTarget:string|null=null) {
  const changes:{operation:string;subject:string;reason:string}[]=[];
  const same=(a:unknown,b:unknown)=>JSON.stringify(a)===JSON.stringify(b);
  const ids=new Set([...before.items,...after.items].map(i=>i.id));
  for(const id of ids){const a=before.items.filter(i=>i.id===id),b=after.items.filter(i=>i.id===id);if(!same(a,b))changes.push({operation:a.length&&b.length?"replace_item":a.length?"remove_item":"add_item",subject:id,reason});}
  if(selectedTarget||!same([before.scene,before.people,before.target_person_id],[after.scene,after.people,after.target_person_id]))changes.push({operation:"select_target",subject:"scene",reason});
  if(!same([before.layering,before.identity_questions,before.footwear_visibility,before.feet_observation],[after.layering,after.identity_questions,after.footwear_visibility,after.feet_observation]))changes.push({operation:"review_relations",subject:"scene",reason});
  return changes;
}

export const pretty=(value:string)=>value.replaceAll("_"," ").replace(/^./,v=>v.toUpperCase());
export const categoryLabel=(value:string)=>value==="footwear"?"Shoes / footwear":value==="unknown"?"Not sure":pretty(value);
export function itemLabel(item:ReviewItem){return `${item.colours.state==="observed"?item.colours.values.map(pretty).join(" and ")+" ":""}${categoryLabel(item.category)}`;}
export function issueMessage(issue:string){
  const code=issue.split(":").at(-1)??issue;
  const messages:Record<string,string>={unresolved_identity:"Please confirm whether this is one garment or a pair.",invalid_category_alternatives:"The AI gave conflicting clothing types. Choose a type or keep it Unknown.",category_role_conflict:"Confirm the clothing type so its wearing position can be recorded correctly.",not_an_observed_item:"Keep only clothing that is visibly present; remove this item if it cannot be seen.",footwear_visibility_conflict:"Please confirm what is visible around the feet; socks are not shoes.",feet_observation_conflict:"The feet description conflicts with the listed socks or shoes. Correct the item or feet description.",visible_socks_missing:"Add the visible socks to the inventory, or correct the feet description.",socks_pair_confirmation_required:"Please confirm whether these are a pair of socks.",socks_pair_grouping_required:"Review the sock records. Group a visible pair or remove a duplicate.",footwear_pair_grouping_required:"Review the shoe records. Group a visible pair or remove a duplicate.",region_outside_person:"Adjust the garment highlight or the selected person's visible region.",wrong_person:"Remove clothing belonging to another person, or choose the correct person.",sleeve_not_applicable:"Sleeve details do not apply to this clothing type. Clear those details explicitly.",invalid_pair:"Please confirm this garment as a single item, not a footwear pair.",duplicate_id:"The AI repeated an item identity. Keep the correct record and remove the duplicate.",same_region_identity_review:"Two records use the same highlight. Remove a duplicate or adjust the highlights for real layers.",identity_review_required:"Review whether the questioned records are genuinely separate garments.",invalid_identity_reference:"Dismiss the outdated identity question after reviewing the actual garments.",invalid_layer_reference:"A layering relationship refers to a removed item. Correct or remove that relationship.",cyclic_layers:"The layers contradict each other. Correct which garment is worn over the other.",user_target_selection_required:"Select and save the intended person, even if the AI preselected someone.",target_selection_required:"Select the person whose outfit you want to review.",person_count_conflict:"Review the person selection or use a clearer single-person photo.",no_person_inventory_conflict:"The AI scene and inventory conflict. Select a visible person or use a clearer photograph.",no_reviewable_outfit:"Select a visible person and include at least one visible garment."};
  return messages[code]??"Review this observation before confirming your outfit.";
}
