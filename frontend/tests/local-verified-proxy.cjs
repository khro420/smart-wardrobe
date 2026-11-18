// Local transport regression. No main backend, account or wardrobe is called.
const path=require('node:path'),http=require('node:http'),url=require('node:url');
const assert=require('node:assert/strict'),crypto=require('node:crypto'),fs=require('node:fs');
const root=path.resolve(__dirname,'..');
const {transpileConfig}=require(path.join(root,'node_modules/next/dist/build/next-config-ts/transpile-config'));
const {proxyRequest}=require(path.join(root,'node_modules/next/dist/server/lib/router-utils/proxy-request'));
const {PHASE_DEVELOPMENT_SERVER:DEV,PHASE_PRODUCTION_SERVER:PROD}=require(path.join(root,'node_modules/next/constants'));
const key='SMART_WARDROBE_LOCAL_PROXY_PROFILE';
const listen=s=>new Promise(resolve=>s.listen(0,'127.0.0.1',()=>resolve(s.address().port)));
const close=s=>new Promise(resolve=>{s.closeAllConnections?.();s.close(resolve);});
(async()=>{
 const compiled=await transpileConfig({nextConfigPath:path.join(root,'next.config.ts'),dir:root});const config=compiled.default;
 process.env[key]='disabled';process.env.SMART_WARDROBE_BACKEND_URL='http://127.0.0.1:8000';
 const normal=config(DEV);assert.equal(normal.experimental?.proxyTimeout,undefined);
 process.env[key]='verified_mixed_v1';const local=config(DEV);assert.equal(local.experimental.proxyTimeout,300000);
 const production=config(PROD);assert.equal(production.experimental?.proxyTimeout,undefined);
 process.env.SMART_WARDROBE_BACKEND_URL='https://example.invalid';
 assert.throws(()=>config(DEV),/loopback backend/);
 process.env.SMART_WARDROBE_BACKEND_URL='http://127.0.0.1:8000';
 const payload=Buffer.from(JSON.stringify({kind:'transport_fixture_not_a_recommendation',body:'x'.repeat(1024*1024)}));
 let authenticated=0;const servers=[];
 const upstream=http.createServer((req,res)=>{let body='';req.on('data',x=>body+=x);req.on('end',()=>{
  if(req.headers.authorization==='Bearer transport-test-only'&&JSON.parse(body).submission_key==='fixed-test-receipt')authenticated++;
  setTimeout(()=>{if(!res.destroyed){res.writeHead(201,{'content-type':'application/json'});res.end(payload);}},31000);
 });});servers.push(upstream);const port=await listen(upstream);
 async function measure(timeout){
  const proxy=http.createServer((req,res)=>{proxyRequest(req,res,url.parse('http://127.0.0.1:'+port+req.url,true),undefined,undefined,timeout).catch(()=>{});});servers.push(proxy);
  const proxyPort=await listen(proxy),start=performance.now();
  const r=await fetch('http://127.0.0.1:'+proxyPort+'/api/v1/recommendations?pipeline=integrated',{method:'POST',headers:{'content-type':'application/json','authorization':'Bearer transport-test-only'},body:JSON.stringify({submission_key:'fixed-test-receipt'})});
  const bytes=Buffer.from(await r.arrayBuffer());return {status:r.status,seconds:(performance.now()-start)/1000,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length};
 }
 try{
  const [oldResponse,newResponse]=await Promise.all([measure(undefined),measure(local.experimental.proxyTimeout)]);
  assert.equal(oldResponse.status,500);assert.equal(newResponse.status,201);assert.equal(newResponse.bytes,payload.length);assert.equal(newResponse.sha256,crypto.createHash('sha256').update(payload).digest('hex'));assert.equal(authenticated,2);
  const result={result:'PASS',default_development_ms:30000,opt_in_development_ms:local.experimental.proxyTimeout,production_default_unchanged:true,remote_profile_refused:true,dummy_auth_and_receipt_preserved:true,old_response:oldResponse,new_response:newResponse};
  if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{await Promise.all(servers.reverse().map(close));}
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
