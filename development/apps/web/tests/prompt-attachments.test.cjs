const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { stripTypeScriptTypes } = require('node:module');
let validateAttachments, MAX_FILE_BYTES;
test.before(async () => {
 const code = stripTypeScriptTypes(fs.readFileSync(path.join(__dirname, '../src/features/learning/prompt-attachments.ts'), 'utf8'));
 ({ validateAttachments, MAX_FILE_BYTES } = await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64')));
});
const file = (name, size=10, type='text/plain') => new File([new Uint8Array(size)], name, {type,lastModified:123});
test('file validation rejects empty, unsupported, mismatched and oversize files',()=>{
 const result=validateAttachments([], [file('empty.txt',0),file('program.exe'),file('picture.png',10,'text/html'),file('huge.txt',MAX_FILE_BYTES+1)]);
 assert.equal(result.accepted.length,0);assert.equal(result.errors.length,4);
});
test('mixed batches retain valid files; duplicate and count limits preserve existing attachments',()=>{
 const existing=[{id:'1',kind:'file',file:file('a.txt')}];const snapshot=existing.slice();
 const result=validateAttachments(existing,[file('a.txt'),file('b.txt'),file('c.txt'),file('d.txt'),file('e.txt'),file('f.txt')]);
 assert.deepEqual(result.accepted.map(f=>f.name),['b.txt','c.txt','d.txt','e.txt']);assert.equal(result.errors.length,2);assert.deepEqual(existing,snapshot);
});
test('total size and recorded audio MIME are handled',()=>{
 const result=validateAttachments([], [file('a.txt',MAX_FILE_BYTES),file('b.txt',MAX_FILE_BYTES),file('c.txt',MAX_FILE_BYTES)]);
 assert.equal(result.accepted.length,2);assert.equal(result.errors.length,1);
 assert.equal(validateAttachments([], [file('voice.webm',20,'audio/webm;codecs=opus')]).accepted.length,1);
});
