import assert from 'node:assert/strict';
import test from 'node:test';

import { waitForLegacyPages } from './wait-for-legacy-pages.mjs';

const SHA = 'a'.repeat(40);

function response(workflowRuns, { ok = true, status = 200 } = {}) {
  return {
    ok,
    status,
    async json() {
      return { workflow_runs: workflowRuns };
    },
  };
}

test('waits for the matching dynamic Pages run to complete', async () => {
  let time = 0;
  const replies = [
    response([{ id: 2, name: 'pages build and deployment', event: 'dynamic',
      head_sha: SHA, status: 'in_progress', conclusion: null }]),
    response([{ id: 2, name: 'pages build and deployment', event: 'dynamic',
      head_sha: SHA, status: 'completed', conclusion: 'success' }]),
  ];
  const result = await waitForLegacyPages({
    token: 'test-token',
    repository: 'owner/repo',
    commitSha: SHA,
    fetchImpl: async () => replies.shift(),
    sleep: async (milliseconds) => { time += milliseconds; },
    now: () => time,
  });
  assert.deepEqual(result, { found: true, conclusion: 'success' });
});

test('continues when no matching legacy run appears in the discovery window', async () => {
  let time = 0;
  const result = await waitForLegacyPages({
    token: 'test-token',
    repository: 'owner/repo',
    commitSha: SHA,
    fetchImpl: async () => response([
      { id: 1, name: 'pages build and deployment', event: 'dynamic',
        head_sha: 'b'.repeat(40), status: 'completed', conclusion: 'success' },
    ]),
    sleep: async (milliseconds) => { time += milliseconds; },
    now: () => time,
    discoveryMilliseconds: 10,
    pollMilliseconds: 10,
  });
  assert.deepEqual(result, { found: false, conclusion: null });
});

test('fails closed when the Actions lookup is unavailable', async () => {
  await assert.rejects(
    waitForLegacyPages({
      token: 'test-token',
      repository: 'owner/repo',
      commitSha: SHA,
      fetchImpl: async () => response([], { ok: false, status: 403 }),
    }),
    /HTTP 403/,
  );
});

test('retries transient Actions failures inside the polling budget', async () => {
  let time = 0;
  const replies = [
    response([], { ok: false, status: 503 }),
    response([{ id: 3, name: 'pages build and deployment', event: 'dynamic',
      head_sha: SHA, status: 'completed', conclusion: 'success' }]),
  ];
  const result = await waitForLegacyPages({
    token: 'test-token',
    repository: 'owner/repo',
    commitSha: SHA,
    fetchImpl: async () => replies.shift(),
    sleep: async (milliseconds) => { time += milliseconds; },
    now: () => time,
  });
  assert.deepEqual(result, { found: true, conclusion: 'success' });
});

test('fails closed on a malformed successful Actions response', async () => {
  await assert.rejects(
    waitForLegacyPages({
      token: 'test-token',
      repository: 'owner/repo',
      commitSha: SHA,
      fetchImpl: async () => ({ ok: true, status: 200, json: async () => ({}) }),
    }),
    /invalid Actions payload/,
  );
});
