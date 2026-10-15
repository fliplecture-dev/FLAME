const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { loadTs } = require('./load-local-typescript.cjs');
const modulePath = path.resolve(__dirname, '../src/lib/simulations/request.ts');
const ready = { status: 'ready', version: 1, engine: 'matter', title: 'Gravity', description: 'Explore gravity', source: 'export default () => ({})' };

test('pending source is polled until ready; only the initial fresh request may start generation', async () => {
  const { requestSimulation } = await loadTs(modulePath);
  const starts = [];
  const result = await requestSimulation(async start => {
    starts.push(start);
    return starts.length < 3 ? { status: 'pending' } : ready;
  }, true, 1000, 1);
  assert.deepEqual(starts, [true, false, false]);
  assert.equal(result.status, 'ready');
  assert.equal(result.spec.engine, 'matter');
  assert.equal(result.spec.source, ready.source);
  assert.equal('status' in result.spec, false);
});

test('restored history and explicit checks retrieve jobs without generating new source', async () => {
  const { requestSimulation } = await loadTs(modulePath);
  const starts = [];
  const result = await requestSimulation(async start => {
    starts.push(start);
    return starts.length === 1 ? { status: 'pending' } : ready;
  }, false, 1000, 1);
  assert.equal(result.status, 'ready');
  assert.deepEqual(starts, [false, false]);
});

test('deadline aborts a hanging network request and permits checking the completed job later', async () => {
  const { requestSimulation } = await loadTs(modulePath);
  let signal;
  await assert.rejects(requestSimulation(async (_, value) => {
    signal = value;
    return new Promise(() => {});
  }, true, 15, 1), /simulation_timeout/);
  assert.equal(signal.aborted, true);
  const result = await requestSimulation(async start => {
    assert.equal(start, false);
    return ready;
  }, false);
  assert.equal(result.status, 'ready');
});

test('pending forever terminates at the deadline; terminal and malformed results do not poll', async () => {
  const { requestSimulation } = await loadTs(modulePath);
  await assert.rejects(requestSimulation(async () => ({ status: 'pending' }), true, 15, 1), /simulation_timeout/);
  for (const value of [{ status: 'expired' }, { status: 'limited' }, { status: 'ineligible' }, { status: 'error' }, { status: 'ready', source: '' }, null]) {
    let calls = 0;
    const result = await requestSimulation(async () => { calls++; return value; }, true, 1000, 1);
    assert.equal(calls, 1);
    assert.equal(result.status, ['expired','limited','ineligible','error'].includes(value?.status) ? value.status : 'error');
  }
});

test('transport failures terminate instead of leaving a pending cached result', async () => {
  const { requestSimulation } = await loadTs(modulePath);
  await assert.rejects(requestSimulation(async () => { throw new Error('offline'); }, true), /offline/);
});
