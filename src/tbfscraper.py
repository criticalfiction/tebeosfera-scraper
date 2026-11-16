''' ===========================================================================

This module implements the Tebeosfera web scraping backend. It provides
functions for searching collections, fetching issue lists, and scraping
issue details from tebeosfera.com via HTTP requests and HTML parsing.

The approach follows the Bedetheque scraper's pattern: use .NET HttpWebRequest
for HTTP requests (with proper User-Agent and cookie handling), and parse HTML
with pre-compiled regular expressions.

License: Apache 2.0

=========================================================================== '''
import re
import clr
import log
import utils
from utils import sstr, strip_tags, html_decode, parse_date
from resources import Resources
from dbmodels import SeriesRef, IssueRef, Issue

clr.AddReference('System')
from System.Net import HttpWebRequest, CookieContainer

clr.AddReference('System.Drawing')
from System.Drawing import Image, Bitmap
from System.IO import StreamReader
from System.Text import Encoding
from System import Uri

# ===========================================================================
# Pre-compiled regex patterns for parsing tebeosfera.com HTML

# Issue list from collection page: <select id="jumper" ...> ... <option value="URL">NUMBER</option>
RE_JUMPER_SELECT = re.compile(
    r'<select[^>]*id="jumper"[^>]*>(.*?)</select>',
    re.DOTALL | re.IGNORECASE)

# Cover gallery on a collection page (first 50 issues); each item is
#   <button ...><img src="COVER" alt="..." .../></button>
#   <a href="/numeros/SLUG.html" ...><span>n&ordm; 3 TITLE<br>
#   <strong>12-III-2017</strong></span></a>
RE_GALLERY_ITEM = re.compile(
    r'<img\s+src="([^"]+)"[^>]*>\s*</button>\s*'
    r'<a\s+href="(?:https?://[^"/]+)?/numeros/([^"/]+?)\.html/?"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL)
# "n<ordinal sign> 3 " / "No. V1 " at the start of a gallery caption
RE_CAPTION_NUMBER = re.compile(r'^\s*n(?:\xba|\xb0|o\.?)\s*\S+\s*', re.IGNORECASE)

RE_JUMPER_OPTION = re.compile(
    r'<option\s+value="([^"]*)"[^>]*>\s*([^<]*)\s*</option>',
    re.IGNORECASE)

# Cover image: <img id="img_principal" src="URL" ...>
RE_COVER_IMG = re.compile(
    r'<img\s+id="img_principal"[^>]*\ssrc="([^"]*)"',
    re.IGNORECASE)

# Issue page: title in <div class="titulo">
RE_ISSUE_TITLE = re.compile(
    r'<div\s+id="titulo_ficha"[^>]*>\s*<div\s+class="titulo"[^>]*>(.*?)</div>',
    re.DOTALL | re.IGNORECASE)

# Author blocks: <div class="tab_datos ..."><span class="tab_subtitulo">ROLE ...</span>: ... <a ...>NAME</a> ...
RE_AUTHOR_BLOCK = re.compile(
    r'<div\s+class="row-fluid\s+tab_datos[^"]*"[^>]*>'
    r'(.*?)</div>',
    re.DOTALL | re.IGNORECASE)

# Author role label
RE_AUTHOR_ROLE = re.compile(
    r'<span\s+class="tab_subtitulo"[^>]*>(.*?)</span>',
    re.IGNORECASE)

# Author names: links with title="Display -Full Name-"
RE_AUTHOR_LINK = re.compile(
    r'<a\s+href="[^"]*"[^>]*title="([^"]*)"[^>]*>(.*?)</a>',
    re.IGNORECASE)

# Search results (from buscador_txt_post.php). Each result is a block
# starting with class="linea_resultados" containing a thumbnail, a link
# <a href="/colecciones/SLUG.html">NAME (YEAR, PUBLISHER)</a>, the display
# title in <strong>, the date range and "N numero(s)".
RE_RESULT_LINK = re.compile(
    r'<a\s+href="(?:https?://[^"/]+)?/colecciones/([^"]+?)\.html"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL)
RE_RESULT_THUMB = re.compile(r'<img[^>]*\ssrc="([^"]+)"', re.IGNORECASE)
RE_RESULT_TITLE = re.compile(r'<strong>(.*?)</strong>', re.IGNORECASE | re.DOTALL)
# "1 numero" / "60 numeros" (the u-acute may arrive as 1 or 2 chars)
RE_RESULT_COUNT = re.compile(r'(\d+)\s+n.{1,2}meros?\b', re.IGNORECASE)
# "MIEDO (2003, GLENAT)" -> year, publisher
RE_NAME_YEAR_PUB = re.compile(r'\((\d{4})\s*,\s*([^)]*)\)')

# ISSN pattern
RE_ISSN = re.compile(r'ISSN:\s*([0-9Xx\-]+)', re.IGNORECASE)

# ISBN pattern
RE_ISBN = re.compile(r'ISBN:\s*([0-9Xx\-]+)', re.IGNORECASE)

# Page count pattern (e.g. "52 pags." or "96 pp.")
RE_PAGES = re.compile(r'(\d+)\s*(?:p(?:\xe1|a)gs?|pp)', re.IGNORECASE)

# Author roles -> ComicRack credits. Matched as prefixes of the role label
# after accents, counts and case are removed ("Guionistas 2" -> "guionistas",
# "Directora de publicacion" -> "directora de publicacion"), so singular,
# plural and feminine forms all match. First match wins.
ROLE_STEMS = [
    ('guion', 'writer'),            # guionista(s)
    ('argumentista', 'writer'),
    ('historietista', 'all'),        # does all of it: see parse_authors
    ('dibujant', 'penciller'),       # dibujante(s), dibujanta
    ('portadista', 'cover_artist'),
    ('colorista', 'colorist'),
    ('entintad', 'inker'),           # entintador(a)(es)
    ('rotulista', 'letterer'),
    ('traduct', 'translator'),       # traductor(a)(es)
    ('director', 'editor'),          # director(a) de (la) publicacion
    ('comentarista', 'editor'),
    ('humorista', 'editor'),
]

# Genre/concept links in tab content
RE_CONCEPT_LINK = re.compile(
    r'<a\s+href="[^"]*/conceptos/[^"]*"[^>]*>(.*?)</a>',
    re.IGNORECASE)

# Character/personaje links
RE_CHARACTER_LINK = re.compile(
    r'<a\s+href="[^"]*/personajes/[^"]*"[^>]*>(.*?)</a>',
    re.IGNORECASE)

# ===========================================================================
# HTTP session state (cookie container for search requests)
__cookie_container = CookieContainer()


# ===========================================================================
def fetch_url(url, encoding='utf-8'):
    '''
    Fetches the content of the given URL and returns it as a decoded string.
    Uses .NET HttpWebRequest with a proper User-Agent and cookie container.

    Raises an Exception if the request fails.
    '''
    global __cookie_container
    try:
        request = HttpWebRequest.Create(url)
        request.UserAgent = Resources.USER_AGENT
        request.CookieContainer = __cookie_container
        request.Timeout = 60000
        request.AllowAutoRedirect = True

        response = request.GetResponse()
        stream = response.GetResponseStream()
        reader = StreamReader(stream, Encoding.GetEncoding(encoding))
        content = reader.ReadToEnd()
        reader.Close()
        response.Close()
        return content
    except Exception, ex:
        log.debug('fetch_url error for %s: %s' % (url, sstr(ex)))
        raise


# ===========================================================================
def post_url(url, fields, encoding='utf-8'):
    '''
    POSTs the given (name, value) pairs as a form to the URL (the way the
    site's jQuery $.post does) and returns the response as a string.
    Raises an Exception if the request fails.
    '''
    global __cookie_container
    body = '&'.join(['%s=%s' % (Uri.EscapeDataString(k), Uri.EscapeDataString(v))
                     for k, v in fields])
    data = Encoding.UTF8.GetBytes(body)
    try:
        request = HttpWebRequest.Create(url)
        request.Method = 'POST'
        request.ContentType = 'application/x-www-form-urlencoded; charset=UTF-8'
        request.UserAgent = Resources.USER_AGENT
        request.Referer = Resources.BASE_URL + '/'
        request.Headers.Add('X-Requested-With', 'XMLHttpRequest')
        request.CookieContainer = __cookie_container
        request.Timeout = 60000
        request.ContentLength = data.Length
        out = request.GetRequestStream()
        try:
            out.Write(data, 0, data.Length)
        finally:
            out.Close()

        response = request.GetResponse()
        reader = StreamReader(response.GetResponseStream(),
                              Encoding.GetEncoding(encoding))
        content = reader.ReadToEnd()
        reader.Close()
        response.Close()
        return content
    except Exception, ex:
        log.debug('post_url error for %s: %s' % (url, sstr(ex)))
        raise


# ===========================================================================
def fetch_image(url):
    '''
    Fetches an image from the given URL and returns a .NET Image object.
    Returns None if the fetch fails.
    '''
    try:
        request = HttpWebRequest.Create(url)
        request.UserAgent = Resources.USER_AGENT
        request.Timeout = 60000

        response = request.GetResponse()
        try:
            # GDI+ keeps reading the stream an Image was loaded from for as
            # long as the Image exists, so copy it into a Bitmap that owns
            # its pixels before the network stream is closed.
            loaded = Image.FromStream(response.GetResponseStream())
            try:
                return Bitmap(loaded)
            finally:
                loaded.Dispose()
        finally:
            response.Close()
    except Exception, ex:
        log.debug('fetch_image error for %s: %s' % (url, sstr(ex)))
        return None


# ===========================================================================
def full_url(path_s):
    '''
    Converts a relative URL path (like '/colecciones/foo.html') to a full
    URL (like 'https://www.tebeosfera.com/colecciones/foo.html').
    '''
    if not path_s:
        return ''
    if path_s.startswith('http'):
        return path_s
    if path_s.startswith('/'):
        return Resources.BASE_URL + path_s
    return Resources.BASE_URL + '/' + path_s


# ===========================================================================
# The site's search page (/buscador/<term>/Colecciones/) contains no results:
# its JavaScript fetches them from this endpoint, one table at a time.
SEARCH_PATH = '/neko/templates/ajax/buscador_txt_post.php'
SEARCH_TABLE = 'T3_publicaciones'   # the table the site labels "Colecciones"

# Leading/trailing articles ignored when ranking ("CAPITAN TRUENO, EL")
_ARTICLES = set(['el', 'la', 'los', 'las', 'lo', 'un', 'una', 'the'])


def search_collections(search_terms, max_results=0):
    '''
    Searches tebeosfera.com for collections matching the given search terms.
    Returns a list of SeriesRef objects, best matches first. If max_results
    is > 0 the list is cut to that length after ranking.
    Network errors are raised to the caller.
    '''
    search_terms = (search_terms or '').strip()
    if not search_terms:
        return []

    log.debug('searching tebeosfera for: %s' % search_terms)
    html = post_url(full_url(SEARCH_PATH),
                    [('tabla', SEARCH_TABLE), ('busqueda', search_terms)])
    # The endpoint answers "Error de acceso ajax (...)" if it doesn't like
    # the request (e.g. no tebeosfera Referer). Don't report that as "no
    # results".
    if html and html.strip().startswith('Error de acceso'):
        raise Exception('tebeosfera.com refused the search request: %s'
                        % html.strip()[:80])

    ranked = []
    wanted = normalize_title(search_terms)
    for ref, title in parse_search_results(html):
        ranked.append((_rank(wanted, title, ref.series_name_s),
                       utils.strip_accents(ref.series_name_s.lower()),
                       ref.volume_year_n, ref))
    ranked.sort()
    results = [r[-1] for r in ranked]
    log.debug('search found %d results' % len(results))
    if max_results > 0:
        results = results[:max_results]
    return results


# ===========================================================================
def parse_search_results(html):
    '''
    Parses the HTML returned by the search endpoint. Returns a list of
    (SeriesRef, display_title) tuples in the order the site returned them.
    '''
    results = []
    seen = set()
    if not html:
        return results

    for row in html.split('class="linea_resultados"')[1:]:
        link = RE_RESULT_LINK.search(row)
        if not link:
            continue
        slug = link.group(1)
        if slug in seen:
            continue
        seen.add(slug)

        label = strip_tags(html_decode(link.group(2))).strip()
        title_m = RE_RESULT_TITLE.search(row)
        title = strip_tags(html_decode(title_m.group(1))).strip() \
            if title_m else ''

        year, publisher = -1, ''
        yp = RE_NAME_YEAR_PUB.search(label)
        if yp:
            year = int(yp.group(1))
            publisher = yp.group(2).strip()

        count_m = RE_RESULT_COUNT.search(row)
        count = int(count_m.group(1)) if count_m else 0

        # the thumbnail comes before the link in each row
        thumb_m = RE_RESULT_THUMB.search(row, 0, link.start())
        thumb = full_url(thumb_m.group(1)) if thumb_m else None

        ref = SeriesRef(
            series_key=slug,
            series_name_s=label or title,
            volume_year_n=year,
            publisher_s=publisher,
            issue_count_n=count,
            thumb_url_s=thumb,
            url_s=full_url('/colecciones/%s.html' % slug))
        results.append((ref, title))
    return results


# ===========================================================================
def normalize_title(text):
    '''
    Lower-cases, strips accents and punctuation, and drops a leading or
    trailing article, so "El Capitan Trueno" == "CAPITAN TRUENO, EL".
    '''
    text = utils.strip_accents(text or '').lower()
    words = re.sub(r'[^a-z0-9]+', ' ', text).split()
    if len(words) > 1 and words[0] in _ARTICLES:
        words = words[1:]
    if len(words) > 1 and words[-1] in _ARTICLES:
        words = words[:-1]
    return ' '.join(words)


# ===========================================================================
def _rank(wanted, title, label):
    '''
    Ranks a search result against the normalized search terms (lower is
    better): 0 exact title, 1 title starts with the terms, 2 all words
    present, 3 anything else the site returned.
    '''
    # the label is "NAME (YEAR, PUBLISHER) -SUBTITLE-"; compare its NAME part
    base = label.split(' (')[0]
    candidates = [normalize_title(t) for t in (title, base) if t]
    if wanted in candidates:
        return 0
    for c in candidates:
        if c.startswith(wanted + ' '):
            return 1
    words = wanted.split()
    for c in candidates:
        cw = c.split()
        if words and all(w in cw for w in words):
            return 2
    return 3


# ===========================================================================
def query_issue_refs(series_ref, callback=None):
    '''
    Fetches the collection page for the given SeriesRef and returns a set of
    IssueRef objects representing all issues in that collection.
    The callback (if provided) is called as callback(complete_ratio) and
    should return True to cancel.
    '''
    results = set()
    if not series_ref or not series_ref.url_s:
        return results

    log.debug('querying issues for series: %s' % series_ref.url_s)

    try:
        html = fetch_url(series_ref.url_s)

        # Cover, title and date from the page's gallery, by issue slug. It
        # lists the first 50 issues; the rest are read from their own page
        # when previewed (see query_preview).
        gallery = {}
        for m in RE_GALLERY_ITEM.finditer(html):
            if m.group(2) not in gallery:
                title, date = _gallery_caption(m.group(3))
                gallery[m.group(2)] = (full_url(m.group(1)), title, date)
        none = (None, '', '')

        # Parse the jumper select for issue URLs and numbers
        jumper_match = RE_JUMPER_SELECT.search(html)
        if jumper_match:
            jumper_html = jumper_match.group(1)
            for opt_match in RE_JUMPER_OPTION.finditer(jumper_html):
                opt_value = opt_match.group(1).strip()
                opt_label = opt_match.group(2).strip()
                if not opt_value or not opt_label:
                    continue
                issue_url = full_url(opt_value)
                # Issue number is the label (e.g. "1", "V1", "10")
                issue_num = opt_label
                # Create a unique key from the URL
                slug = opt_value.replace('/numeros/', '').replace('.html', '')
                cover, title, date = gallery.get(slug, none)
                issue_ref = IssueRef(
                    issue_num_s=issue_num,
                    issue_key=slug,
                    title_s=title,
                    date_s=date,
                    thumb_url_s=cover,
                    url_s=issue_url)
                results.add(issue_ref)

        # No jumper (e.g. single-issue collections): take /numeros/ links
        # whose slug is the collection's slug ("miedo_2003_glenat", a single
        # issue) or starts with it plus "_" ("..._12"). Other /numeros/ links
        # on the page are sidebar promos for unrelated comics.
        if not results:
            coll_slug = series_ref.series_key
            seen = set()
            for match in re.finditer(
                    r'href="(?:https?://[^"/]+)?/numeros/([^"/]+?)\.html/?"',
                    html, re.IGNORECASE):
                slug = match.group(1)
                if slug in seen:
                    continue
                if slug == coll_slug:
                    num = '1'
                elif slug.startswith(coll_slug + '_'):
                    num = slug[len(coll_slug) + 1:].upper()
                else:
                    continue
                seen.add(slug)
                cover, title, date = gallery.get(slug, none)
                results.add(IssueRef(
                    issue_num_s=num,
                    issue_key=slug,
                    title_s=title,
                    date_s=date,
                    thumb_url_s=cover,
                    url_s=full_url('/numeros/%s.html' % slug)))

        log.debug('found %d issues for series' % len(results))

        if callback:
            callback(1.0)

    except Exception, ex:
        log.debug('query_issue_refs error: %s' % sstr(ex))
        log.debug_exc()

    return results


# ===========================================================================
def query_issue_ref(series_ref, issue_num_s):
    '''
    Attempts to find a specific IssueRef matching the given issue number
    within the given series. Returns None if no match is found.
    '''
    if not issue_num_s:
        return None
    issue_num_s = sstr(issue_num_s).strip()

    issue_refs = query_issue_refs(series_ref)
    for ref in issue_refs:
        if ref.issue_num_s == issue_num_s:
            return ref

    # Try fuzzy match (e.g. "1" matches "001")
    for ref in issue_refs:
        try:
            if int(ref.issue_num_s) == int(issue_num_s):
                return ref
        except:
            pass

    return None


# ===========================================================================
def query_issue(issue_ref, slow_data=False):
    '''
    Fetches the full issue details from tebeosfera.com and returns an
    Issue object populated with all available metadata.

    The issue_ref provides the URL to fetch. The Issue object is
    constructed from the issue_ref and then populated with data from
    the issue page.
    '''
    if not issue_ref or not issue_ref.url_s:
        return None

    log.debug('querying issue details: %s' % issue_ref.url_s)

    issue = Issue(issue_ref)

    try:
        html = fetch_url(issue_ref.url_s)
        parse_issue_page(html, issue)

        # Also fetch the collection page for series-level data
        # (publisher, genre, characters, synopsis) if available
        if issue.series_key:
            collection_url = '%s/colecciones/%s.html' % (Resources.BASE_URL,
                                                          issue.series_key)
            try:
                coll_html = fetch_url(collection_url)
                parse_collection_page_for_issue(coll_html, issue)
            except Exception, ex:
                log.debug('could not fetch collection page: %s' % sstr(ex))

    except Exception, ex:
        log.debug('query_issue error: %s' % sstr(ex))
        log.debug_exc()

    return issue


# ===========================================================================
# HTML helpers. Data values on tebeosfera nest <div>s (e.g. the "Registros"
# row), so non-greedy "(.*?)</div>" regexes cut them short. These pull out a
# whole element by counting nested <div> tags instead.
RE_DIV_TAG = re.compile(r'<(/?)div\b[^>]*>', re.IGNORECASE)
RE_LABEL_CELL = re.compile(
    r'<div\s+class="span3\s+etiqueta[^"]*"[^>]*>(.*?)</div>',
    re.IGNORECASE | re.DOTALL)
RE_VALUE_CELL = re.compile(r'\s*<div\s+class="span9\s+dato', re.IGNORECASE)
RE_TAB_HEADER = re.compile(r'<a\s+href="#(tab\d+)"[^>]*>(.*?)</a>',
                           re.IGNORECASE | re.DOTALL)
RE_COLLECTION_LINK = re.compile(
    r'<a\s+href="(?:https?://[^"/]+)?/colecciones/([^"]+?)\.html"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL)
# "12-V-1986", "X-2003" (day optional; month is a roman numeral)
RE_PUB_DATE = re.compile(
    r'(?:\b(\d{1,2})-)?\b(XII|XI|X|IX|VIII|VII|VI|V|IV|III|II|I)-(\d{4})\b')
RE_YEAR = re.compile(r'\b(1[89]\d\d|20\d\d)\b')
ROMAN_MONTHS = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6,
                'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10, 'XI': 11, 'XII': 12}


def _div_inner(html, start):
    """Inner HTML of the <div> whose '<div' is at index start ('' if none)."""
    if start < 0:
        return ''
    open_end = html.find('>', start)
    if open_end < 0:
        return ''
    depth = 1
    for m in RE_DIV_TAG.finditer(html, open_end + 1):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return html[open_end + 1:m.start()]
    return ''


def _div_by_id(html, div_id):
    m = re.search(r'<div\b[^>]*\sid="%s"' % re.escape(div_id), html or '',
                  re.IGNORECASE)
    return _div_inner(html, m.start()) if m else ''


def _div_by_class(html, css_class):
    m = re.search(r'<div\b[^>]*\sclass="[^"]*\b%s\b' % re.escape(css_class),
                  html or '', re.IGNORECASE)
    return _div_inner(html, m.start()) if m else ''


def _text(fragment):
    """Plain single-line text of an HTML fragment."""
    t = html_decode(strip_tags(fragment or ''))
    return re.sub(r'\s+', ' ', t).strip()


# Characters U+0080-U+009F are control codes, but the site sometimes stores
# Windows-1252 punctuation in them (0x97 em dash, 0x92 apostrophe, 0x85
# ellipsis...). Map them back to the characters they stand for.
RE_C1_CONTROL = re.compile(u'[\x80-\x9f]')


def _fix_cp1252(text):
    return RE_C1_CONTROL.sub(
        lambda m: m.group(0).encode('latin-1').decode('cp1252', 'ignore'), text)


def _multiline_text(fragment):
    """Plain text of an HTML fragment, keeping paragraph/list breaks."""
    t = re.sub(r'(?i)<br\s*/?>|</p>|</li>|</div>', '\n', fragment or '')
    t = _fix_cp1252(html_decode(strip_tags(t)))
    lines = [re.sub(r'[ \t\xa0]+', ' ', l).strip() for l in t.splitlines()]
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()


def _key(label):
    """'Distribuci&oacute;n:' -> 'distribucion' (also drops counts)."""
    t = utils.strip_accents(_text(label)).lower()
    return re.sub(r'[^a-z ]', '', t).strip()


def _link_texts(fragment, section=None):
    """Texts of the links in fragment, optionally only /<section>/ links."""
    if section:
        pat = r'<a\s+href="(?:https?://[^"/]+)?/%s/[^"]*"[^>]*>(.*?)</a>' % section
    else:
        pat = r'<a\b[^>]*>(.*?)</a>'
    out = []
    for t in re.findall(pat, fragment or '', re.IGNORECASE | re.DOTALL):
        t = _text(t)
        if t:
            out.append(t)
    return out


def _data_fields(block):
    """{label key: value html} for each etiqueta/dato row in block."""
    fields = {}
    for m in RE_LABEL_CELL.finditer(block or ''):
        if not RE_VALUE_CELL.match(block, m.end()):
            continue
        key = _key(m.group(1))
        if key and key not in fields:
            fields[key] = _div_inner(block, block.find('<div', m.end()))
    return fields


def _tabs(html):
    """{tab title key: pane html}, e.g. 'generos', 'personajes', 'sagas'."""
    tabs = {}
    for m in RE_TAB_HEADER.finditer(html or ''):
        title = _key(m.group(2))
        if title and title not in tabs:
            tabs[title] = _div_by_id(html, m.group(1))
    return tabs


def _merge(existing, new):
    """existing + new, without case-insensitive duplicates."""
    out = list(existing)
    seen = set(x.lower() for x in out)
    for n in new:
        if n.lower() not in seen:
            out.append(n)
            seen.add(n.lower())
    return out


def _apply_date(text, issue):
    """Sets pub day/month/year from text like '12-V-1986' or 'X-2003'."""
    m = RE_PUB_DATE.search(text or '')
    if m:
        issue.pub_year_n = int(m.group(3))
        issue.pub_month_n = ROMAN_MONTHS[m.group(2)]
        if m.group(1):
            issue.pub_day_n = int(m.group(1))
        return True
    m = RE_YEAR.search(text or '')
    if m:
        issue.pub_year_n = int(m.group(1))
        return True
    return False


def _apply_pages(text, issue):
    m = RE_PAGES.search(text or '')
    if m:
        issue.page_count_n = int(m.group(1))


def _description(html):
    """
    The page's description: the T3WISIWISI block (usually the physical
    description, "Libro de 128 paginas...") followed by the div_recension
    block (the story synopsis), when the page has one. Either may be absent.
    """
    parts = [_multiline_text(_div_by_class(html, c))
             for c in ('T3WISIWISI', 'div_recension')]
    return '\n\n'.join(p for p in parts if p)


def _format_of(value_html):
    """'Libro / Cartone' from the Formato value (first line only)."""
    first = re.split(r'(?i)<br\s*/?>', value_html or '')[0]
    links = _link_texts(first)
    text = ' / '.join(links) if links else _text(first)
    return utils.smart_title(text)


# Colour wording, matched on lower-case, accent-free text
_BW = r'blanco y negro|b/n|byn'
_COLOUR = r'(?:todo |a todo )?color(?:es)?|cuatricromia'
RE_COLOR_PART = re.compile(r'(%s|%s|bitono|duotono)\s*(?:\(([^)]*)\))?'
                           % (_BW, _COLOUR))
RE_PAGES_IN = re.compile(r'paginas?(?: interiores)?,? (?:en|a) (%s|%s)'
                         % (_BW, _COLOUR))
RE_BW_ANY = re.compile(r'\ben (?:%s)\b' % _BW)
RE_COLOUR_ANY = re.compile(r'\b(?:en|a) (?:%s)\b' % _COLOUR)


def _black_and_white(color_field_text, summary):
    """
    True if the comic's interior is black and white, False if it's colour,
    None if the page doesn't say. The "Color:" data row wins when it names
    the interior ("COLOR (portada) BLANCO Y NEGRO (interior)"); otherwise
    the description is read ("Libro de 48 paginas en color").
    """
    def norm(t):
        return re.sub(r'\s+', ' ', utils.strip_accents(t or '').lower())

    field = norm(color_field_text)
    if field:
        parts = RE_COLOR_PART.findall(field)
        for kind, where in parts:
            if 'interior' in where:
                return bool(re.match(_BW, kind)) if not kind.startswith(
                    ('bitono', 'duotono')) else None
        kinds = set('bw' if re.match(_BW, k) else k.split()[0]
                    for k, _ in parts)
        if kinds == set(['bw']):
            return True
        if kinds and kinds <= set(['color', 'colores', 'todo', 'a', 'cuatricromia']):
            return False

    text = norm(summary)
    m = RE_PAGES_IN.search(text)
    if m:
        return bool(re.match(_BW, m.group(1)))
    bw, colour = RE_BW_ANY.search(text), RE_COLOUR_ANY.search(text)
    if bw and not colour:
        return True
    if colour and not bw:
        return False
    return None


# ===========================================================================
def parse_issue_page(html, issue):
    """
    Parses an issue (numero) page and fills in the given Issue.
    Everything except the title and cover is read from the cuerpo2_ficha
    block, so the site's menus and sidebars can't leak in.
    """
    if not html:
        return

    # The title block is either just a title ("MIEDO"), or the series in
    # grey, a line break, then the issue's own title:
    #   <span ...>EL CAPITAN TRUENO</span><br>EL COMBATE POR SIGRIDSHOLM
    m = RE_ISSUE_TITLE.search(html)
    if m:
        parts = re.split(r'(?i)<br\s*/?>', m.group(1), 1)
        own = _text(parts[1]) if len(parts) > 1 else ''
        issue.title_s = utils.smart_title(own or _text(parts[0]))

    body = _div_by_id(html, 'cuerpo2_ficha')

    # Header row: "N 10 de <a href=/colecciones/SLUG.html>SERIES</a> [de 13]"
    head_m = re.search(r'<div\s+class="row-fluid\s+dato"', body, re.IGNORECASE)
    head = _div_inner(body, head_m.start()) if head_m else ''
    coll = RE_COLLECTION_LINK.search(head)
    if coll:
        issue.series_key = coll.group(1)
        issue.series_name_s = utils.smart_title(_text(coll.group(2)))

    # The first entity link is the publisher (later ones in the block are
    # the distributor and printer).
    entities = _link_texts(body, 'entidades')
    if entities:
        issue.publisher_s = entities[0]

    fields = _data_fields(body)
    _apply_date(_text(fields.get('distribucion')), issue)
    _apply_pages(_text(fields.get('paginacion')), issue)
    if fields.get('formato'):
        issue.format_s = _format_of(fields['formato'])
    registros = _text(fields.get('registros'))
    m = RE_ISSN.search(registros)
    if m:
        issue.issn_s = m.group(1)
    m = RE_ISBN.search(registros)
    if m:
        issue.isbn_s = m.group(1)

    all_rounders = parse_authors(fields.get('autores') or body, issue)

    cover = _main_cover_url(html)
    if cover:
        issue.image_urls_sl = [cover]

    synopsis = _description(html)
    if synopsis:
        issue.summary_s = synopsis

    issue.black_and_white = _black_and_white(
        _text(fields.get('color')), issue.summary_s)
    # historietistas also coloured it, unless it's black and white
    if all_rounders and issue.black_and_white is not True:
        issue.colorists_sl = _merge(issue.colorists_sl, all_rounders)

    parse_tabs(html, issue)
    issue.webpage_s = issue.url_s


# ===========================================================================
def _credit_type(role_label):
    """'Directora de publicacion 1' -> 'editor' (None if not a credit)."""
    key = _key(role_label)
    for stem, credit in ROLE_STEMS:
        if key.startswith(stem):
            return credit
    return None


def _credit_name(title_attr, display_html):
    """
    The best-cased form of an author's name. Links look like
      <a title="DuBouillon -Alain Bouillon-">DUBOUILLON</a>
    so the part of the title before " -" is the same name with the site's
    own casing; use it unless it's ALL CAPS too, then title-case the text.
    """
    display = _text(display_html)
    if not display:
        return ''
    alias = html_decode(title_attr or '').split(' -')[0].strip()
    same = utils.strip_accents(alias).lower() == utils.strip_accents(display).lower()
    if alias and same and not utils.is_all_caps(alias):
        return alias
    return utils.smart_title(display)


def parse_authors(html, issue):
    """
    Adds the credits in the issue's "Autores" rows to the Issue. Each row is
      <div class="row-fluid tab_datos ..."><span class="tab_subtitulo">ROLE
      <span class="peque">N</span></span>: <a title="...">NAME</a>, ...
    """
    lists = {'writer': ['writers_sl'], 'penciller': ['pencillers_sl'],
             'cover_artist': ['cover_artists_sl'], 'colorist': ['colorists_sl'],
             'inker': ['inkers_sl'], 'letterer': ['letterers_sl'],
             'editor': ['editors_sl'], 'translator': ['translators_sl'],
             # A historietista does all the work on a comic (or on their
             # strip in an anthology): script, pencils, inks, letters and
             # colour. Colour is added by the caller, once it knows whether
             # the comic is black and white.
             'all': ['writers_sl', 'pencillers_sl', 'inkers_sl', 'letterers_sl']}
    all_rounders = []
    for block in RE_AUTHOR_BLOCK.finditer(html or ''):
        role = RE_AUTHOR_ROLE.search(block.group(1))
        credit = _credit_type(role.group(1)) if role else None
        if not credit:
            continue
        names = [n for n in (_credit_name(m.group(1), m.group(2))
                             for m in RE_AUTHOR_LINK.finditer(block.group(1))) if n]
        for attr in lists[credit]:
            setattr(issue, attr, _merge(getattr(issue, attr), names))
        if credit == 'all':
            all_rounders = _merge(all_rounders, names)
    return all_rounders


# ===========================================================================
def parse_tabs(html, issue):
    """
    Adds genres (GENEROS tab) and characters (PERSONAJES tab) to the Issue.
    Tabs are found by their titles; their order differs between pages.
    """
    tabs = _tabs(html)
    if 'generos' in tabs:
        issue.genres_sl = _merge(issue.genres_sl,
                                 _link_texts(tabs['generos'], 'conceptos'))
    if 'personajes' in tabs:
        issue.characters_sl = _merge(issue.characters_sl, [
            utils.smart_title(c)
            for c in _link_texts(tabs['personajes'], 'personajes')])


# ===========================================================================
def parse_collection_page_for_issue(html, issue):
    """
    Fills in series-level data from a collection page for anything the
    issue page didn't have: publisher, year, page count, format, genres,
    characters and synopsis.
    """
    if not html:
        return

    if not issue.publisher_s:
        # e.g. "GRUPO EDITORIAL BRUNO : SALVAT" -> the last one is the label
        entities = _link_texts(_div_by_id(html, 'cuerpo1_ficha'), 'entidades')
        if entities:
            issue.publisher_s = entities[-1]

    fields = _data_fields(_div_by_id(html, 'cuerpo2_ficha'))
    if issue.pub_year_n == -1:
        _apply_date(_text(fields.get('fechas')), issue)
    if issue.page_count_n == -1:
        _apply_pages(_text(fields.get('paginacion')), issue)
    if not issue.format_s and fields.get('formato'):
        issue.format_s = _format_of(fields['formato'])

    parse_tabs(html, issue)

    synopsis = _description(html)
    if not issue.summary_s and synopsis:
        issue.summary_s = synopsis

    # The issue page didn't say; try the collection's Color row and text.
    if issue.black_and_white is None:
        issue.black_and_white = _black_and_white(
            _text(fields.get('color')), synopsis)


# ===========================================================================
def _main_cover_url(html):
    """
    The page's own cover. Looked for only inside div_imagen_principal: the
    sidebar's "novedades" images use the same id="img_principal", so a page
    without a cover would otherwise get an unrelated comic's.
    """
    m = RE_COVER_IMG.search(_div_by_id(html, 'div_imagen_principal'))
    return full_url(m.group(1)) if m else None


# Image files live at  .../T3_numeros/a/b/NAME.jpg  with resized copies at
#                      .../T3_numeros/a/b/NAME/w-200_NAME.jpg  (also R-100_,
# a 100x100 crop, which is what search results link to).
RE_SIZED_IMAGE = re.compile(
    r'^(?P<dir>.*)/(?P<name>[^/]+)/(?:R|w)-\d+_(?P=name)(?P<ext>\.\w+)$')
RE_FULL_IMAGE = re.compile(r'^(?P<dir>.*)/(?P<name>[^/]+?)(?P<ext>\.\w+)$')


def _preview_urls(url):
    """URLs to try for a preview: the 200px-wide copy, then the original."""
    m = RE_SIZED_IMAGE.match(url) or RE_FULL_IMAGE.match(url)
    if not m:
        return [url]
    d, name, ext = m.group('dir'), m.group('name'), m.group('ext')
    out = ['%s/%s/w-200_%s%s' % (d, name, name, ext), '%s/%s%s' % (d, name, ext)]
    if url not in out:
        out.append(url)
    return out


_MONTH_ABBR = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def display_date(year, month=-1, day=-1):
    """'12 Mar 2017', 'Oct 2003', '1986', or '' (each part may be -1)."""
    if year is None or year < 0:
        return ''
    if 1 <= (month or -1) <= 12:
        text = '%s %d' % (_MONTH_ABBR[month - 1], year)
        return ('%d %s' % (day, text)) if (day or -1) > 0 else text
    return str(year)


def _display_date_text(text):
    """Display date from a site date like '12-III-2017' or 'X-2003'."""
    found = Issue(IssueRef('', 'date'))
    if _apply_date(text, found):
        return display_date(found.pub_year_n, found.pub_month_n, found.pub_day_n)
    return ''


def _gallery_caption(caption_html):
    """
    (title, display date) from a gallery caption such as
    'n<ordinal> 3 &iexcl;EL SE&Ntilde;OR DE LA GUERRA!<br><strong>12-III-2017</strong>'.
    """
    parts = re.split(r'(?i)<br\s*/?>', caption_html or '', 1)
    title = RE_CAPTION_NUMBER.sub('', _text(parts[0]))
    date = _display_date_text(_text(parts[1])) if len(parts) > 1 else ''
    return utils.smart_title(title), date


def query_preview(ref):
    """
    Data for the preview beside the series/issue lists: (image, details).
    image is a .NET Image of the cover, or None if the comic has none.
    details is None, unless the ref's own page had to be read to find the
    cover; then it's {'title': ..., 'date': ...} for an IssueRef, so the
    issue list can show them for issues the gallery didn't include.
    Slow (network): call it off the UI thread.
    """
    url, details = ref.thumb_url_s, None
    if not url and ref.url_s:
        html = fetch_url(ref.url_s)
        url = _main_cover_url(html)
        if isinstance(ref, IssueRef):
            issue = Issue(ref)
            parse_issue_page(html, issue)
            details = {'title': issue.title_s,
                       'date': display_date(issue.pub_year_n,
                                            issue.pub_month_n, issue.pub_day_n)}
    if not url:
        return None, details
    for candidate in _preview_urls(url):
        img = fetch_image(candidate)
        if img is not None:
            return img, details
    return None, details


# ===========================================================================
def get_db_name():
    '''Returns the name of this data source.'''
    return 'Tebeosfera'
