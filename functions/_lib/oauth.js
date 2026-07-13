// Decap requires the OAuth popup origin to exactly match backend.base_url.
export const OAUTH_ORIGIN = "https://ivanbercovich.com";
export const OAUTH_CALLBACK_URL = `${OAUTH_ORIGIN}/api/callback`;
export const OAUTH_SCOPE = "public_repo";

export const OAUTH_STATE_COOKIE = "__Host-decap_oauth_state";
export const OAUTH_VERIFIER_COOKIE = "__Host-decap_oauth_verifier";

const OAUTH_COOKIE_MAX_AGE = 10 * 60;

function bytesToBase64Url(bytes) {
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }

  return btoa(binary)
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

export function randomBase64Url(byteLength = 32) {
  return bytesToBase64Url(crypto.getRandomValues(new Uint8Array(byteLength)));
}

export async function sha256Base64Url(value) {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(value)
  );
  return bytesToBase64Url(new Uint8Array(digest));
}

export function oauthCookie(name, value, maxAge = OAUTH_COOKIE_MAX_AGE) {
  return [
    `${name}=${value}`,
    "Path=/",
    `Max-Age=${maxAge}`,
    "HttpOnly",
    "Secure",
    "SameSite=Lax",
  ].join("; ");
}

export function clearOauthCookie(name) {
  return oauthCookie(name, "", 0);
}

export function readCookie(request, name) {
  const cookieHeader = request.headers.get("Cookie") || "";

  for (const cookie of cookieHeader.split(";")) {
    const [key, ...valueParts] = cookie.trim().split("=");
    if (key === name) {
      return valueParts.join("=");
    }
  }

  return null;
}

export function isCanonicalOauthRequest(request) {
  return new URL(request.url).origin === OAUTH_ORIGIN;
}

export function secureHeaders(contentType) {
  return new Headers({
    "Cache-Control": "no-store",
    "Content-Type": contentType,
    Pragma: "no-cache",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
  });
}

export function plainTextResponse(message, status) {
  return new Response(message, {
    status,
    headers: secureHeaders("text/plain; charset=UTF-8"),
  });
}
