import assert from 'node:assert/strict';
import test from 'node:test';

import { waitForPagesArtifact } from './wait-for-pages-artifact.mjs';

function response(artifacts, { ok = true, status = 200 } = {}) {
  return { ok, status, async json() { return { artifacts }; } };
}

test('waits until the Pages artifact is visible', async () => {
  let time = 0;
  const abortBudgets = [];
  const replies = [
    response([]),
    response([{ id: 42, name: 'github-pages', expired: false }]),
  ];
  const result = await waitForPagesArtifact({
    token: 'test-token',
    repository: 'owner/repo',
    runId: '123',
    fetchImpl: async () => replies.shift(),
    sleep: async (milliseconds) => { time += milliseconds; },
    now: () => time,
    abortAfter: (milliseconds) => {
      abortBudgets.push(milliseconds);
      return new AbortController().signal;
    },
  });
  assert.deepEqual(result, { id: 42 });
  assert.deepEqual(abortBudgets, [60_000, 58_000]);
});

test('ignores expired and unrelated artifacts', async () => {
  let time = 0;
  await assert.rejects(
    waitForPagesArtifact({
      token: 'test-token',
      repository: 'owner/repo',
      runId: '123',
      fetchImpl: async () => response([
        { id: 1, name: 'github-pages', expired: true },
        { id: 2, name: 'other', expired: false },
      ]),
      sleep: async (milliseconds) => { time += milliseconds; },
      now: () => time,
      timeoutMilliseconds: 10,
      pollMilliseconds: 10,
    }),
    /not visible within 10ms/,
  );
});

test('retries transient API failures', async () => {
  let time = 0;
  const replies = [
    response([], { ok: false, status: 503 }),
    response([{ id: 7, name: 'github-pages', expired: false }]),
  ];
  const result = await waitForPagesArtifact({
    token: 'test-token',
    repository: 'owner/repo',
    runId: '123',
    fetchImpl: async () => replies.shift(),
    sleep: async (milliseconds) => { time += milliseconds; },
    now: () => time,
  });
  assert.deepEqual(result, { id: 7 });
});

test('fails closed on permanent or malformed responses', async () => {
  const common = { token: 'test-token', repository: 'owner/repo', runId: '123' };
  await assert.rejects(
    waitForPagesArtifact({
      ...common,
      fetchImpl: async () => response([], { ok: false, status: 403 }),
    }),
    /HTTP 403/,
  );
  await assert.rejects(
    waitForPagesArtifact({
      ...common,
      fetchImpl: async () => ({ ok: true, status: 200, json: async () => ({}) }),
    }),
    /invalid Actions payload/,
  );
  await assert.rejects(
    waitForPagesArtifact({
      ...common,
      fetchImpl: async () => ({
        ok: true,
        status: 200,
        json: async () => { throw new SyntaxError('private intermediary detail'); },
      }),
    }),
    /^Error: Pages artifact lookup returned malformed JSON$/,
  );
});

test('bounds a stalled request and sanitizes request failures', async () => {
  const controller = new AbortController();
  const request = waitForPagesArtifact({
    token: 'test-token',
    repository: 'owner/repo',
    runId: '123',
    abortAfter: () => controller.signal,
    fetchImpl: async (_endpoint, { signal }) => new Promise((_resolve, reject) => {
      signal.addEventListener('abort', () => reject(new Error('private network detail')));
    }),
    timeoutMilliseconds: 25,
  });
  controller.abort();
  await assert.rejects(request, /not visible within 25ms/);

  await assert.rejects(
    waitForPagesArtifact({
      token: 'test-token',
      repository: 'owner/repo',
      runId: '123',
      fetchImpl: async () => { throw new Error('private network detail'); },
    }),
    /^Error: Pages artifact lookup request failed$/,
  );
});
