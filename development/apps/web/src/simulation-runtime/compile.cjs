const {parentPort,workerData}=require('node:worker_threads');
const {compileSimulation}=require('../lib/simulations/compiler.cjs');
compileSimulation(workerData.engine,workerData.source).then(worker=>parentPort.postMessage({worker}),()=>parentPort.postMessage({error:true})).finally(()=>require('esbuild').stop());
