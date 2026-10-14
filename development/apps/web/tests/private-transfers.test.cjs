const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {stripTypeScriptTypes} = require('node:module');
let adapter;
test.before(async () => {
  const source = fs.readFileSync(path.join(__dirname, '../src/lib/api/private-transfers.ts'), 'utf8');
  adapter = await import('data:text/javascript;base64,' + Buffer.from(stripTypeScriptTypes(source)).toString('base64'));
});
test('large bytes go directly to storage; concurrent submission shares one ticket', async () => {
  const original = global.fetch, calls = [];
  const file = new File([new Uint8Array(5 * 1024 * 1024)], 'demo.webm', {type:'video/webm'});
  global.fetch = async (url, options={}) => {
    calls.push({url, options});
    if (url.endsWith('/configuration')) return Response.json({direct_upload:true});
    if (url.endsWith('/csrf')) return Response.json({csrf:'synthetic-csrf'});
    if (url.endsWith('/authorize')) {
      const body = JSON.parse(options.body); assert.equal(body.byte_size, file.size); assert.match(body.sha256, /^[0-9a-f]{64}$/);
      return Response.json({ticket:'synthetic-ticket',upload_url:'https://storage.example.test/storage/v1/object/upload/sign/private/staged-uploads/test?token=synthetic',storage_origin:'https://storage.example.test',expires_in:7200});
    }
    if (options.method === 'PUT') { assert.equal(options.body,file); assert.equal(options.credentials,'omit'); assert.equal(options.redirect,'error'); return Response.json({}); }
    if (url.endsWith('/complete')) { assert.deepEqual(JSON.parse(options.body),{ticket:'synthetic-ticket'}); return Response.json({upload_id:'one-upload'}); }
    throw Error('Unexpected request');
  };
  try {
    const results=await Promise.all([adapter.uploadPrivateFile(file,{purpose:'resource'}),adapter.uploadPrivateFile(file,{purpose:'resource'})]);
    assert.deepEqual(results,[{upload_id:'one-upload'},{upload_id:'one-upload'}]);
    assert.equal(calls.filter(c=>c.options.method==='PUT').length,1);
    assert.equal(calls.filter(c=>c.url.endsWith('/authorize')).length,1);
    assert(calls.filter(c=>c.url.startsWith('/api/')).every(c=>!c.options.body || typeof c.options.body==='string' && c.options.body.length<3000));
  } finally { global.fetch=original; }
});
test('uncertain finalization retries the same ticket without resending file bytes',async()=>{
  const original=global.fetch;let uploads=0,finishes=0,authorizations=0;
  const file=new File(['synthetic'],'tiny.png',{type:'image/png'});
  global.fetch=async(url,options={})=>{
    if(url.endsWith('/configuration'))return Response.json({direct_upload:true});
    if(url.endsWith('/csrf'))return Response.json({csrf:'synthetic'});
    if(url.endsWith('/authorize')){authorizations++;return Response.json({ticket:'retained-ticket',upload_url:'https://storage.example.test/storage/v1/object/upload/sign/private/staged-uploads/retry?token=synthetic',storage_origin:'https://storage.example.test',expires_in:7200});}
    if(options.method==='PUT'){uploads++;return Response.json({});}
    if(url.endsWith('/complete')){finishes++;assert.equal(JSON.parse(options.body).ticket,'retained-ticket');if(finishes===1)throw new TypeError('Connection lost');return Response.json({upload_id:'same-upload'});}
  };
  try{await assert.rejects(adapter.uploadPrivateFile(file,{purpose:'resource'}),/Connection lost/);assert.deepEqual(await adapter.uploadPrivateFile(file,{purpose:'resource'}),{upload_id:'same-upload'});assert.equal(uploads,1);assert.equal(authorizations,1);assert.equal(finishes,2);}finally{global.fetch=original;}
});
test('expired upload URL gets fresh authorization on retry', async () => {
  const original = global.fetch; let permits = 0, uploads = 0;
  const file = new File(['synthetic'], 'tiny.png', {type: 'image/png'});
  global.fetch = async (url, options = {}) => {
    if (url.endsWith('/configuration')) return Response.json({direct_upload:true});
    if (url.endsWith('/csrf')) return Response.json({csrf:'synthetic'});
    if (url.endsWith('/authorize')) {
      permits++;
      return Response.json({ticket:'ticket-' + permits,upload_url:'https://storage.example.test/storage/v1/object/upload/sign/private/staged-uploads/retry?token=synthetic',storage_origin:'https://storage.example.test',expires_in:7200});
    }
    if (options.method === 'PUT') return ++uploads === 1 ? Response.json({}, {status:403}) : Response.json({});
    if (url.endsWith('/complete')) return Response.json({upload_id:'fresh-upload'});
    throw Error('Unexpected request');
  };
  try {
    await assert.rejects(adapter.uploadPrivateFile(file,{purpose:'resource'}), /Private storage/);
    assert.deepEqual(await adapter.uploadPrivateFile(file,{purpose:'resource'}),{upload_id:'fresh-upload'});
    assert.equal(permits,2);
  } finally { global.fetch = original; }
});
test('foreign storage URL is rejected before sending file bytes', async () => {
  const original = global.fetch;
  global.fetch = async (url, options = {}) => {
    assert.notEqual(options.method, 'PUT');
    if (url.endsWith('/configuration')) return Response.json({direct_upload:true});
    if (url.endsWith('/csrf')) return Response.json({csrf:'synthetic'});
    return Response.json({ticket:'synthetic',upload_url:'https://foreign.example.test/storage/v1/object/upload/sign/private/file',storage_origin:'https://storage.example.test',expires_in:7200});
  };
  try {
    await assert.rejects(adapter.uploadPrivateFile(new File(['data'],'tiny.png',{type:'image/png'}),{purpose:'resource'}), /invalid transfer address/);
  } finally { global.fetch = original; }
});
