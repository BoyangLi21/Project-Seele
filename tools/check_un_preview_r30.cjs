// Run only after the native client exits, so the two GPU jobs do not compete.
const fs=require('fs'),path=require('path'),{pathToFileURL}=require('url');
const root=path.resolve(__dirname,'..');
const {chromium}=require(path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const folder=path.join(root,'artifacts/facility_r30/models/delivery');
 const browser=await chromium.launch({channel:'chrome',headless:true,args:['--allow-file-access-from-files','--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:1400,height:1050}});const errors=[],requests=[];
 page.on('pageerror',e=>errors.push(String(e)));page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url());});
 await page.goto(pathToFileURL(path.join(folder,'preview.html')).href,{waitUntil:'commit',timeout:60000});console.log('Offline document opened');
 await page.waitForSelector('[data-preview-state]',{timeout:120000});console.log('Viewer initialized');
 const panels=page.locator('[data-preview-state]');
 for(let i=0;i<await panels.count();i++){
   await panels.nth(i).scrollIntoViewIfNeeded();
   await page.waitForFunction(n=>document.querySelectorAll('[data-preview-state]')[n].dataset.previewState==='ready',i,{timeout:60000});console.log('Viewport ready',i);
 }
 const views=page.locator('[data-preview-state="ready"]');const count=await views.count();
 const scene=page.locator('#scene-section [data-preview-state="ready"]');await scene.scrollIntoViewIfNeeded();
 const box=await scene.boundingBox();if(!box)throw new Error('No scene viewport');
 await page.screenshot({path:path.join(folder,'preview_scene_before.png')});
 const before=Number(await scene.getAttribute('data-interactions')||0);await page.mouse.move(box.x+box.width*.45,box.y+box.height*.5);await page.mouse.down();await page.mouse.move(box.x+box.width*.65,box.y+box.height*.62,{steps:15});await page.mouse.up();await page.mouse.wheel(0,-180);
 await page.waitForFunction(n=>Number(document.querySelector('#scene-section [data-preview-state="ready"]').dataset.interactions)>n,before,{timeout:10000});
 await page.screenshot({path:path.join(folder,'preview_scene_rotated.png')});
 const after=Number(await scene.getAttribute('data-interactions'));const result={passed:count===3&&after>before&&errors.length===0&&requests.length===0,loaded_viewports:count,scene_interactions_before:before,scene_interactions_after:after,page_errors:errors,network_requests:requests,scope:'Real offline GLB loading, orbit drag and wheel zoom in an isolated headless Chromium. Source cards are explicitly the original Lux bases; the scene is the final edited pair.'};
 fs.writeFileSync(path.join(folder,'preview_check.json'),JSON.stringify(result,null,2));await browser.close();console.log(JSON.stringify(result));if(!result.passed)process.exitCode=1;
})().catch(e=>{console.error(e);process.exit(1)});
