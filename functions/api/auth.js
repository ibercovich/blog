const DECAP_AUTH_ORIGIN = "https://ivanbercovich.com";

function randomNonce(byteLength = 18) {
  const bytes = crypto.getRandomValues(new Uint8Array(byteLength));
  let binary = "";

  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }

  return btoa(binary)
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

function secureHeaders(contentType) {
  return new Headers({
    "Cache-Control": "no-store, max-age=0",
    "Content-Type": contentType,
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy":
      "camera=(), geolocation=(), microphone=(), payment=(), usb=()",
    Pragma: "no-cache",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-Robots-Tag": "noindex, nofollow",
  });
}

function plainTextResponse(message, status) {
  return new Response(message, {
    status,
    headers: secureHeaders("text/plain; charset=UTF-8"),
  });
}

function tokenPromptResponse() {
  const nonce = randomNonce();
  const expectedOrigin = JSON.stringify(DECAP_AUTH_ORIGIN);

  const html = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Connect Decap CMS</title>
    <style nonce="${nonce}">
      * { box-sizing: border-box; }
      body {
        align-items: center;
        background: #f7f7f7;
        color: #333;
        display: flex;
        font-family: Palatino, "Palatino Linotype", "Book Antiqua", serif;
        justify-content: center;
        margin: 0;
        min-height: 100vh;
        padding: 2rem 1rem;
      }
      main {
        background: #fff;
        border: 1px solid #ddd;
        border-radius: 4px;
        box-shadow: 0 8px 28px rgb(0 0 0 / 8%);
        max-width: 34rem;
        padding: 2.25rem;
        width: 100%;
      }
      h1 {
        font-size: 1.75rem;
        font-weight: 400;
        margin: 0 0 1rem;
      }
      p {
        line-height: 1.55;
        margin: 0 0 1.25rem;
      }
      label {
        display: block;
        font-weight: 600;
        margin-bottom: 0.45rem;
      }
      input {
        background: #fff;
        border: 1px solid #aaa;
        border-radius: 3px;
        color: #222;
        font: 1rem ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        padding: 0.75rem;
        width: 100%;
      }
      input:focus {
        border-color: #555;
        box-shadow: 0 0 0 3px rgb(0 0 0 / 10%);
        outline: none;
      }
      button {
        background: #333;
        border: 1px solid #333;
        border-radius: 3px;
        color: #fff;
        cursor: pointer;
        font: inherit;
        margin-top: 1rem;
        padding: 0.7rem 1.15rem;
      }
      button:disabled {
        cursor: wait;
        opacity: 0.55;
      }
      .status {
        color: #666;
        font-size: 0.9rem;
        margin: 0.75rem 0 0;
        min-height: 1.4em;
      }
      .note {
        border-top: 1px solid #e5e5e5;
        color: #666;
        font-size: 0.85rem;
        margin: 1.5rem 0 0;
        padding-top: 1rem;
      }
      .field + .field {
        margin-top: 1rem;
      }
    </style>
  </head>
  <body>
    <main>
      <h1>Connect Decap CMS</h1>
      <p>
        Sign in with the password saved for <strong>ivanbercovich.com</strong>.
        It is the fine-grained GitHub token Decap uses to access
        <strong>ibercovich/blog</strong>.
      </p>
      <form id="token-form" action="about:blank" method="post" autocomplete="on">
        <div class="field">
          <label for="username">Username</label>
          <input
            id="username"
            type="text"
            value="NA"
            autocomplete="username"
            autocapitalize="none"
            spellcheck="false"
          >
        </div>
        <div class="field">
          <label for="token">Password</label>
          <input
            id="token"
            type="password"
            autocomplete="current-password"
            autocapitalize="none"
            maxlength="1024"
            required
            spellcheck="false"
          >
        </div>
        <button id="continue" type="submit" disabled>Continue</button>
        <p id="status" class="status" role="status" aria-live="polite">
          Connecting to Decap…
        </p>
      </form>
      <p class="note">
        This prompt never sends the token to the Cloudflare Function. Decap
        stores the token in this browser's local storage; logging out clears
        the saved login, and revoking the token invalidates it.
      </p>
    </main>
    <script nonce="${nonce}">
      (() => {
        const expectedOrigin = ${expectedOrigin};
        const opener = window.opener;
        const form = document.getElementById("token-form");
        const tokenInput = document.getElementById("token");
        const continueButton = document.getElementById("continue");
        const status = document.getElementById("status");
        let handshakeComplete = false;

        if (!opener) {
          tokenInput.disabled = true;
          status.textContent = "Open this prompt from the Decap login page.";
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

          handshakeComplete = true;
          continueButton.disabled = false;
          status.textContent = "Ready.";
          window.removeEventListener("message", receiveMessage, false);
          tokenInput.focus();
        };

        window.addEventListener("message", receiveMessage, false);
        opener.postMessage("authorizing:github", expectedOrigin);

        form.addEventListener("submit", (event) => {
          event.preventDefault();

          const token = tokenInput.value.trim();
          if (!handshakeComplete) {
            status.textContent = "Decap is not ready. Close this window and try again.";
            return;
          }

          if (!token || /\\s/.test(token)) {
            status.textContent = "Paste one GitHub token without spaces.";
            tokenInput.focus();
            return;
          }

          continueButton.disabled = true;
          status.textContent = "Signing in…";
          const payload = JSON.stringify({ token, provider: "github" });
          tokenInput.value = "";
          opener.postMessage(
            "authorization:github:success:" + payload,
            expectedOrigin
          );
        });
      })();
    </script>
  </body>
</html>`;

  const headers = secureHeaders("text/html; charset=UTF-8");
  headers.set(
    "Content-Security-Policy",
    `default-src 'none'; script-src 'nonce-${nonce}'; style-src 'nonce-${nonce}'; connect-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'`
  );

  return new Response(html, { status: 200, headers });
}

export function onRequest({ request }) {
  if (request.method !== "GET") {
    const response = plainTextResponse("Method not allowed", 405);
    response.headers.set("Allow", "GET");
    return response;
  }

  const url = new URL(request.url);
  if (url.origin !== DECAP_AUTH_ORIGIN) {
    return plainTextResponse(
      "Decap authentication is only available on the production site",
      403
    );
  }

  if (url.searchParams.get("provider") !== "github") {
    return plainTextResponse("Unsupported authentication provider", 400);
  }

  return tokenPromptResponse();
}
