import {
  OAUTH_CALLBACK_URL,
  OAUTH_SCOPE,
  OAUTH_STATE_COOKIE,
  OAUTH_VERIFIER_COOKIE,
  isCanonicalOauthRequest,
  oauthCookie,
  plainTextResponse,
  randomBase64Url,
  secureHeaders,
  sha256Base64Url,
} from "../_lib/oauth.js";

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

  if (!env.GITHUB_CLIENT_ID) {
    console.error("GITHUB_CLIENT_ID is not configured");
    return plainTextResponse("OAuth is not configured", 500);
  }

  const requestedScope = new URL(request.url).searchParams.get("scope");
  if (requestedScope && requestedScope !== OAUTH_SCOPE) {
    return plainTextResponse("Unsupported OAuth scope", 400);
  }

  const state = randomBase64Url();
  const codeVerifier = randomBase64Url();
  const codeChallenge = await sha256Base64Url(codeVerifier);

  const redirectUrl = new URL("https://github.com/login/oauth/authorize");
  redirectUrl.searchParams.set("client_id", env.GITHUB_CLIENT_ID);
  redirectUrl.searchParams.set("redirect_uri", OAUTH_CALLBACK_URL);
  redirectUrl.searchParams.set("scope", OAUTH_SCOPE);
  redirectUrl.searchParams.set("state", state);
  redirectUrl.searchParams.set("code_challenge", codeChallenge);
  redirectUrl.searchParams.set("code_challenge_method", "S256");

  const headers = secureHeaders("text/plain; charset=UTF-8");
  headers.set("Location", redirectUrl.href);
  headers.append("Set-Cookie", oauthCookie(OAUTH_STATE_COOKIE, state));
  headers.append(
    "Set-Cookie",
    oauthCookie(OAUTH_VERIFIER_COOKIE, codeVerifier)
  );

  return new Response(null, { status: 302, headers });
}
