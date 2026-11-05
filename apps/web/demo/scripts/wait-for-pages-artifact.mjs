import { pathToFileURL } from 'node:url';

const wait = (milliseconds) =>
  new Promise((resolve) => setTimeout(resolve, milliseconds));

export async function waitForPagesArtifact({
  token,
  repository,
  runId,
  fetchImpl = fetch,
  sleep = wait,
  now = Date.now,
  timeoutMilliseconds = 60_000,
  pollMilliseconds = 2_000,
}) {
  if (!token || !repository || !runId) {
    throw new Error('Pages artifact wait requires token, repository, and run ID');
  }

  const started = now();
  const endpoint =
    `https://api.github.com/repos/${repository}/actions/runs/${runId}/artifacts` +
    '?name=github-pages&per_page=100';

  while (now() - started < timeoutMilliseconds) {
    const response = await fetchImpl(endpoint, {
      headers: {
        Accept: 'application/vnd.github+json',
        Authorization: `Bearer ${token}`,
        'X-GitHub-Api-Version': '2022-11-28',
      },
    });
    if (response.status === 429 || response.status >= 500) {
      await sleep(pollMilliseconds);
      continue;
    }
    if (!response.ok) {
      throw new Error(`Pages artifact lookup failed with HTTP ${response.status}`);
    }

    const payload = await response.json();
    if (!Array.isArray(payload.artifacts)) {
      throw new Error('Pages artifact lookup returned an invalid Actions payload');
    }
    const artifact = payload.artifacts.find(
      (candidate) => candidate.name === 'github-pages' && candidate.expired !== true,
    );
    if (artifact) {
      return { id: artifact.id };
    }
    await sleep(pollMilliseconds);
  }

  throw new Error(`github-pages artifact was not visible within ${timeoutMilliseconds}ms`);
}

async function main() {
  const artifact = await waitForPagesArtifact({
    token: process.env.GH_TOKEN,
    repository: process.env.REPOSITORY,
    runId: process.env.RUN_ID,
  });
  console.log(`github-pages artifact is visible (ID ${artifact.id}); deployment may start.`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
