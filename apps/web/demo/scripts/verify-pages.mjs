import { fileURLToPath } from 'node:url'

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

export async function verifyDeployment(pageUrl, fetchImpl = fetch) {
  const page = await fetchImpl(pageUrl, { cache: 'no-store' })
  if (!page.ok) throw new Error(`page returned HTTP ${page.status}`)

  const assets = findAppAssets(await page.text(), pageUrl)
  for (const asset of assets) {
    const response = await fetchImpl(asset, { cache: 'no-store' })
    if (!response.ok) {
      throw new Error(`${asset.pathname} returned HTTP ${response.status}`)
    }
  }
  return assets.map((asset) => asset.href)
}

const isMain = process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]
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
        if (attempt === attempts) throw error
        console.log(`verification attempt ${attempt} failed: ${error.message}; retrying`)
        await new Promise((resolve) => setTimeout(resolve, 10_000))
      }
    }
  }
}
