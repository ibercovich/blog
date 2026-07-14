# Personal Blog

### Update April 2024

Added Decap CMS to be able to edit posts without dealing directly with the repo. The site is hosted on Cloudflare Pages.

- https://decapcms.org

### Update July 2026

Decap uses a fine-grained GitHub personal access token restricted to
`ibercovich/blog`, with only **Contents: read and write** permission. The token
is pasted from a password manager into the browser-only prompt served by
`/api/auth`; it must not be committed to this repository or stored in
Cloudflare. The prompt never sends it back to the Function. It passes the token
to Decap, which stores it in the browser's local storage until logout.

When moving from the former OAuth flow, deploy this version first. Then revoke
the old GitHub OAuth authorization, log out of Decap (or clear its saved site
data), sign in with the fine-grained token, and test one publish. Remove the old
`GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` Cloudflare secrets only after that
test succeeds.

### Update November 2024

- added compress_images.sh script to /assets
