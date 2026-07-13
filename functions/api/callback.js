import {
  OAUTH_CALLBACK_URL,
  OAUTH_ORIGIN,
  OAUTH_STATE_COOKIE,
  OAUTH_VERIFIER_COOKIE,
  clearOauthCookie,
  isCanonicalOauthRequest,
  plainTextResponse,
  randomBase64Url,
  readCookie,
  secureHeaders,
} from "../_lib/oauth.js";

const BASE64URL_PATTERN = /^[A-Za-z0-9_-]{43,128}$/;
const MAX_AUTHORIZATION_CODE_LENGTH = 1024;

function safeJson(value) {
  return JSON.stringify(value).replace(/</g, "\\u003c");
}

function oauthPopupResponse(status, content, httpStatus = 200) {
  const nonce = randomBase64Url(18);
  const authorizationMessage = safeJson(
    `authorization:github:${status}:${JSON.stringify(content)}`
  );
  const expectedOrigin = safeJson(OAUTH_ORIGIN);

  const html = `<!doctype html>
<html lang="en">
  <head><meta charset="utf-8"><title>GitHub authorization</title></head>
  <body>
    <p>Completing GitHub authorization…</p>
    <script nonce="${nonce}">
      (() => {
        const expectedOrigin = ${expectedOrigin};
        const authorizationMessage = ${authorizationMessage};
        const opener = window.opener;

        if (!opener) {
          document.body.textContent = "Unable to complete authorization.";
          return;
        }

        const receiveMessage = (event) => {
          if (
            event.source !== opener ||
            event.origin !== expectedOrigin ||
            event.data !== "authorizing:github"
          ) {
            return;
          }

          opener.postMessage(authorizationMessage, expectedOrigin);
          window.removeEventListener("message", receiveMessage, false);
        };

        window.addEventListener("message", receiveMessage, false);
        opener.postMessage("authorizing:github", expectedOrigin);
      })();
    </script>
  </body>
</html>`;

  const headers = secureHeaders("text/html; charset=UTF-8");
  headers.set(
    "Content-Security-Policy",
    `default-src 'none'; script-src 'nonce-${nonce}'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'`
  );
  headers.append("Set-Cookie", clearOauthCookie(OAUTH_STATE_COOKIE));
  headers.append("Set-Cookie", clearOauthCookie(OAUTH_VERIFIER_COOKIE));

  return new Response(html, { status: httpStatus, headers });
}

function oauthError(message, status = 400) {
  return oauthPopupResponse("error", { message }, status);
}

export async function onRequest({ request, env }) {
  if (request.method !== "GET") {
    return plainTextResponse("Method not allowed", 405);
  }

  if (!isCanonicalOauthRequest(request)) {
    return plainTextResponse(
      "OAuth is only available on the production site",
      403
    );
  }

  const url = new URL(request.url);
  const returnedState = url.searchParams.get("state");
  const expectedState = readCookie(request, OAUTH_STATE_COOKIE);
  const codeVerifier = readCookie(request, OAUTH_VERIFIER_COOKIE);

  if (
    !returnedState ||
    !expectedState ||
    !BASE64URL_PATTERN.test(returnedState) ||
    !BASE64URL_PATTERN.test(expectedState) ||
    returnedState !== expectedState ||
    !codeVerifier ||
    !BASE64URL_PATTERN.test(codeVerifier)
  ) {
    return oauthError("The authorization request is invalid or has expired.");
  }

  const oauthErrorCode = url.searchParams.get("error");
  if (oauthErrorCode) {
    const description = url.searchParams.get("error_description");
    return oauthError(description || "GitHub authorization was denied.");
  }

  const code = url.searchParams.get("code");
  if (!code || code.length > MAX_AUTHORIZATION_CODE_LENGTH) {
    return oauthError("GitHub did not return an authorization code.");
  }

  if (!env.GITHUB_CLIENT_ID || !env.GITHUB_CLIENT_SECRET) {
    console.error("GitHub OAuth credentials are not configured");
    return oauthError("OAuth is not configured.", 500);
  }

  try {
    const response = await fetch(
      "https://github.com/login/oauth/access_token",
      {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/x-www-form-urlencoded",
          "User-Agent": "neversupervised-decap-oauth",
        },
        body: new URLSearchParams({
          client_id: env.GITHUB_CLIENT_ID,
          client_secret: env.GITHUB_CLIENT_SECRET,
          code,
          redirect_uri: OAUTH_CALLBACK_URL,
          code_verifier: codeVerifier,
        }),
      }
    );

    const result = await response.json();
    if (
      !response.ok ||
      result.error ||
      typeof result.access_token !== "string" ||
      !result.access_token
    ) {
      console.error(
        "GitHub OAuth token exchange failed",
        result.error || response.status
      );
      return oauthError("GitHub could not complete authorization.", 401);
    }

    const grantedScopes = new Set(
      typeof result.scope === "string"
        ? result.scope.split(/[\s,]+/).filter(Boolean)
        : []
    );
    if (!grantedScopes.has("public_repo") && !grantedScopes.has("repo")) {
      return oauthError(
        "GitHub did not grant the required repository access.",
        403
      );
    }

    return oauthPopupResponse("success", {
      token: result.access_token,
      provider: "github",
    });
  } catch (error) {
    console.error("GitHub OAuth token exchange failed", error);
    return oauthError("GitHub could not complete authorization.", 502);
  }
}
