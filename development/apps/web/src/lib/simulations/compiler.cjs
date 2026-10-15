// Trusted compiler only: generated code is input to esbuild, never evaluated in Node.
const esbuild = require('esbuild');
const fs = require('node:fs');
const path = require('node:path');
const engines = ['matter','three','r3f','phaser','rive','html5'];
const runtimeDir = path.resolve(process.cwd(), 'src/simulation-runtime');
async function compileSimulation(engine, source) {
  if (!engines.includes(engine) || typeof source !== 'string' || !source.trim() || source.length > 16000) throw Error('invalid_simulation');
  const allowed = {matter:['matter-js'],three:['three'],r3f:['react','react/jsx-runtime','three','@react-three/fiber'],phaser:[],rive:[],html5:[]}[engine];
  const result = await esbuild.build({
    stdin:{contents:`import mount from 'flame-generated';\n${fs.readFileSync(path.join(runtimeDir,'worker.js'),'utf8')}`,resolveDir:process.cwd(),sourcefile:'flame-bootstrap.js'},
    bundle:true,write:false,platform:'browser',format:'iife',target:'es2020',minify:true,
    define:{'process.env.NODE_ENV':'"production"',FLAME_ENGINE:JSON.stringify(engine)},
    logLevel:'silent',jsx:'automatic',
    plugins:[{name:'restricted-generated-module',setup(build){
      build.onResolve({filter:/^flame-generated$/},args=>args.namespace==='generated'?{errors:[{text:'Dependency not permitted'}]}:{path:'source',namespace:'generated'});
      build.onLoad({filter:/.*/,namespace:'generated'},()=>({contents:source,loader:'tsx',resolveDir:process.cwd()}));
      build.onResolve({filter:/.*/,namespace:'generated'},args=>{
        if(args.kind==='dynamic-import'||!allowed.includes(args.path))return {errors:[{text:'Dependency not permitted'}]};
        return {path:require.resolve(args.path)};
      });
      // R3F is only needed for its worker adapter, not every engine bundle.
      build.onResolve({filter:/^flame-fiber$/},()=>engine==='r3f'?{path:require.resolve('@react-three/fiber')}:{path:'empty-fiber',namespace:'empty'});
      build.onResolve({filter:/^flame-three$/},()=>['r3f','three'].includes(engine)?{path:require.resolve('three')}:{path:'empty-three',namespace:'empty'});
      build.onResolve({filter:/^flame-matter$/},()=>engine==='matter'?{path:require.resolve('matter-js')}:{path:'empty-matter',namespace:'empty'});
      build.onLoad({filter:/.*/,namespace:'empty'},()=>({contents:'export default null;export const createRoot=undefined,extend=undefined,advance=undefined,WebGLRenderer=undefined;'}));
    }}],
  });
  if(result.warnings.length || result.outputFiles[0].contents.length>4*1024*1024)throw Error('unsupported_source');
  return result.outputFiles[0].text;
}
async function trustedAdapter(engine) {
  if(engine==='phaser')return fs.readFileSync(path.join(process.cwd(),'node_modules/phaser/dist/phaser.min.js'),'utf8');
  if(engine==='rive')return fs.readFileSync(path.join(process.cwd(),'node_modules/@rive-app/canvas-lite/rive.js'),'utf8');
  return '';
}
module.exports={compileSimulation,trustedAdapter,runtimeDir};
