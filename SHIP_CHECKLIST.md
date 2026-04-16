# Ship Checklist — Zenodo release

Complete these steps in order. Total time: ~10 minutes.

## 1. Enable GitHub–Zenodo webhook (one-time, 2 min)

1. Visit https://zenodo.org/account/settings/github/
2. Find `shizhigu/ct-endpoint-audit` in the repository list
3. Toggle the switch to **ON**

(This is a separate switch from the one you already enabled for
`faers-lit-filter`; each repo is a separate webhook subscription.)

## 2. Trigger DOI minting (1 min)

Because the v1.0.0 release was created *before* enabling the webhook,
Zenodo will not auto-detect it. Two options:

### Option A: re-release v1.0.0 (cleaner)

```bash
gh release delete v1.0.0 --yes
git tag -d v1.0.0
git push origin :refs/tags/v1.0.0
git tag -a v1.0.0 -m "v1.0.0"
git push origin v1.0.0
gh release create v1.0.0 paper/main.pdf --title "v1.0.0" --notes-file /tmp/release-notes.md
```

### Option B: bump to v1.0.1 (simpler)

```bash
git tag -a v1.0.1 -m "v1.0.1 — Zenodo DOI mint"
git push origin v1.0.1
gh release create v1.0.1 paper/main.pdf --title "v1.0.1 — Zenodo DOI mint" \
    --notes "Trigger DOI minting via GitHub-Zenodo webhook. No code changes."
```

## 3. Wait for Zenodo webhook (2-5 min)

Check https://zenodo.org/account/settings/github/ — the
`ct-endpoint-audit` row should show the new release and a DOI badge.

If it doesn't appear:
- Check webhook delivery at
  https://github.com/shizhigu/ct-endpoint-audit/settings/hooks
  → latest delivery should be `release.released` with HTTP 200
- Fall back to manual upload: `/tmp/ct-endpoint-audit-v1.0.0.zip`
  at https://zenodo.org/uploads/new (copy metadata from the
  FAERS paper record)

## 4. Fill in DOI (1 min — send to me)

Once you have the DOI (format `10.5281/zenodo.XXXXXXX`), send it back
and I will back-fill it into:

- [ ] `README.md` (DOI badge + BibTeX citation)
- [ ] `CITATION.cff` (`url` and `doi` fields)
- [ ] `paper/main.tex` (Data and code availability section)
- [ ] GitHub release description
- [ ] `STATE.md` in the parent project

Then I will recompile the PDF and push a final commit.

## 5. Portfolio update (optional, 5 min)

Consider adding the DOI to:
- LinkedIn profile / featured section
- ORCID (https://orcid.org/0009-0009-3036-2268)
- Resume/CV publications section
- Substack / personal site

## Placeholder values to replace after DOI mint

- `10.5281/zenodo.XXXXXXX` appears in:
    * `README.md` lines referencing DOI badge and BibTeX
    * `CITATION.cff` `url` field
    * `paper/main.tex` Data and code availability section
