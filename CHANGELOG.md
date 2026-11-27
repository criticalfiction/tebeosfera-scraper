# Changelog
## 0.9.2
### Added
- New **Credits** setting, "Authors whose signature differs from their real
  name are credited as". Some authors sign their work with a name other than
  their own (a colorist signing as `1ver2anes` is really Verane Otero). The
  choices are Signature (the default, as before), Real name,
  `Signature (Real name)` and `Real name (Signature)`. It applies to every
  credit role. When the page gives no different real name, the name is used
  as it is.
- Two more choices for that setting, `Signature (Real name) [Smart]` and
  `Real name (Signature) [Smart]`, which avoid repeating what the other part
  already says. The real name stops at the last word the signature uses,
  dropping surnames it doesn't need (`Monteys (Albert Monteys)`, not
  `Monteys (Albert Monteys Homar)`; `Juan Carlos Perez (Pepo Perez)`). It
  is never cut at a given name: the first name, or a name with two or more
  parts still after it (`Daniel` in Jorge Daniel Fernandez Castany).
  Particles count as part of the surname after them (`Del Vas`,
  `San Martin`). When the signature adds nothing to the name, it's left out
  (`Fermin Solis`, `Manel Fontdevila`). A signature that is just the first
  name (`Guillermo`) or isn't taken from the real name (`JMV`) keeps the
  whole real name and both parts. A short form of a surname is kept
  (`Jose Antonio Fernandez (Fer)`).
- `Ilustrador` / `Ilustradora` credits are now read as penciller, the same
  as `Dibujante`. The "use penciller as inker / cover artist / colorist"
  settings apply to them.
### Fixed
- Text on the Behavior and Credits tabs of the configuration dialog could be
  cut off on scaled displays: the font grew with the display but the fixed
  label and checkbox sizes didn't, so a label hid its last line ("credited
  as:") and a checkbox lost the end of its text. Both tabs now stack their
  controls, giving each label and checkbox the height its wrapped text
  needs and moving the ones below down. At 100% the layout is unchanged.
- Titles were run together when the issue page's heading has a note on
  the edition in a nested block, as in `CALAVERA LUNAR` +
  `especial 25 aniversario`, which gave `CALAVERA LUNARespecial 25
  aniversario`. The heading is now read as a whole. The text before the
  note is the series name, so the note alone is the title:
  `Especial 25 aniversario`. After an issue's own title, a note is added in
  brackets.
- Initials in author names stay upper-case: `JMV`, not `Jmv`, and
  `Jose A. Serrano`, not `Jose a. Serrano`. A word with no vowels is taken
  as an initialism, and a letter with a full stop as an initial. The
  connecting words `y`, `i` and `e` stay lower-case (`Ortega y Gasset`).
  Titles and series names are cased as before.
- Author names listed with a trailing dash (`NEVIL -`) no longer keep the
  dash, so the credit is `Nevil` instead of `Nevil -`.
- The publisher was wrong for collections published under a group and an
  imprint, listed as `Penguin Random House Grupo : Reservoir Books`. The
  scraper used the first link (the group). It now reads the publisher row
  and uses the last link (the imprint, `Reservoir Books`), as the
  collection page fallback already did.
### Changed
- `src/tbfscraper.py`: `query_issue()`, `parse_issue_page()` and
  `parse_authors()` take a `name_style` argument; added `_real_name()`,
  `_name_parts()`, `_match_signature()` and `_smart_credit()`. The issue
  title is read by `_issue_title()`; `RE_ISSUE_TITLE` was removed.
  `src/utils.py`: added `smart_name()`, used for author names.
  `src/configform.py`: added `stack_layout()`.
  `src/configuration.py`, `src/configform.py` and `src/scrapeengine.py`
  carry the new `credit_name_style_n` setting.

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
