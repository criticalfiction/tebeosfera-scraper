''' ===========================================================================

This module defines the abstract BookData class, which represents a comic
book's metadata in a way that is independent of the host application.

License: Apache 2.0

=========================================================================== '''
import utils
from utils import sstr


# ===========================================================================
class BookData(object):
    '''
    An abstract base class representing all the metadata fields of a comic
    book. Subclasses (like PluginBookData) connect this abstraction to a
    specific host application (like ComicRack).

    Every metadata property has a validating setter that normalizes values
    (strips whitespace, clamps dates, etc). The class also tracks which
    properties have been updated (via the updated_properties set) so the
    host-specific update() method knows exactly what to write back.
    '''

    # The set of all metadata property names that BookData manages.
    ALL_PROPERTIES = frozenset([
        'series_s', 'number_s', 'title_s', 'volume_n',
        'publisher_s', 'imprint_s', 'format_s',
        'pub_year_n', 'pub_month_n', 'pub_day_n',
        'page_count_n', 'summary_s', 'webpage_s',
        'writers_sl', 'pencillers_sl', 'inkers_sl',
        'colorists_sl', 'letterers_sl', 'cover_artists_sl',
        'editors_sl', 'translators_sl',
        'genres_sl', 'characters_sl',
        'issn_s', 'isbn_s',
        'language_s', 'black_and_white',
        'cover_url_s', 'path_s',
    ])

    def __init__(self):
        # Initialize all properties to blank/default values
        self._series_s = ''
        self._number_s = ''
        self._title_s = ''
        self._volume_n = -1
        self._publisher_s = ''
        self._imprint_s = ''
        self._format_s = ''
        self._pub_year_n = -1
        self._pub_month_n = -1
        self._pub_day_n = -1
        self._page_count_n = -1
        self._summary_s = ''
        self._webpage_s = ''
        self._writers_sl = []
        self._pencillers_sl = []
        self._inkers_sl = []
        self._colorists_sl = []
        self._letterers_sl = []
        self._cover_artists_sl = []
        self._editors_sl = []
        self._translators_sl = []
        self._genres_sl = []
        self._characters_sl = []
        self._issn_s = ''
        self._isbn_s = ''
        # Read-only: the series the host guessed from the file name (''
        # if none). Not written back; used to search when series_s is blank.
        self.proposed_series_s = ''
        self._language_s = ''           # ISO code, e.g. 'es'
        self._black_and_white = None    # True / False / None = unknown
        self._cover_url_s = ''
        self._path_s = ''

        # Track which properties have been updated
        self._updated = set()

    # --- property definitions with validating setters ---

    @property
    def series_s(self):
        return self._series_s

    @series_s.setter
    def series_s(self, val):
        self._series_s = sstr(val).strip() if val else ''
        self._updated.add('series_s')

    @property
    def number_s(self):
        return self._number_s

    @number_s.setter
    def number_s(self, val):
        self._number_s = sstr(val).strip() if val else ''
        self._updated.add('number_s')

    @property
    def title_s(self):
        return self._title_s

    @title_s.setter
    def title_s(self, val):
        self._title_s = sstr(val).strip() if val else ''
        self._updated.add('title_s')

    @property
    def volume_n(self):
        return self._volume_n

    @volume_n.setter
    def volume_n(self, val):
        try:
            self._volume_n = int(val)
        except:
            self._volume_n = -1
        self._updated.add('volume_n')

    @property
    def publisher_s(self):
        return self._publisher_s

    @publisher_s.setter
    def publisher_s(self, val):
        self._publisher_s = sstr(val).strip() if val else ''
        self._updated.add('publisher_s')

    @property
    def imprint_s(self):
        return self._imprint_s

    @imprint_s.setter
    def imprint_s(self, val):
        self._imprint_s = sstr(val).strip() if val else ''
        self._updated.add('imprint_s')

    @property
    def format_s(self):
        return self._format_s

    @format_s.setter
    def format_s(self, val):
        self._format_s = sstr(val).strip() if val else ''
        self._updated.add('format_s')

    @property
    def pub_year_n(self):
        return self._pub_year_n

    @pub_year_n.setter
    def pub_year_n(self, val):
        try:
            self._pub_year_n = utils.clamp(int(val), -1, 9999)
        except:
            self._pub_year_n = -1
        self._updated.add('pub_year_n')

    @property
    def pub_month_n(self):
        return self._pub_month_n

    @pub_month_n.setter
    def pub_month_n(self, val):
        try:
            self._pub_month_n = utils.clamp(int(val), -1, 12)
        except:
            self._pub_month_n = -1
        self._updated.add('pub_month_n')

    @property
    def pub_day_n(self):
        return self._pub_day_n

    @pub_day_n.setter
    def pub_day_n(self, val):
        try:
            self._pub_day_n = utils.clamp(int(val), -1, 31)
        except:
            self._pub_day_n = -1
        self._updated.add('pub_day_n')

    @property
    def page_count_n(self):
        return self._page_count_n

    @page_count_n.setter
    def page_count_n(self, val):
        try:
            self._page_count_n = int(val)
        except:
            self._page_count_n = -1
        self._updated.add('page_count_n')

    @property
    def summary_s(self):
        return self._summary_s

    @summary_s.setter
    def summary_s(self, val):
        self._summary_s = sstr(val).strip() if val else ''
        self._updated.add('summary_s')

    @property
    def webpage_s(self):
        return self._webpage_s

    @webpage_s.setter
    def webpage_s(self, val):
        self._webpage_s = sstr(val).strip() if val else ''
        self._updated.add('webpage_s')

    @property
    def writers_sl(self):
        return self._writers_sl

    @writers_sl.setter
    def writers_sl(self, val):
        self._writers_sl = self._clean_list(val)
        self._updated.add('writers_sl')

    @property
    def pencillers_sl(self):
        return self._pencillers_sl

    @pencillers_sl.setter
    def pencillers_sl(self, val):
        self._pencillers_sl = self._clean_list(val)
        self._updated.add('pencillers_sl')

    @property
    def inkers_sl(self):
        return self._inkers_sl

    @inkers_sl.setter
    def inkers_sl(self, val):
        self._inkers_sl = self._clean_list(val)
        self._updated.add('inkers_sl')

    @property
    def colorists_sl(self):
        return self._colorists_sl

    @colorists_sl.setter
    def colorists_sl(self, val):
        self._colorists_sl = self._clean_list(val)
        self._updated.add('colorists_sl')

    @property
    def letterers_sl(self):
        return self._letterers_sl

    @letterers_sl.setter
    def letterers_sl(self, val):
        self._letterers_sl = self._clean_list(val)
        self._updated.add('letterers_sl')

    @property
    def cover_artists_sl(self):
        return self._cover_artists_sl

    @cover_artists_sl.setter
    def cover_artists_sl(self, val):
        self._cover_artists_sl = self._clean_list(val)
        self._updated.add('cover_artists_sl')

    @property
    def editors_sl(self):
        return self._editors_sl

    @editors_sl.setter
    def editors_sl(self, val):
        self._editors_sl = self._clean_list(val)
        self._updated.add('editors_sl')

    @property
    def translators_sl(self):
        return self._translators_sl

    @translators_sl.setter
    def translators_sl(self, val):
        self._translators_sl = self._clean_list(val)
        self._updated.add('translators_sl')

    @property
    def genres_sl(self):
        return self._genres_sl

    @genres_sl.setter
    def genres_sl(self, val):
        self._genres_sl = self._clean_list(val)
        self._updated.add('genres_sl')

    @property
    def characters_sl(self):
        return self._characters_sl

    @characters_sl.setter
    def characters_sl(self, val):
        self._characters_sl = self._clean_list(val)
        self._updated.add('characters_sl')

    @property
    def issn_s(self):
        return self._issn_s

    @issn_s.setter
    def issn_s(self, val):
        self._issn_s = sstr(val).strip() if val else ''
        self._updated.add('issn_s')

    @property
    def isbn_s(self):
        return self._isbn_s

    @isbn_s.setter
    def isbn_s(self, val):
        self._isbn_s = sstr(val).strip() if val else ''
        self._updated.add('isbn_s')

    @property
    def language_s(self):
        return self._language_s

    @language_s.setter
    def language_s(self, val):
        self._language_s = sstr(val).strip() if val else ''
        self._updated.add('language_s')

    @property
    def black_and_white(self):
        return self._black_and_white

    @black_and_white.setter
    def black_and_white(self, val):
        self._black_and_white = None if val is None else bool(val)
        self._updated.add('black_and_white')

    @property
    def cover_url_s(self):
        return self._cover_url_s

    @cover_url_s.setter
    def cover_url_s(self, val):
        self._cover_url_s = sstr(val).strip() if val else ''
        self._updated.add('cover_url_s')

    @property
    def path_s(self):
        return self._path_s

    @path_s.setter
    def path_s(self, val):
        self._path_s = sstr(val) if val else ''

    # --- tracking helpers ---

    def dont_update(self, prop_name):
        '''Removes a property from the "to update" set.'''
        self._updated.discard(prop_name)

    def updated_properties(self):
        '''Returns the set of property names that have been updated.'''
        return set(self._updated)

    def blank(self, prop_name):
        '''Returns True if the given property is blank/empty/unknown.'''
        val = getattr(self, prop_name)
        if isinstance(val, list):
            return len(val) == 0
        if isinstance(val, int):
            return val == -1
        return not val or not sstr(val).strip()

    @classmethod
    def all_properties(cls):
        '''Returns the set of all managed property names.'''
        return set(cls.ALL_PROPERTIES)

    @staticmethod
    def _clean_list(val):
        '''Cleans a list value: ensures it's a list, strips items, removes empties.'''
        if val is None:
            return []
        if isinstance(val, str):
            val = [val]
        result = []
        for item in val:
            if item:
                item = sstr(item).strip().strip(',;')
                if item:
                    result.append(item)
        return result

    # --- abstract methods (subclasses must implement) ---

    def update(self):
        '''Writes the updated properties back to the host application. Abstract.'''
        raise NotImplementedError('update() must be implemented by subclass')

    def create_image_of_page(self, page_num):
        '''Returns a .NET Image of the given page. Abstract.'''
        raise NotImplementedError('create_image_of_page() must be implemented')
