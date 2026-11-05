import assert from 'node:assert/strict';
import test from 'node:test';

import { waitForPagesArtifact } from './wait-for-pages-artifact.mjs';

function response(artifacts, { ok = true, status = 200 } = {}) {
  return { ok, status, async json() { return { artifacts }; } };
}

test('waits until the Pages artifact is visible', async () => {
  let time = 0;
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
  });
  assert.deepEqual(result, { id: 42 });
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
});
