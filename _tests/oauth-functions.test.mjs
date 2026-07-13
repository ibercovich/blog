import assert from "node:assert/strict";
import test from "node:test";

import { onRequest as authorize } from "../functions/api/auth.js";
import { onRequest as callback } from "../functions/api/callback.js";

const ORIGIN = "https://ivanbercovich.com";
const STATE_COOKIE = "__Host-decap_oauth_state";
const VERIFIER_COOKIE = "__Host-decap_oauth_verifier";

function cookieValue(setCookieHeader, name) {
  const match = setCookieHeader.match(new RegExp(`${name}=([^;,]*)`));
  return match?.[1] || null;
}

async function beginAuthorization() {
  return authorize({
    request: new Request(
      `${ORIGIN}/api/auth?provider=github&scope=public_repo`
    ),
    env: { GITHUB_CLIENT_ID: "test-client-id" },
  });
}

test("authorization starts with state, PKCE, narrow scope, and secure cookies", async () => {
  const response = await beginAuthorization();
  const location = new URL(response.headers.get("Location"));
  const setCookie = response.headers.get("Set-Cookie");
  const state = cookieValue(setCookie, STATE_COOKIE);
  const verifier = cookieValue(setCookie, VERIFIER_COOKIE);

  assert.equal(response.status, 302);
  assert.equal(response.headers.get("Cache-Control"), "no-store");
  assert.equal(location.origin, "https://github.com");
  assert.equal(location.pathname, "/login/oauth/authorize");
  assert.equal(
    location.searchParams.get("redirect_uri"),
    `${ORIGIN}/api/callback`
  );
  assert.equal(location.searchParams.get("scope"), "public_repo");
  assert.equal(location.searchParams.get("state"), state);
  assert.equal(location.searchParams.get("code_challenge_method"), "S256");
  assert.ok(state?.length >= 43);
  assert.ok(verifier?.length >= 43);
  assert.match(setCookie, /HttpOnly/);
  assert.match(setCookie, /Secure/);
  assert.match(setCookie, /SameSite=Lax/);

  const challengeBytes = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(verifier)
  );
  const expectedChallenge = Buffer.from(challengeBytes)
    .toString("base64url");
  assert.equal(location.searchParams.get("code_challenge"), expectedChallenge);
});

test("authorization rejects other hosts and broader scopes", async () => {
  const wrongHost = await authorize({
    request: new Request("https://preview.pages.dev/api/auth?scope=public_repo"),
    env: { GITHUB_CLIENT_ID: "test-client-id" },
  });
  const broadScope = await authorize({
    request: new Request(`${ORIGIN}/api/auth?scope=repo`),
    env: { GITHUB_CLIENT_ID: "test-client-id" },
  });

  assert.equal(wrongHost.status, 403);
  assert.equal(broadScope.status, 400);
});

test("callback rejects missing or mismatched state before exchanging a token", async () => {
  const originalFetch = globalThis.fetch;
  let fetchCalled = false;
  globalThis.fetch = async () => {
    fetchCalled = true;
    throw new Error("fetch should not be called");
  };

  try {
    const response = await callback({
      request: new Request(`${ORIGIN}/api/callback?code=test&state=wrong`, {
        headers: {
          Cookie: `${STATE_COOKIE}=expected; ${VERIFIER_COOKIE}=verifier`,
        },
      }),
      env: {
        GITHUB_CLIENT_ID: "test-client-id",
        GITHUB_CLIENT_SECRET: "test-client-secret",
      },
    });

    assert.equal(response.status, 400);
    assert.equal(fetchCalled, false);
    assert.match(
      await response.text(),
      /authorization request is invalid or has expired/i
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("callback exchanges the code with PKCE and restricts the popup handshake", async () => {
  const authorization = await beginAuthorization();
  const location = new URL(authorization.headers.get("Location"));
  const setCookie = authorization.headers.get("Set-Cookie");
  const state = cookieValue(setCookie, STATE_COOKIE);
  const verifier = cookieValue(setCookie, VERIFIER_COOKIE);
  const originalFetch = globalThis.fetch;
  let tokenRequest;

  globalThis.fetch = async (url, options) => {
    tokenRequest = { url, options };
    return new Response(
      JSON.stringify({
        access_token: "gho_test_token",
        scope: "public_repo",
        token_type: "bearer",
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );
  };

  try {
    const response = await callback({
      request: new Request(
        `${ORIGIN}/api/callback?code=test-code&state=${state}`,
        {
          headers: {
            Cookie: `${STATE_COOKIE}=${state}; ${VERIFIER_COOKIE}=${verifier}`,
          },
        }
      ),
      env: {
        GITHUB_CLIENT_ID: "test-client-id",
        GITHUB_CLIENT_SECRET: "test-client-secret",
      },
    });
    const html = await response.text();
    const body = new URLSearchParams(tokenRequest.options.body);

    assert.equal(response.status, 200);
    assert.equal(response.headers.get("Cache-Control"), "no-store");
    assert.match(
      response.headers.get("Content-Security-Policy"),
      /default-src 'none'/
    );
    assert.equal(tokenRequest.url, "https://github.com/login/oauth/access_token");
    assert.equal(body.get("code"), "test-code");
    assert.equal(body.get("code_verifier"), verifier);
    assert.equal(body.get("redirect_uri"), `${ORIGIN}/api/callback`);
    assert.match(html, /authorization:github:success/);
    assert.match(html, /gho_test_token/);
    assert.match(html, /event\.source !== opener/);
    assert.match(html, /event\.origin !== expectedOrigin/);
    assert.match(html, /event\.data !== "authorizing:github"/);
    assert.doesNotMatch(html, /postMessage\("authorizing:github", "\*"\)/);
    assert.match(response.headers.get("Set-Cookie"), /Max-Age=0/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
