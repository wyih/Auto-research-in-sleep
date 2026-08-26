# Zotero Fulltext Attachment Semantics

Use Zotero as a **local discovery and attachment channel**, not as an excuse to mutate the user's library. Prefer a configured Zotero connector/API when available. A read-only local-library query is an allowed fallback only for the exact requested paper.

## Identity Model

Keep these identities separate:

1. **Bibliographic parent item** — title, authors, year, venue, DOI, and the stable parent item key.
2. **Attachment child item** — its own item key, `parentItemID`, content type, link mode, and path locator.
3. **Resolved local file** — actual bytes, size, detected format, and SHA-256.
4. **METHOD_CARD** — records both Zotero keys, the accepted local path, and the byte hash.

Never use an attachment filename/title as authoritative paper metadata when a parent item exists. Never cite an attachment child as though it were the bibliographic item.

## Common Local Path Semantics

- `storage:<filename>` is an imported/stored attachment. Resolve it beneath the attachment item's storage directory, conventionally `Zotero/storage/<attachment_item_key>/<filename>`.
- `attachments:<relative-path>` is a linked attachment relative to Zotero's configured base attachment path.
- An absolute linked-file path remains an absolute path; do not rewrite or relocate it inside Zotero.
- A URL or HTML snapshot is not a PDF. Require `contentType=application/pdf` plus the normal PDF verifier for a PDF-only downstream step.

Treat the live library/API as authoritative for the current locator. Do not infer a stored path from the parent key, and do not assume every child is a file attachment.

## Read-Only Resolution Procedure

1. Match the bibliographic parent by exact DOI when present, otherwise normalized title + author/year.
2. Enumerate only that parent's attachment children.
3. Prefer an identity-matched PDF child. Record parent key, attachment key, content type, path semantics, and whether it is stored or linked.
4. Resolve the file without changing Zotero preferences, the database, attachment links, collections, tags, or notes.
5. Copy into the project acceptance/fulltext area only when the caller needs an immutable working artifact; never overwrite the Zotero source.
6. Verify format, stable size, SHA-256, page count, and first-page identity.
7. In the METHOD_CARD, set `fulltext_channel: zotero` and record both Zotero keys plus the verified artifact hash.

## Missing Target

If the requested paper has no matching parent or no valid PDF child:

- record `zotero_parent_missing` or `zotero_pdf_attachment_missing`;
- continue down the lawful channel ladder;
- do not silently create/import a Zotero item, attach a file, or edit the library.

## Acceptance

Zotero linkage passes only when all of the following hold:

- parent and child identities are distinct and linked;
- the locator resolves to an existing file;
- the file is the requested paper and passes deterministic verification;
- the accepted artifact hash equals the resolved source bytes;
- METHOD_CARD provenance contains both keys and the hash;
- no Zotero write occurred.
