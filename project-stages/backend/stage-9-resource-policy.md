# B9.1 resource media and delivery policy — approved

## Owner override — Interactive HTML5 uploads, 2026-10-09

Interactive alone now accepts complete self-contained UTF-8 `.html`/`.htm` files up to 2 MiB through the protected admin upload/draft/review/publication flow. Inline CSS/JavaScript and embedded assets run in an opaque-origin `allow-scripts` iframe with restrictive CSP; no network, parent/session access, nested frames, popups or forms. Authorized delivery is JSON, never an executable HTML signed URL on the application origin. Uploaded HTML requires accessibility/keyboard notes and existing rights checks. Image/Video rules and existing approved external Interactive links are unchanged. Multi-file executable packages, model-authored response HTML and arbitrary remote iframe embedding remain excluded. See [implementation and checks](stage-9-interactive-html5.md). This overrides earlier blanket HTML-upload exclusion only within this Interactive workflow.

Status: **approved by the project owner** (2026-09-28). B9.2–B9.10 are implemented in development. Publication enforces rights, availability and accessibility checks; this policy approval alone does not publish resources. B9.11 live private-storage and approved-asset acceptance remains.

## Approved MVP choices

| Decision | Proposed rule | Implementation consequence |
| --- | --- | --- |
| Uploaded formats | JPEG, PNG and WebP images; MP3 and M4A audio; MP4 and WebM video. Animation uses video or a reviewed in-app experience. Exclude SVG, HTML, scripts, archives, executables and arbitrary interactive packages. | Check extension, declared MIME and inspected content. Decode images; serve fixed safe Content-Type with nosniff. |
| Upload limits | 10 MiB/image, 25 MiB/audio, 100 MiB/video; one binary per resource version. Captions can initially be text metadata. | Stream with bounds, reject oversize before commit, clean failed objects; configure server limits with these defaults. |
| External links | HTTPS direct media from an explicit host allowlist. Reject credentials, localhost/private-network hosts and redirects to unapproved hosts. | Validate canonical host and port at save and delivery; no unsafe server fetch. |
| Interactive experiences | Only reviewed application-owned IDs, initially gravity-lab, may embed in the sandboxed viewer. Reviewed external experiences may open in a separate page after explicit allowlisting. | No arbitrary HTML/JS upload or iframe. |
| Durable storage | Metadata and associations in PostgreSQL; uploaded binaries in a private Supabase Storage bucket when deployed. Private backend-local storage is development-only. Store opaque object keys, never filesystem paths/public URLs. | Add storage adapter and verify object availability before publication. |
| Delivery and expiry | Authenticate and check current publication/path eligibility on every delivery request. Issue five-minute signed object URLs; refresh through that endpoint. | Unpublish blocks new URLs immediately; issued URLs can last five minutes. Use an authenticated proxy if immediate revocation is required. |
| Distribution rights | Admin records owned/licensed/permission basis, rights holder/source, distribution scope and required attribution/license terms. Publish requires affirmative authorization. | Add rights metadata and publication checks; technical validation cannot prove ownership. |
| Accessibility | Images/diagrams require meaningful alt text. Audio/video carry captions/transcript when available, or an explicit reason they are unavailable. | Validate at publish and return accessibility metadata to viewers. |

## Configuration and publication gates

- The approved formats and limits exclude PDF. A later PDF addition needs its own viewer and validation decision.
- No external media host or external interactive experience has been named. The host allowlist defaults to empty; external links cannot be saved until explicitly configured.
- Private Supabase Storage and the five-minute residual signed-URL window are approved. A private deployed bucket still needs configuration and live verification before deployment.
- An admin records the approved distribution basis and evidence/reference for publication. Drafts may omit them; B9.3 must reject publication until the required fields are present. No sample asset is presumed licensed.

## B9 execution handoff

1. B9.2: typed metadata, rights fields, private storage adapter, bounded upload and URL validation.
2. B9.3: versioned draft/edit/publish/unpublish and filters; verify rights, object presence, association and accessibility.
3. B9.4–B9.5: exact authorized lookup, refreshable delivery, withdrawn and missing-asset outcomes.
4. B9.6/B9.11: real cards/viewers, duplicate-safe open/play events and access/upload/expiry tests.

Existing resource tables provide a starting point. Their published flag and storage-key/external-URL check do not enforce this policy. The frontend gravity-lab allowlist is a reviewed local demonstration, not permission to host arbitrary interactive files.


## Owner-requested resource workflow updates (2026-10-03)

- The later GIF enhancement adds validated `image/gif` animations under the 10 MiB image limit, with meaningful descriptions, optional captions, original-byte storage and accessible playback/reduced-motion controls.
- Media creation and publication are independent of mapping. Unmapped media may be saved and published, but has no learner placement or delivery eligibility until a valid mapping exists in a published curriculum.
- Mapping changes use current resource versions and valid path IDs, save atomically, and preserve publication. A published resource may be fully unmapped without being unpublished.
- Delete removes a resource from the active library, unpublishes it and removes associations. Deletion records, ownership records, media and historical references are retained, including shared files. There is no restore action or automatic purge policy in this implementation. Confirmation states this explicitly. Existing signed cloud URL expiry rules still apply.

## Owner-requested external video and strict playback (2026-10-03)

- External video is a distinct URL-only type with explicit YouTube/Vimeo adapters. Other hosts, iframe HTML, unsafe links and private URL formats are rejected. Public metadata can be saved provisionally; publication requires provider API verification of public visibility and embedding in addition to rights/accessibility requirements.
- Provider verification is separate from student playback approval. No YouTube or Vimeo configuration is currently approved for the required navigation-free student mode. Published and mapped entries remain blocked for learner lookup/recommendations/delivery; mapping cannot override this restriction. Legacy provider URLs cannot bypass the policy under another resource type.
- Admin preview is metadata/thumbnail only and explains the limitation. No provider iframe, external-site fallback, branding overlay, extracted stream or iframe/CSP permission relaxation is introduced. A licensed uploaded video is the approved in-app alternative.
- Vimeo settings depend on owner configuration and plan. The current block is an absence of strict approval, not a claim that every future Vimeo configuration is impossible. Any additional provider/configuration requires implemented validation and demonstrated compliance before enabling student playback.

## Owner override: keyless standard video playback (2026-10-03)

This later owner instruction supersedes the strict external-video section above. YouTube/Vimeo no longer require provider API credentials for saving or publication. Fixed HTTPS oEmbed endpoints validate available public metadata; this does not establish every visibility or embedding restriction. Publication still checks rights, accessibility, availability and current resource version. Unsafe URLs, unsupported providers and private URL formats remain rejected.

Standard YouTube/Vimeo embeds are enabled in admin preview and authorized learner delivery. Provider branding, recommendations and links may navigate externally; the owner has accepted that limitation for now. FLAME does not add external-site buttons or redirect on errors. Player failures stay in the viewer, with retry/close controls. CSP limits frames to FLAME, YouTube and Vimeo. Other providers still require explicit adapters.

The ten existing FlipLecture Grade 1 Science Gravity samples are mapped explicitly to every current path in the Gravity (Forces & Motion) category: one topic and eight subtopics, nine associations each (90 total). All remain unpublished drafts; mapping does not assert rights or teacher suitability. See `work/keyless-video-category-mapping.md` for verification.
