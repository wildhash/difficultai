import { pathToFileURL } from 'node:url'

const EXPECTED_TITLE = '<title>DifficultAI - Voice Training Demo</title>'

export function findAppAssets(html, pageUrl) {
  if (!html.includes(EXPECTED_TITLE)) {
    throw new Error('deployed page is not the DifficultAI owner-pilot app')
  }

  const references = [
    ...html.matchAll(/<script\b[^>]*\bsrc=["']([^"']+)["']/gi),
    ...html.matchAll(/<link\b[^>]*\bhref=["']([^"']+)["']/gi),
  ].map((match) => new URL(match[1], pageUrl))

  const pageOrigin = new URL(pageUrl).origin
  const assets = references.filter(
    (url) => url.origin === pageOrigin && /\/assets\/[^/]+\.(?:css|js)$/.test(url.pathname),
  )
  const extensions = new Set(assets.map((url) => url.pathname.split('.').pop()))

  if (!extensions.has('js') || !extensions.has('css')) {
    throw new Error('deployed app is missing its versioned JavaScript or CSS asset')
  }
  return [...new Map(assets.map((url) => [url.href, url])).values()]
}

export async function verifyDeployment(pageUrl, fetchImpl = fetch, cacheBust = Date.now()) {
  const verificationUrl = new URL(pageUrl)
  verificationUrl.searchParams.set('repo-rescue-verify', String(cacheBust))
  const page = await fetchImpl(verificationUrl, {
    cache: 'no-store',
    signal: AbortSignal.timeout(15_000),
  })
  if (!page.ok) throw new Error(`page returned HTTP ${page.status}`)

  const assets = findAppAssets(await page.text(), pageUrl)
  for (const asset of assets) {
    const response = await fetchImpl(asset, {
      cache: 'no-store',
      signal: AbortSignal.timeout(15_000),
    })
    if (!response.ok) {
      throw new Error(`${asset.pathname} returned HTTP ${response.status}`)
    }
    const contentType = response.headers?.get?.('content-type') ?? ''
    const validType = asset.pathname.endsWith('.css')
      ? /^text\/css(?:;|$)/i.test(contentType)
      : /(?:java|ecma)script/i.test(contentType)
    if (!validType) {
      throw new Error(
        `${asset.pathname} served unexpected content-type ${contentType || '(missing)'}`,
      )
    }
  }
  return assets.map((asset) => asset.href)
}

export async function verifyWithRetry(pageUrl, options = {}) {
  const {
    attempts = 6,
    delayMs = 10_000,
    fetchImpl = fetch,
    cacheBust = () => Date.now(),
    onRetry = () => {},
  } = options

  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      return await verifyDeployment(pageUrl, fetchImpl, cacheBust())
    } catch (error) {
      if (attempt === attempts) throw error
      onRetry(error, attempt)
      await new Promise((resolve) => setTimeout(resolve, delayMs))
    }
  }
  throw new Error('deployment verification exhausted without a result')
}

const isMain = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href
if (isMain) {
  const pageUrl = process.argv[2]
  if (!pageUrl) {
    console.error('usage: npm run verify:deployment -- <page-url>')
    process.exitCode = 2
  } else {
    const assets = await verifyWithRetry(pageUrl, {
      onRetry: (error, attempt) => {
        console.log(`verification attempt ${attempt} failed: ${error.message}; retrying`)
      },
    })
    console.log(`verified owner-pilot app and ${assets.length} assets at ${pageUrl}`)
  }
}
