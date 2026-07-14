import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const config = await readFile(
  new URL("../admin/config.yml", import.meta.url),
  "utf8"
);

function collection(name) {
  const marker = `  - name: "${name}"`;
  const start = config.indexOf(marker);
  assert.notEqual(start, -1, `missing ${name} collection`);
  const next = config.indexOf("\n  - name:", start + marker.length);
  return config.slice(start, next === -1 ? undefined : next);
}

test("the live post schema exposes the front matter used by the site", () => {
  const block = collection("post");

  for (const field of [
    "permalink",
    "redirect_from",
    "noindex",
  ]) {
    assert.match(block, new RegExp(`name: ["']?${field}["']?`), `post.${field}`);
  }

  assert.match(block, /name: "author"[\s\S]{0,80}widget: "hidden"/);
  for (const field of ["description", "image"]) {
    assert.match(
      block,
      new RegExp(`name: ["']${field}["'][^\\n]+widget: ["']hidden["']`),
      `${field} remains an invisible pass-through field`
    );
  }
  assert.match(block, /label: "Original publication date"/);
  assert.match(block, /name: "date"[\s\S]{0,100}default: ""/);
  assert.doesNotMatch(block, /name: ["']?categories["']?/);
});

test("publication dates never default to the edit time", () => {
  assert.doesNotMatch(config, /\{\{\s*now\s*\}\}/i);
  assert.match(
    collection("post"),
    /Editing or saving the post does not update it\./
  );
});
