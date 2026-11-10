import {test,expect} from '@playwright/test';
import path from 'node:path';
const A='99cc52e8-473e-4192-b6d9-a6fa3227d45c',B='94f3e9af-86ce-48a1-b21d-c0612526dde3';
test.beforeEach(async({page})=>{
  if(process.env.SW_CATEGORY_RESTORED!=='yes') throw new Error('Admission browser writes require the owned restored-copy runner.');
  await page.addInitScript(({token,a})=>{sessionStorage.setItem('smart_wardrobe_access_token',token);if(!sessionStorage.getItem('smart_wardrobe_profile_id'))sessionStorage.setItem('smart_wardrobe_profile_id',a);},{token:process.env.SW_SETUP_TOKEN!,a:A});
});
test('restored demo: male/female admission starts at classification, without partial saving',async({page})=>{
  const rows=[{wearer:A,category:'vest_dress',ok:false},{wearer:A,category:'skirt',ok:false},{wearer:A,category:'long_sleeve_top',ok:true},{wearer:A,category:'trousers',ok:true},{wearer:B,category:'vest_dress',ok:true},{wearer:B,category:'skirt',ok:true},{wearer:B,category:'trousers',ok:true}];
  const results=[];
  await page.goto('/extract');
  for(const row of rows){
    await page.getByRole('combobox',{name:'Select active wardrobe profile'}).first().selectOption(row.wearer);
    await page.goto('/extract');
    await expect(page.getByTestId('wearer-category-guidance')).toContainText(row.wearer===A?'8 garment categories':'13 garment categories');
    const pending=page.waitForResponse(r=>r.url().includes('/processing/jobs?')&&r.request().method()==='POST');
    await page.getByLabel('Wardrobe image',{exact:true}).setInputFiles(path.join(process.env.SW_REVIEW_DIR!,'browser-inputs',row.category+'.png'));
    const created=await pending;expect(created.status()).toBe(202);const job=await created.json();
    await page.waitForURL('**/extract/results?job='+job.id);
    const response=await page.request.get('/api/v1/processing/jobs/'+job.id,{headers:{Authorization:'Bearer '+process.env.SW_SETUP_TOKEN!,'X-Wardrobe-Profile-Id':row.wearer}});expect(response.status()).toBe(200);
    const current=await response.json();expect(current.status).toBe(row.ok?'completed':'review_required');
    expect(current.items[0].wearer_category_eligibility.usable).toBe(row.ok);
    if(!row.ok){await expect(page.getByText('Garments have not been added yet',{exact:true})).toBeVisible();await expect(page.getByText(/selected wearer policy prevents saving this batch/)).toBeVisible();}
    results.push({wearer:row.wearer,category:row.category,expected_saved:row.ok,job_id:job.id,status:current.status});
  }
  await page.screenshot({path:path.join(process.env.SW_REVIEW_DIR!,'restored-admission-browser.png'),fullPage:true});
  test.info().attach('actual admission outcomes',{body:JSON.stringify(results,null,2),contentType:'application/json'});
});
