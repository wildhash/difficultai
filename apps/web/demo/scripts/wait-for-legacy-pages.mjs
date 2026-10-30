import { pathToFileURL } from 'node:url';

const LEGACY_WORKFLOW = 'pages build and deployment';

const wait = (milliseconds) =>
  new Promise((resolve) => setTimeout(resolve, milliseconds));

export async function waitForLegacyPages({
  token,
  repository,
  commitSha,
  fetchImpl = fetch,
  sleep = wait,
  now = Date.now,
  discoveryMilliseconds = 30_000,
  timeoutMilliseconds = 5 * 60_000,
  pollMilliseconds = 5_000,
}) {
  if (!token || !repository || !commitSha) {
    throw new Error('legacy Pages wait requires token, repository, and commit SHA');
  }

  const started = now();
  const endpoint =
    `https://api.github.com/repos/${repository}/actions/runs?head_sha=${commitSha}&per_page=50`;

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
      throw new Error(`legacy Pages lookup failed with HTTP ${response.status}`);
    }

    const payload = await response.json();
    if (!Array.isArray(payload.workflow_runs)) {
      throw new Error('legacy Pages lookup returned an invalid Actions payload');
    }
    const run = payload.workflow_runs
      .filter(
        (candidate) =>
          candidate.name === LEGACY_WORKFLOW &&
          candidate.event === 'dynamic' &&
          candidate.head_sha === commitSha,
      )
      .sort((left, right) => right.id - left.id)[0];

    if (run?.status === 'completed') {
      if (run.conclusion !== 'success') {
        console.warn(`Legacy Pages run concluded with ${run.conclusion}; ordering is still complete.`);
      }
      return { found: true, conclusion: run.conclusion };
    }
    if (!run && now() - started >= discoveryMilliseconds) {
      return { found: false, conclusion: null };
    }
    await sleep(pollMilliseconds);
  }

  throw new Error(
    `legacy Pages publication did not finish within ${timeoutMilliseconds}ms`,
  );
}

async function main() {
  const result = await waitForLegacyPages({
    token: process.env.GH_TOKEN,
    repository: process.env.REPOSITORY,
    commitSha: process.env.COMMIT_SHA,
  });
  if (result.found) {
    console.log(`Legacy Pages run completed (${result.conclusion}); publishing Vite last.`);
  } else {
    console.log('No matching legacy Pages run appeared; continuing with Vite publication.');
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
