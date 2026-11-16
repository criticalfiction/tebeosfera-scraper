''' ===========================================================================

This module defines the core data model classes used by the Tebeosfera
Scraper: SeriesRef, IssueRef, and Issue. These are adapted from the
comic-vine-scraper's dbmodels.py.

License: Apache 2.0

=========================================================================== '''
import re
import utils
from utils import sstr, clamp, is_number


# ===========================================================================
class SeriesRef(object):
    '''
    An immutable, lightweight reference to a series (collection) on
    tebeosfera.com.  It contains just enough data to uniquely identify and
    display the series in the UI; the full details are fetched later via
    the scraper backend.

    series_key       -- a string key that uniquely identifies this series
                        on tebeosfera.com (typically the URL slug)
    series_name_s    -- the display name of the series
    volume_year_n    -- the year this series started, or -1 if unknown
    publisher_s      -- the publisher name, or ''
    issue_count_n    -- the number of issues in this series, or 0 if unknown
    thumb_url_s      -- URL to a thumbnail image, or None
    url_s            -- the full URL to the collection page on tebeosfera.com
    '''

    def __init__(self, series_key, series_name_s='', volume_year_n=-1,
                 publisher_s='', issue_count_n=0, thumb_url_s=None,
                 url_s=''):
        self.__series_key = sstr(series_key)
        self.__series_name_s = series_name_s or ('Series ' + sstr(series_key))
        self.__volume_year_n = self.__parse_int(volume_year_n, -1)
        self.__publisher_s = publisher_s or ''
        self.__issue_count_n = self.__parse_int(issue_count_n, 0)
        self.__thumb_url_s = thumb_url_s
        self.__url_s = url_s or ''

    # --- public read-only properties ---
    @property
    def series_key(self):
        return self.__series_key

    @property
    def series_name_s(self):
        return self.__series_name_s

    @property
    def volume_year_n(self):
        return self.__volume_year_n

    @property
    def publisher_s(self):
        return self.__publisher_s

    @property
    def issue_count_n(self):
        return self.__issue_count_n

    @property
    def thumb_url_s(self):
        return self.__thumb_url_s

    @property
    def url_s(self):
        return self.__url_s

    # --- comparison / hashing (via series_key) ---
    @property
    def _cmpkey_s(self):
        return sstr(self.__series_key)

    def __cmp__(self, other):
        if other is None:
            return 1
        return cmp(self._cmpkey_s, other._cmpkey_s)

    def __eq__(self, other):
        return other is not None and self._cmpkey_s == other._cmpkey_s

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._cmpkey_s)

    def __str__(self):
        return self.__series_name_s + ' (' + sstr(self.__volume_year_n) + ')'

    def __repr__(self):
        return 'SeriesRef(%s)' % self._cmpkey_s

    @staticmethod
    def __parse_int(val, default):
        if val is None:
            return default
        if isinstance(val, (int, long, float)):
            return int(val)
        try:
            return int(val)
        except:
            return default


# ===========================================================================
class IssueRef(object):
    '''
    An immutable, lightweight reference to a single issue (numero) on
    tebeosfera.com.

    issue_num_s   -- the issue number as a string (e.g. '1', 'V1', '10A')
    issue_key     -- a unique key identifying this issue (typically the URL)
    title_s       -- the title of this issue, or ''
    thumb_url_s   -- URL to a thumbnail image, or None
    url_s         -- the full URL to the issue page on tebeosfera.com
    '''

    def __init__(self, issue_num_s, issue_key, title_s='', thumb_url_s=None,
                 url_s='', date_s=''):
        self.__issue_num_s = sstr(issue_num_s) if issue_num_s else ''
        self.__issue_key = sstr(issue_key)
        self.__title_s = title_s or ''
        self.__thumb_url_s = thumb_url_s
        self.__url_s = url_s or ''
        self.__date_s = date_s or ''

    # --- public read-only properties ---
    @property
    def issue_num_s(self):
        return self.__issue_num_s

    @property
    def date_s(self):
        '''Display date, e.g. "12 Mar 2017" or "Oct 2003" ('' if unknown).'''
        return self.__date_s

    @property
    def issue_key(self):
        return self.__issue_key

    @property
    def title_s(self):
        return self.__title_s

    @property
    def thumb_url_s(self):
        return self.__thumb_url_s

    @property
    def url_s(self):
        return self.__url_s

    # --- comparison / hashing (via issue_key) ---
    @property
    def _cmpkey_s(self):
        return sstr(self.__issue_key)

    def __cmp__(self, other):
        if other is None:
            return 1
        return cmp(self._cmpkey_s, other._cmpkey_s)

    def __eq__(self, other):
        return other is not None and self._cmpkey_s == other._cmpkey_s

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._cmpkey_s)

    def __str__(self):
        return '#' + self.__issue_num_s + ' (' + self.__issue_key + ')'

    def __repr__(self):
        return 'IssueRef(%s)' % self._cmpkey_s


# ===========================================================================
class Issue(object):
    '''
    The full detail record for a single issue. Returned by the scraper
    backend when the full issue details are fetched from tebeosfera.com.
    Every field is exposed as a read-write property with validating setters.

    Constructed from an IssueRef; shares its issue_key and issue_num_s.
    '''

    def __init__(self, issue_ref):
        # carried over from the IssueRef
        self.__issue_key = issue_ref.issue_key
        self.__issue_num_s = issue_ref.issue_num_s
        self.__url_s = issue_ref.url_s

        # series-level info (filled from collection page or issue page)
        self.__series_key = ''
        self.__series_name_s = ''
        self.__publisher_s = ''
        self.__imprint_s = ''

        # issue-level info
        self.__title_s = ''
        self.__summary_s = ''
        self.__webpage_s = ''
        self.__format_s = ''

        # dates (each -1 = unknown)
        self.__pub_year_n = -1
        self.__pub_month_n = -1
        self.__pub_day_n = -1

        self.__page_count_n = -1
        self.__rating_n = 0.0

        # author/credit lists
        self.__writers_sl = []
        self.__pencillers_sl = []
        self.__inkers_sl = []
        self.__colorists_sl = []
        self.__letterers_sl = []
        self.__cover_artists_sl = []
        self.__editors_sl = []
        self.__translators_sl = []

        # genre/character lists
        self.__genres_sl = []
        self.__characters_sl = []

        # image URLs
        self.__image_urls_sl = []

        # ISSN and ISBN
        self.__issn_s = ''
        self.__isbn_s = ''

        # interior colour: True = black and white, False = colour, None = unknown
        self.__black_and_white = None

    # --- carried-over read-only properties ---
    @property
    def issue_key(self):
        return self.__issue_key

    @property
    def issue_num_s(self):
        return self.__issue_num_s

    @property
    def url_s(self):
        return self.__url_s

    # --- read-write properties with validating setters ---

    @property
    def series_key(self):
        return self.__series_key

    @series_key.setter
    def series_key(self, val):
        self.__series_key = sstr(val) if val else ''

    @property
    def series_name_s(self):
        return self.__series_name_s

    @series_name_s.setter
    def series_name_s(self, val):
        self.__series_name_s = sstr(val) if val else ''

    @property
    def publisher_s(self):
        return self.__publisher_s

    @publisher_s.setter
    def publisher_s(self, val):
        self.__publisher_s = sstr(val) if val else ''

    @property
    def imprint_s(self):
        return self.__imprint_s

    @imprint_s.setter
    def imprint_s(self, val):
        self.__imprint_s = sstr(val) if val else ''

    @property
    def title_s(self):
        return self.__title_s

    @title_s.setter
    def title_s(self, val):
        self.__title_s = sstr(val) if val else ''

    @property
    def summary_s(self):
        return self.__summary_s

    @summary_s.setter
    def summary_s(self, val):
        self.__summary_s = sstr(val) if val else ''

    @property
    def webpage_s(self):
        return self.__webpage_s

    @webpage_s.setter
    def webpage_s(self, val):
        self.__webpage_s = sstr(val) if val else ''

    @property
    def format_s(self):
        return self.__format_s

    @format_s.setter
    def format_s(self, val):
        self.__format_s = sstr(val) if val else ''

    @property
    def pub_year_n(self):
        return self.__pub_year_n

    @pub_year_n.setter
    def pub_year_n(self, val):
        self.__pub_year_n = clamp(int(val) if val else -1, -1, 9999)

    @property
    def pub_month_n(self):
        return self.__pub_month_n

    @pub_month_n.setter
    def pub_month_n(self, val):
        self.__pub_month_n = clamp(int(val) if val else -1, -1, 12)

    @property
    def pub_day_n(self):
        return self.__pub_day_n

    @pub_day_n.setter
    def pub_day_n(self, val):
        self.__pub_day_n = clamp(int(val) if val else -1, -1, 31)

    @property
    def page_count_n(self):
        return self.__page_count_n

    @page_count_n.setter
    def page_count_n(self, val):
        self.__page_count_n = int(val) if val and int(val) > 0 else -1

    @property
    def rating_n(self):
        return self.__rating_n

    @rating_n.setter
    def rating_n(self, val):
        try:
            self.__rating_n = clamp(float(val), 0.0, 5.0)
        except:
            self.__rating_n = 0.0

    @property
    def issn_s(self):
        return self.__issn_s

    @issn_s.setter
    def issn_s(self, val):
        self.__issn_s = sstr(val).strip() if val else ''

    @property
    def isbn_s(self):
        return self.__isbn_s

    @isbn_s.setter
    def isbn_s(self, val):
        self.__isbn_s = sstr(val).strip() if val else ''

    @property
    def black_and_white(self):
        '''True = black and white interior, False = colour, None = unknown.'''
        return self.__black_and_white

    @black_and_white.setter
    def black_and_white(self, val):
        self.__black_and_white = None if val is None else bool(val)

    # --- list properties (each setter strips None/empties and cleans commas) ---
    def __set_list(self, current, val):
        if val is None:
            val = []
        if isinstance(val, str):
            val = [val]
        result = []
        for item in val:
            if item:
                item = sstr(item).strip()
                # Remove leading/trailing commas that ComicRack uses as delimiters
                item = item.strip(',;')
                if item:
                    result.append(item)
        return result

    @property
    def writers_sl(self):
        return self.__writers_sl

    @writers_sl.setter
    def writers_sl(self, val):
        self.__writers_sl = self.__set_list(self.__writers_sl, val)

    @property
    def pencillers_sl(self):
        return self.__pencillers_sl

    @pencillers_sl.setter
    def pencillers_sl(self, val):
        self.__pencillers_sl = self.__set_list(self.__pencillers_sl, val)

    @property
    def inkers_sl(self):
        return self.__inkers_sl

    @inkers_sl.setter
    def inkers_sl(self, val):
        self.__inkers_sl = self.__set_list(self.__inkers_sl, val)

    @property
    def colorists_sl(self):
        return self.__colorists_sl

    @colorists_sl.setter
    def colorists_sl(self, val):
        self.__colorists_sl = self.__set_list(self.__colorists_sl, val)

    @property
    def letterers_sl(self):
        return self.__letterers_sl

    @letterers_sl.setter
    def letterers_sl(self, val):
        self.__letterers_sl = self.__set_list(self.__letterers_sl, val)

    @property
    def cover_artists_sl(self):
        return self.__cover_artists_sl

    @cover_artists_sl.setter
    def cover_artists_sl(self, val):
        self.__cover_artists_sl = self.__set_list(self.__cover_artists_sl, val)

    @property
    def editors_sl(self):
        return self.__editors_sl

    @editors_sl.setter
    def editors_sl(self, val):
        self.__editors_sl = self.__set_list(self.__editors_sl, val)

    @property
    def translators_sl(self):
        return self.__translators_sl

    @translators_sl.setter
    def translators_sl(self, val):
        self.__translators_sl = self.__set_list(self.__translators_sl, val)

    @property
    def genres_sl(self):
        return self.__genres_sl

    @genres_sl.setter
    def genres_sl(self, val):
        self.__genres_sl = self.__set_list(self.__genres_sl, val)

    @property
    def characters_sl(self):
        return self.__characters_sl

    @characters_sl.setter
    def characters_sl(self, val):
        self.__characters_sl = self.__set_list(self.__characters_sl, val)

    @property
    def image_urls_sl(self):
        return self.__image_urls_sl

    @image_urls_sl.setter
    def image_urls_sl(self, val):
        self.__image_urls_sl = self.__set_list(self.__image_urls_sl, val)

    def __str__(self):
        return 'Issue[%s #%s: %s]' % (self.__series_name_s,
                                       self.__issue_num_s, self.__title_s)
