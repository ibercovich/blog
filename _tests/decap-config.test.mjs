import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const config = await readFile(
  new URL("../admin/config.yml", import.meta.url),
  "utf8"
);

const EDITABLE_PAGE_FILES = [
  "_pages/about.md",
  "_pages/antiportfolio.md",
  "_pages/principles.md",
  "_pages/research.md",
  "_pages/safety.md",
];

function collection(name) {
  const marker = `  - name: "${name}"`;
  const start = config.indexOf(marker);
  assert.notEqual(start, -1, `missing ${name} collection`);
  const next = config.indexOf("\n  - name:", start + marker.length);
  return config.slice(start, next === -1 ? undefined : next);
}

function fieldSchema(name) {
  const block = collection(name);
  const fields = block.slice(block.indexOf("\n    fields:"));
  return fields.split("\n\n", 1)[0].trim();
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
  for (const field of ["description", "image", "draft"]) {
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

test("archived posts use the same front matter schema as live posts", () => {
  assert.equal(fieldSchema("post_archived"), fieldSchema("post"));
  assert.doesNotMatch(
    collection("post_archived"),
    /name: ["']?categories["']?/
  );
});

test("Books is a Git-backed folder collection with the tracking fields", () => {
  const block = collection("books");

  assert.match(block, /^    folder: ["']_books["']$/m);
  assert.match(block, /^    create: true$/m);
  assert.match(block, /^    format: ["']yaml-frontmatter["']$/m);

  for (const field of [
    "title",
    "author",
    "isbn",
    "cover",
    "color",
    "status",
    "collections",
    "physical_copy",
    "recommended",
    "finished_on",
    "synopsis",
  ]) {
    assert.match(block, new RegExp(`name: ["']${field}["']`), `books.${field}`);
  }

  assert.match(block, /name: ["']cover["'][\s\S]{0,180}media_folder: ["']\/assets\/covers["']/);
  assert.match(block, /label: ["']Want to read["'], value: ["']want_to_read["']/);
});

test("Pages exposes exactly the five ordinary pages as explicit files", () => {
  const block = collection("pages");

  assert.match(block, /^    files:\s*$/m);
  assert.doesNotMatch(block, /^    folder:/m);
  assert.doesNotMatch(block, /^    create:\s*true\s*$/m);

  const files = [
    ...block.matchAll(/^\s+file:\s*["']?([^"'\s]+)["']?\s*$/gm),
  ]
    .map(([, file]) => file)
    .sort();
  assert.deepEqual(files, EDITABLE_PAGE_FILES);
});

test("Post collections exclude non-post layouts", () => {
  for (const name of ["post", "post_archived"]) {
    assert.match(
      collection(name),
      /filter:[\s\S]{0,120}field:\s*["']?layout["']?[\s\S]{0,80}value:\s*["']?post["']?/
    );
  }
});
