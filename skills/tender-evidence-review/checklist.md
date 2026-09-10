# Independent Reviewer Checklist — tender-evidence-review v1.2 (Draft)

Both machine validation and human re-reading are required; neither substitutes for the other.

## Pre-review

- [ ] Pack contains all six JSON products (project-profile, file-manifest, requirements, coverage, findings, review-report)
- [ ] `identity_ok` in output: all six contract names map to `true` (it is a dict, not a single boolean)
- [ ] Empty stdout is not success — always check exit code

## Bilateral evidence re-read (for each `severity=potential_rejection` OR `severity=high`, regardless of `certainty`)

- [ ] **Tender-side**: Re-read requirement matrix entry → source file page/paragraph
  - [ ] `source_file_id` resolves to a file in manifest
  - [ ] Compare `source_quote` against actual text
  - [ ] Record: locator → result → consistent/inconsistent → reason
- [ ] **Bid-side**: Re-read bid document location
  - [ ] `bid_evidence[].file_id` resolves to a file in manifest
  - [ ] Compare `observation` against actual content
  - [ ] Record: locator → result → consistent/inconsistent → reason
- [ ] If `evidence_type=absence`:
  - [ ] `searched_coverage_item_ids` is non-empty
  - [ ] Each referenced item exists, is `checked`, belongs to same `file_id`
  - [ ] Page numbers within `physical_pages`

## Negative example search

- [ ] Check addenda, exception clauses, other pages
- [ ] If negative example holds → record downgrade/withdrawal

## Calculation verification

- [ ] Re-compute `expression` with real decimal calculator
- [ ] Verify inputs, units, formula, rounding, result

## Image observation validation

- [ ] Actual viewing record exists (not placeholder)
- [ ] `readability` matches actual state
- [ ] `file_id` points to an actual source file in manifest (PDF, DOCX, images, any format)
- [ ] `location` within `physical_pages`

## Coverage closure re-count

- [ ] `checked` / `failed` / `unchecked` counts match summary
- [ ] Every failed/unchecked item has non-empty `reason`
- [ ] Every checked item has `method` OR `location`
- [ ] `coverage_file_ids[]` covers full manifest minus excluded with reasons

## Version binding (G06)

- [ ] `file-manifest.manifest_id` = `requirements.manifest_id` = `coverage.manifest_id` = `findings.manifest_id` = `report.inputs_version.manifest_id`
- [ ] `project-profile` has no `manifest_id`

## Report conclusion (G03)

- [ ] `coverage_closed=false` → `conclusion` is `partial_only` or `cannot_conclude`
- [ ] `conclusion=pass` requires all complete, no failures, no unchecked

## Review status (R5)

- [ ] Author pack: no `reviewed_*`
- [ ] `review_summary.notes` uses complete `issue_id`, may reference `limitations`
- [ ] No invented `review_reason`/`review_note` fields

## Path safety (G07)

- [ ] No backslashes at any position in `relative_path`
- [ ] No absolute / drive / UNC / `..` / NUL / empty

## Machine vs human scope

- [ ] Machine enforces R2/G05 bilateral for `potential_rejection` only
- [ ] Human re-reads both `potential_rejection` AND `high` regardless of `certainty`
- [ ] `observation_method` non-empty (machine gate)
- [ ] No machine rule currently enforces bilateral for `high`

## Final recording

- [ ] Complete `issue_id` in review notes (not substring)
- [ ] "Not read" never written as "not provided"
