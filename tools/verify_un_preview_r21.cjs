const path=require('path'),os=require('os'),crypto=require('crypto');
let playwright;try{playwright=require('playwright')}catch{playwright=require(path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'))}
const {chromium}=playwright;const output=path.resolve(__dirname,'../artifacts/un_models_r21/delivery');
const fs=require('fs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true,args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:1440,height:960}});const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.goto(require('url').pathToFileURL(path.join(output,'preview.html')).href,{waitUntil:'domcontentloaded',timeout:120000});
 const stages=page.locator('[data-preview-state]');await stages.first().waitFor();
 const rows=[];
 for(let i=0;i<await stages.count();i++){
  const stage=stages.nth(i);await stage.scrollIntoViewIfNeeded();
  await page.waitForFunction(i=>document.querySelectorAll('[data-preview-state]')[i].dataset.previewState==='ready',i,{timeout:60000});
  const before=Number(await stage.getAttribute('data-interactions')||0),b=await stage.boundingBox();
  await page.mouse.move(b.x+b.width*.45,b.y+b.height*.45);await page.mouse.down();await page.mouse.move(b.x+b.width*.62,b.y+b.height*.58,{steps:12});await page.mouse.up();await page.mouse.wheel(0,-160);
  await page.waitForFunction(({i,before})=>Number(document.querySelectorAll('[data-preview-state]')[i].dataset.interactions)>before,{i,before},{timeout:5000});
  rows.push({index:i,state:await stage.getAttribute('data-preview-state'),interactionEvents:Number(await stage.getAttribute('data-interactions'))-before});
 }
 await page.locator('#scene-section').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(output,'verified_preview.png')});
 if(errors.length||rows.length!==3)throw Error(JSON.stringify({errors,rows}));
 fs.writeFileSync(path.join(output,'browser_validation.json'),JSON.stringify({passed:true,headless:true,rotationAndZoom:true,previews:rows,errors,htmlSha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(output,'preview.html'))).digest('hex')},null,2));
 await browser.close();console.log(JSON.stringify(rows));
})().catch(e=>{console.error(e);process.exit(1)});
