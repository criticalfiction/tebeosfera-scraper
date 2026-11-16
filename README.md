# Tebeosfera Scraper for ComicRack

A ComicRack plugin that scrapes comic book metadata from [tebeosfera.com](https://www.tebeosfera.com), the Spanish comic encyclopedia.

## Overview

Tebeosfera is a comprehensive Spanish-language database of comics, graphic novels, and popular graphic culture. Unlike other comic databases (e.g., Comic Vine), tebeosfera.com does not provide a REST API. This plugin scrapes the website's HTML pages directly to extract metadata for Spanish-language comics.

The plugin's UI follows the pattern established by the [Comic Vine Scraper](https://github.com/cbanack/comic-vine-scraper), with web scraping techniques inspired by the [Bedetheque Scraper](https://github.com/maforget/Bedetheque-Scrapper-2).

## Features

- Search tebeosfera.com for comic series by name
- Interactive series and issue selection dialogs
- Scrapes the following metadata:
  - Series name, issue number, title
  - Writers (Guionistas), Pencillers (Dibujantes), Cover Artists (Portadistas)
  - Inkers (Entintadores), Colorists (Coloristas), Letterers (Rotulistas)
  - Editors (Directores de publicación), Translators (Traductores)
  - Publisher, publication date, page count, format
  - Summary/synopsis, genre, characters
  - Cover image (for fileless books)
  - ISSN, web page URL
- Configurable: choose which fields to scrape, overwrite behavior, etc.
- Persistent geometry and settings across sessions
- Automatic rescrape of previously scraped books

## Installation

1. Build the plugin (see below) to produce a `.crplugin` file
2. In ComicRack, go to **Edit > Preferences > Scripts**
3. Click **Install** and select the `.crplugin` file
4. Restart ComicRack

## Usage

1. Select one or more comic books in ComicRack
2. Right-click and choose **Tebeosfera Scraper** (or use the metadata editor)
3. The scraper will:
   - Show a search dialog with the book's series name
   - Search tebeosfera.com for matching collections
   - Show a list of matching series for selection
   - Show a list of issues for the selected series
   - Scrape and apply the metadata to the selected book

## Configuration

Access via **File > Automation > Tebeosfera Scraper Config** (or the ConfigScript hook).

- **Fields tab**: Toggle which metadata fields to scrape
- **Behavior tab**: Overwrite existing data, auto-choose series, fast rescrape, etc.
- **Advanced tab**: Advanced settings (scrape delay, max search results, publisher aliases, ignored publishers)

## Building

### Prerequisites

- Python 2.7 (for the build script; the plugin itself runs on IronPython 2.7 embedded in ComicRack)

### Build

```bash
python build.py
```

This creates `build/TebeosferaScraper-<version>.crplugin`.

## Architecture

The plugin is written in IronPython 2 and uses .NET WinForms for the UI. Key components:

| File | Purpose |
|------|---------|
| `TebeosferaScraper.py` | Entry point with ComicRack hook annotations |
| `scrapeengine.py` | Main processing loop (search → series → issue → apply) |
| `tbfscraper.py` | Web scraping backend (HTTP + regex HTML parsing) |
| `dbmodels.py` | Data models (SeriesRef, IssueRef, Issue) |
| `comicbook.py` | ComicRack book wrapper with metadata mapping |
| `configuration.py` | Settings persistence |
| `searchform.py` | Search terms input dialog |
| `seriesform.py` | Series selection dialog (DataGridView) |
| `issueform.py` | Issue selection dialog (DataGridView) |
| `configform.py` | Configuration dialog (tabbed) |
| `comicform.py` | Status window (persistent during scrape) |
| `utils.py` | Utility functions |
| `log.py` | Debug logging |
| `resources.py` | Path constants |

### Web Scraping Approach

The plugin uses .NET `HttpWebRequest` to fetch HTML pages from tebeosfera.com, then parses them with pre-compiled regular expressions. Key URL patterns:

- **Search**: `/buscador/{term}/Colecciones/` (with session cookie handling)
- **Collection page**: `/colecciones/{slug}.html`
- **Issue page**: `/numeros/{slug}_{number}.html`
- **Issue list**: Parsed from the collection page's `<select id="jumper">` element
- **Alphabetical fallback**: `/buscador-alfabetico/colecciones/{letter}.html`

## License

Apache 2.0 — see [LICENSE](LICENSE)
