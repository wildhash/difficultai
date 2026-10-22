import { pathToFileURL } from 'node:url'

const EXPECTED_TITLE = '<title>DifficultAI - Voice Training Demo</title>'

class DeploymentMismatchError extends Error {}

export function findAppAssets(html, pageUrl) {
  if (!html.includes(EXPECTED_TITLE)) {
    throw new DeploymentMismatchError('deployed page is not the DifficultAI owner-pilot app')
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
    throw new DeploymentMismatchError('deployed app is missing its versioned JavaScript or CSS asset')
  }
  return [...new Map(assets.map((url) => [url.href, url])).values()]
}

export async function verifyDeployment(pageUrl, fetchImpl = fetch) {
  const page = await fetchImpl(pageUrl, {
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
      throw new DeploymentMismatchError(
        `${asset.pathname} served unexpected content-type ${contentType || '(missing)'}`,
      )
    }
  }
  return assets.map((asset) => asset.href)
}

const isMain = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href
if (isMain) {
  const pageUrl = process.argv[2]
  if (!pageUrl) {
    console.error('usage: npm run verify:deployment -- <page-url>')
    process.exitCode = 2
  } else {
    const attempts = 6
    for (let attempt = 1; attempt <= attempts; attempt += 1) {
      try {
        const assets = await verifyDeployment(pageUrl)
        console.log(`verified owner-pilot app and ${assets.length} assets at ${pageUrl}`)
        break
      } catch (error) {
        if (error instanceof DeploymentMismatchError || attempt === attempts) throw error
        console.log(`verification attempt ${attempt} failed: ${error.message}; retrying`)
        await new Promise((resolve) => setTimeout(resolve, 10_000))
      }
    }
  }
}
