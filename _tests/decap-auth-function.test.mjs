import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";

import { onRequest as authenticate } from "../functions/api/auth.js";

const ORIGIN = "https://ivanbercovich.com";

function authRequest(
  url = `${ORIGIN}/api/auth?provider=github&site_id=ivanbercovich.com&scope=repo`,
  method = "GET"
) {
  return authenticate({
    request: new Request(url, { method }),
    env: {
      GITHUB_CLIENT_ID: "must-not-appear",
      GITHUB_CLIENT_SECRET: "must-not-appear",
    },
  });
}

function popupScript(html) {
  const scripts = [
    ...html.matchAll(/<script nonce="[A-Za-z0-9_-]+">([\s\S]*?)<\/script>/g),
  ];
  assert.equal(scripts.length, 1);
  return scripts[0][1];
}

function popupRuntime(script, { withOpener = true } = {}) {
  const elements = new Map();

  for (const id of ["token-form", "token", "continue", "status"]) {
    elements.set(id, {
      disabled: id === "continue",
      focused: false,
      listeners: new Map(),
      textContent: "",
      value: "",
      addEventListener(type, listener) {
        this.listeners.set(type, listener);
      },
      focus() {
        this.focused = true;
      },
    });
  }

  const postedMessages = [];
  const opener = withOpener
    ? {
        postMessage(message, targetOrigin) {
          postedMessages.push({ message, targetOrigin });
        },
      }
    : null;
  const messageListeners = new Set();
  const window = {
    opener,
    addEventListener(type, listener) {
      if (type === "message") {
        messageListeners.add(listener);
      }
    },
    removeEventListener(type, listener) {
      if (type === "message") {
        messageListeners.delete(listener);
      }
    },
  };
  const document = {
    getElementById(id) {
      return elements.get(id);
    },
  };

  vm.runInNewContext(script, { document, JSON, window });

  return {
    elements,
    opener,
    postedMessages,
    receiveMessage(event) {
      for (const listener of [...messageListeners]) {
        listener(event);
      }
    },
    submit() {
      elements.get("token-form").listeners.get("submit")({
        preventDefault() {},
      });
    },
  };
}

test("serves a browser-only fine-grained token prompt", async () => {
  const response = authRequest();
  const html = await response.text();
  const csp = response.headers.get("Content-Security-Policy");

  assert.equal(response.status, 200);
  assert.equal(response.headers.get("Cache-Control"), "no-store, max-age=0");
  assert.equal(response.headers.get("Content-Type"), "text/html; charset=UTF-8");
  assert.equal(response.headers.get("Set-Cookie"), null);
  assert.equal(response.headers.get("Location"), null);
  assert.match(csp, /default-src 'none'/);
  assert.match(csp, /script-src 'nonce-[A-Za-z0-9_-]+'/);
  assert.match(csp, /style-src 'nonce-[A-Za-z0-9_-]+'/);
  assert.match(csp, /connect-src 'none'/);
  assert.match(csp, /form-action 'none'/);
  assert.match(csp, /frame-ancestors 'none'/);
  assert.match(html, /<input[\s\S]+type="password"/);
  assert.match(html, /action="about:blank" method="post"/);
  assert.match(html, /<form[^>]+autocomplete="on"/);
  const inputs = [...html.matchAll(/<input\b[^>]*>/g)].map(
    (match) => match[0]
  );
  const usernameInput = inputs.find((input) => /\sid="username"/.test(input));
  const tokenInput = inputs.find((input) => /\sid="token"/.test(input));
  assert.ok(usernameInput);
  assert.ok(tokenInput);
  assert.match(usernameInput, /\stype="text"/);
  assert.match(usernameInput, /\svalue="NA"/);
  assert.match(usernameInput, /\sautocomplete="username"/);
  assert.doesNotMatch(usernameInput, /\sname=/);
  assert.match(tokenInput, /\stype="password"/);
  assert.doesNotMatch(tokenInput, /\sname=/);
  assert.match(tokenInput, /\sautocomplete="current-password"/);
  assert.match(tokenInput, /spellcheck="false"/);
  assert.match(html, /fine-grained GitHub token/);
  assert.doesNotMatch(html, /github\.com\/login\/oauth/);
  assert.doesNotMatch(html, /must-not-appear/);
});

test("rejects non-GET requests and advertises the allowed method", async () => {
  for (const method of ["POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]) {
    const response = authRequest(undefined, method);
    assert.equal(response.status, 405, method);
    assert.equal(response.headers.get("Allow"), "GET", method);
    assert.equal(response.headers.get("Cache-Control"), "no-store, max-age=0");
  }
});

test("accepts only the exact production origin", async () => {
  for (const origin of [
    "https://www.ivanbercovich.com",
    "http://ivanbercovich.com",
    "https://ivanbercovich.com:444",
    "https://ivanbercovich.com.evil.example",
    "https://preview.pages.dev",
  ]) {
    const response = authRequest(`${origin}/api/auth?provider=github`);
    assert.equal(response.status, 403, origin);
    assert.equal(response.headers.get("Cache-Control"), "no-store, max-age=0");
  }
});

test("accepts only the GitHub provider", async () => {
  const missingProvider = authRequest(`${ORIGIN}/api/auth`);
  const wrongProvider = authRequest(
    `${ORIGIN}/api/auth?provider=gitlab&scope=repo`
  );

  assert.equal(missingProvider.status, 400);
  assert.equal(wrongProvider.status, 400);
});

test("locks the Decap popup handshake to its opener and exact origin", async () => {
  const response = authRequest();
  const html = await response.text();

  assert.match(html, /event\.source !== opener/);
  assert.match(html, /event\.origin !== expectedOrigin/);
  assert.match(html, /event\.data !== "authorizing:github"/);
  assert.match(html, /opener\.postMessage\("authorizing:github", expectedOrigin\)/);
  assert.match(html, /authorization:github:success:/);
  assert.match(html, /JSON\.stringify\(\{ token, provider: "github" \}\)/);
  assert.match(html, /tokenInput\.value = ""/);
  assert.doesNotMatch(html, /postMessage\([^\n]+,\s*["']\*["']/);
});

test("executes the trusted handshake before sending and clearing a token", async () => {
  const response = authRequest();
  const runtime = popupRuntime(popupScript(await response.text()));
  const tokenInput = runtime.elements.get("token");
  const continueButton = runtime.elements.get("continue");
  const status = runtime.elements.get("status");

  assert.deepEqual(runtime.postedMessages, [
    {
      message: "authorizing:github",
      targetOrigin: ORIGIN,
    },
  ]);

  tokenInput.value = "github_pat_not_sent_early";
  runtime.submit();
  assert.equal(runtime.postedMessages.length, 1);
  assert.match(status.textContent, /not ready/i);

  for (const event of [
    { source: {}, origin: ORIGIN, data: "authorizing:github" },
    { source: runtime.opener, origin: "https://evil.example", data: "authorizing:github" },
    { source: runtime.opener, origin: ORIGIN, data: "wrong" },
  ]) {
    runtime.receiveMessage(event);
  }
  assert.equal(continueButton.disabled, true);

  runtime.receiveMessage({
    source: runtime.opener,
    origin: ORIGIN,
    data: "authorizing:github",
  });
  assert.equal(continueButton.disabled, false);
  assert.equal(tokenInput.focused, true);

  tokenInput.value = 'github_pat_quote"slash\\less<than';
  runtime.submit();

  assert.equal(runtime.postedMessages.length, 2);
  assert.equal(runtime.postedMessages[1].targetOrigin, ORIGIN);
  assert.match(
    runtime.postedMessages[1].message,
    /^authorization:github:success:/
  );
  assert.deepEqual(
    JSON.parse(
      runtime.postedMessages[1].message.replace(
        "authorization:github:success:",
        ""
      )
    ),
    {
      token: 'github_pat_quote"slash\\less<than',
      provider: "github",
    }
  );
  assert.equal(tokenInput.value, "");
  assert.equal(continueButton.disabled, true);
});

test("keeps empty, malformed, and opener-less submissions local", async () => {
  const response = authRequest();
  const script = popupScript(await response.text());
  const runtime = popupRuntime(script);
  const tokenInput = runtime.elements.get("token");

  runtime.receiveMessage({
    source: runtime.opener,
    origin: ORIGIN,
    data: "authorizing:github",
  });

  for (const token of ["", "   ", "github_pat_has a space", "line1\nline2"]) {
    tokenInput.value = token;
    runtime.submit();
    assert.equal(runtime.postedMessages.length, 1, JSON.stringify(token));
    assert.doesNotMatch(runtime.elements.get("status").textContent, /github_pat|line1/);
  }

  const withoutOpener = popupRuntime(script, { withOpener: false });
  assert.equal(withoutOpener.elements.get("token").disabled, true);
  assert.match(withoutOpener.elements.get("status").textContent, /Decap login page/i);
  assert.equal(withoutOpener.postedMessages.length, 0);
});

test("contains no server-side OAuth flow or browser token side channels", async () => {
  const response = authRequest(
    `${ORIGIN}/api/auth?provider=github&scope=repo&token=secret-marker`
  );
  const html = await response.text();
  const script = popupScript(html);
  const source = await readFile(
    new URL("../functions/api/auth.js", import.meta.url),
    "utf8"
  );
  const config = await readFile(
    new URL("../admin/config.yml", import.meta.url),
    "utf8"
  );
  const admin = await readFile(
    new URL("../admin/index.html", import.meta.url),
    "utf8"
  );

  assert.doesNotMatch(html, /secret-marker/);
  assert.doesNotMatch(
    script,
    /\b(fetch|XMLHttpRequest|sendBeacon|WebSocket|localStorage|sessionStorage|document\.cookie|navigator\.clipboard|console\.)\b/
  );
  assert.doesNotMatch(
    source,
    /GITHUB_CLIENT|login\/oauth|access_token|code_verifier|oauth_state/i
  );
  assert.doesNotMatch(config, /auth_scope/);
  assert.match(admin, /decap-cms@3\.14\.1/);
  assert.match(admin, /integrity="sha384-[A-Za-z0-9+/=]+"/);
  assert.match(admin, /crossorigin="anonymous"/);
});
