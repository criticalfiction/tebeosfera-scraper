# Changelog

## 0.9.1

### Fixed

- Issues were not found for collections whose issue slug ends in a different
  publisher than the collection slug. For example, the collection
  `36_de_la_madeleine_los_2026_cartem` lists its issue as
  `36_de_la_madeleine_los_2026_panini`. For collections with no issue
  dropdown, `query_issue_refs` only accepted `/numeros/` links that started
  with the collection slug, so it rejected that issue. It now falls back to
  the issue gallery on the collection page, which lists only that
  collection's own issues. The issue number is read from the gallery caption.
  Behavior is unchanged when the dropdown or the slug match already finds
  issues.
- Publisher names shown in all caps (for example `PLANETA DE AGOSTINI`) are
  now converted to title case (`Planeta de Agostini`). This applies to series
  search results, issue pages, and the collection page fallback. Words of 2 to
  3 letters stay upper-case, since they are usually acronyms (`DC`, `ECC`,
  `EDT`). Names that already contain lower-case letters are not changed. The
  `PUBLISHER_ALIAS` setting still applies.

### Changed

- `src/tbfscraper.py`: added `_publisher_name()` and extended
  `query_issue_refs()`.
