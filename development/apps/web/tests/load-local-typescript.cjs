// Load owned, pure TS modules and JSON fixtures without introducing a test bundler.
const fs=require('node:fs'),path=require('node:path');
const {stripTypeScriptTypes}=require('node:module');
const cache=new Map();
function moduleUrl(file){
  if(cache.has(file))return cache.get(file);
  let source;
  if(file.endsWith('.json'))source='export default '+fs.readFileSync(file,'utf8');
  else{
    source=fs.readFileSync(file,'utf8').replace(/^import type .*;\r?\n/gm,'');
    source=source.replace(/from\s+["'](\.\.?\/[^"']+)["']/g,(_,specifier)=>{
      let dependency=path.resolve(path.dirname(file),specifier);
      if(!path.extname(dependency))dependency+='.ts';
      return 'from '+JSON.stringify(moduleUrl(dependency));
    });
    source=stripTypeScriptTypes(source);
  }
  const url='data:text/javascript;base64,'+Buffer.from(source).toString('base64');cache.set(file,url);return url;
}
exports.loadTs=file=>import(moduleUrl(file));
