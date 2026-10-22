import assert from 'node:assert/strict'
import test from 'node:test'

import { findAppAssets, verifyDeployment, verifyWithRetry } from './verify-pages.mjs'

const appHtml = `<!doctype html><html><head>
  <title>DifficultAI - Voice Training Demo</title>
  <script type="module" src="/difficultai/assets/index-abc123.js"></script>
  <link rel="stylesheet" href="/difficultai/assets/index-def456.css">
</head></html>`

test('rejects a successful documentation deployment', () => {
  assert.throws(
    () => findAppAssets('<title>Difficult AI | difficultai</title>', 'https://example.test/difficultai/'),
    /not the DifficultAI owner-pilot app/,
  )
})

test('verifies the app marker and same-origin versioned assets', async () => {
  const requested = []
  const fetchImpl = async (input) => {
    const url = input instanceof URL ? input.href : input
    requested.push(url)
    const contentType = url.endsWith('.css') ? 'text/css' : 'application/javascript'
    return {
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': contentType }),
      text: async () => appHtml,
    }
  }

  const assets = await verifyDeployment('https://example.test/difficultai/', fetchImpl, '123')
  assert.deepEqual(assets, [
    'https://example.test/difficultai/assets/index-abc123.js',
    'https://example.test/difficultai/assets/index-def456.css',
  ])
  assert.deepEqual(requested, [
    'https://example.test/difficultai/?repo-rescue-verify=123',
    ...assets,
  ])
})

test('fails when a referenced app asset is unavailable', async () => {
  const fetchImpl = async (input) => {
    const url = input instanceof URL ? input.href : input
    if (url.endsWith('.css')) return { ok: false, status: 404 }
    return {
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/javascript' }),
      text: async () => appHtml,
    }
  }

  await assert.rejects(
    verifyDeployment('https://example.test/difficultai/', fetchImpl),
    /index-def456\.css returned HTTP 404/,
  )
})

test('rejects an HTML fallback returned for a missing asset', async () => {
  const fetchImpl = async (input) => {
    const url = input instanceof URL ? input.href : input
    if (url.endsWith('.css')) {
      return {
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'text/html; charset=utf-8' }),
      }
    }
    return {
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/javascript' }),
      text: async () => appHtml,
    }
  }

  await assert.rejects(
    verifyDeployment('https://example.test/difficultai/', fetchImpl),
    /index-def456\.css served unexpected content-type text\/html/,
  )
})

test('retries a stale documentation page and accepts the propagated app', async () => {
  let pageRequests = 0
  const fetchImpl = async (input) => {
    const url = input instanceof URL ? input.href : input
    if (url.includes('repo-rescue-verify')) {
      pageRequests += 1
      return {
        ok: true,
        status: 200,
        text: async () => pageRequests === 1
          ? '<title>Difficult AI | difficultai</title>'
          : appHtml,
      }
    }
    const contentType = url.endsWith('.css') ? 'text/css' : 'application/javascript'
    return {
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': contentType }),
    }
  }

  const assets = await verifyWithRetry('https://example.test/difficultai/', {
    attempts: 2,
    delayMs: 0,
    fetchImpl,
    cacheBust: () => pageRequests + 1,
  })
  assert.equal(pageRequests, 2)
  assert.equal(assets.length, 2)
})
