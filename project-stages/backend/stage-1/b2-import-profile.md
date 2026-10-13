# B2 workbook import profile

The accepted source is `Curriculum Documents/Fliplecture Curriculum Grade 1 to 5.xlsx` (SHA-256 `962c8f118ead8e9dfa20dc64f2c606578d7ad6bc91d995562848c8bd454868da`). This identifies the reviewed version, not a hard-coded restriction on later curricula. The upload targets an existing curriculum whose normalized code is `fliplecture`; the workbook never creates that curriculum.

## Sheet and row mapping

For this workbook, the six visible sheets `Grade KG`, `Grade 1`, `Grade 2`, `Grade 3`, `Grade 4`, and `Grade 5` map to Level values with the same names. A future import explicitly selects sheets and their expected Level values during preview. Every selected sheet has the nine headers in the import contract, in order. `Learning Outcome` may also be absent as an optional column. Unselected reference sheets are ignored. A selected sheet cannot be hidden, empty, or contain merged cells.

The first row is the header. A data row requires Curriculum Code, Level, Subject, Domain, Topic, and Subtopic. Category, Learning Outcome, and Source URL may be blank. A blank Category means a topic directly under the Domain. Topic-only paths are invalid under the 2026-09-26 product rule. Equal text in Domain and Category is valid and creates two separate database nodes; Category is hidden in student navigation but its ID remains in teaching context. Completely blank rows after the last populated row, including styled rows, are ignored. A blank row between populated rows is an error.

The five repeated full paths on Grade 1 rows 32–36 and 37–41 are accepted. Preview counts their second occurrences as duplicates; commit creates/reuses each distinct path once. A duplicate with conflicting nonblank topic-level Learning Outcomes is invalid. Source URL and embedded Excel hyperlink targets are never fetched; only cell display text is parsed. Hyperlink metadata is ignored.

## Normalization and limits

Text is Unicode NFC normalized, trimmed, and internal whitespace runs collapse to one space. Display text keeps its case; matching keys use Unicode casefold of the normalized text. Each node is matched under its full parent path and curriculum, so identical names in different branches or curricula remain distinct. Curriculum Code matching uses the same text normalization. A blank optional cell is `None`, not an empty named node. Import omissions never delete existing nodes and never imply a rename.

Limits for the B2 parser: `.xlsx` only; 10 MiB uploaded ZIP; 50 MiB total expanded ZIP entries; 1,000 ZIP entries; 32 selected sheets; 20,000 populated rows per workbook; 25,000 worksheet rows scanned per selected sheet. Curriculum Code and generated Level Code are limited to 80 characters, hierarchy names to 255, and Learning Outcome to 2,000, matching the database. Reject formulas, error cells, non-text values in import columns, macros, external links, embedded objects, duplicate headers, missing required values, mismatched curriculum codes or sheet levels, and extra populated columns. Bound preview row errors and never include raw submitted values in API error envelopes.

The reviewed workbook has 1,726 populated rows, 5 repeated full paths, no outcomes or Source URL values, no formulas, no internal blank rows, and no missing required cells. It is accepted as the final B2 source with its repeated paths handled by the duplicate rule above. This profile records B2.1 decisions; parser, preview, commit, and history implementation remain separate steps.

## Student hierarchy rule — 2026-09-26

My Learning displays Curriculum → Level → Subject → Domain → Topic → Subtopic. Category is imported and stored for exact topic ancestry and LLM context, but never rendered as a student-facing row, filter, or breadcrumb. Every imported Topic path must end in a real Subtopic. The database keeps nullable category_id and draft Topic records so administration can build a hierarchy in stages; publication must reject Topics with no Subtopics. No Supabase schema migration is needed for this display/validation rule.
