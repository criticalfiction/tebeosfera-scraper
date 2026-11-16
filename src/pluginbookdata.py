''' ===========================================================================

This module defines PluginBookData, the concrete BookData subclass that
connects to ComicRack's native ComicBook object.

License: Apache 2.0

=========================================================================== '''
import clr
import log
import utils
from bookdata import BookData
from utils import sstr

clr.AddReference('System')
from System import Enum
from System.IO import Path as SysPath


# ===========================================================================
class PluginBookData(BookData):
    '''
    A BookData implementation that wraps a ComicRack native ComicBook object.
    Reads all metadata fields from the native book on construction, and writes
    updated fields back via the update() method.
    '''

    def __init__(self, crbook, scraper):
        '''
        Initializes this BookData by reading all metadata from the given
        native ComicRack book object.
        '''
        super(PluginBookData, self).__init__()

        self.__crbook = crbook
        self.__scraper = scraper

        # Don't track updates during initial read
        self._updated = set()

        # Read all fields from the native book
        try:
            self._series_s = sstr(crbook.Series) if crbook.Series else ''
            # ComicRack's guess from the file name (read-only); see
            # ComicBook.series_s
            if hasattr(crbook, 'ProposedSeries') and crbook.ProposedSeries:
                self.proposed_series_s = sstr(crbook.ProposedSeries).strip()
            self._number_s = sstr(crbook.Number) if crbook.Number else ''
            self._title_s = sstr(crbook.Title) if crbook.Title else ''
            self._volume_n = int(crbook.Volume) if crbook.Volume else -1
            self._publisher_s = sstr(crbook.Publisher) if crbook.Publisher else ''
            self._imprint_s = sstr(crbook.Imprint) if hasattr(crbook, 'Imprint') and crbook.Imprint else ''
            self._format_s = sstr(crbook.Format) if hasattr(crbook, 'Format') and crbook.Format else ''

            # Dates
            # ComicRack's Year / Month / Day ints, -1 when blank
            self._pub_year_n = int(crbook.Year)
            self._pub_month_n = int(crbook.Month)
            self._pub_day_n = int(crbook.Day)

            self._page_count_n = int(crbook.PageCount) if hasattr(crbook, 'PageCount') and crbook.PageCount else -1
            self._summary_s = sstr(crbook.Summary) if hasattr(crbook, 'Summary') and crbook.Summary else ''
            self._webpage_s = sstr(crbook.Web) if hasattr(crbook, 'Web') and crbook.Web else ''

            # Author lists (ComicRack stores comma-separated)
            self._writers_sl = self.__split_list(crbook.Writer)
            self._pencillers_sl = self.__split_list(crbook.Penciller)
            self._inkers_sl = self.__split_list(crbook.Inker) if hasattr(crbook, 'Inker') else []
            self._colorists_sl = self.__split_list(crbook.Colorist) if hasattr(crbook, 'Colorist') else []
            self._letterers_sl = self.__split_list(crbook.Letterer) if hasattr(crbook, 'Letterer') else []
            self._cover_artists_sl = self.__split_list(crbook.CoverArtist) if hasattr(crbook, 'CoverArtist') else []
            self._editors_sl = self.__split_list(crbook.Editor) if hasattr(crbook, 'Editor') else []

            # Genre and characters
            self._genres_sl = self.__split_list(crbook.Genre) if hasattr(crbook, 'Genre') else []
            self._characters_sl = self.__split_list(crbook.Characters) if hasattr(crbook, 'Characters') else []

            # ISSN/ISBN
            self._issn_s = sstr(crbook.ISSN) if hasattr(crbook, 'ISSN') and crbook.ISSN else ''
            self._isbn_s = sstr(crbook.ISBN) if hasattr(crbook, 'ISBN') and crbook.ISBN else ''

            # Language (ISO code) and black-and-white (a YesNo enum)
            self._language_s = sstr(crbook.LanguageISO) \
                if hasattr(crbook, 'LanguageISO') and crbook.LanguageISO else ''
            if hasattr(crbook, 'BlackAndWhite'):
                bw = sstr(crbook.BlackAndWhite)
                self._black_and_white = True if bw == 'Yes' else \
                    False if bw == 'No' else None

            # Path
            self._path_s = sstr(crbook.FilePath) if hasattr(crbook, 'FilePath') and crbook.FilePath else ''

        except Exception, ex:
            log.debug('Error reading book data: %s' % sstr(ex))

        # Start with a clean update set (nothing to write yet)
        self._updated = set()

    # =========================================================================
    def update(self):
        '''
        Writes all updated metadata properties back to the native ComicRack
        book object.
        '''
        ok_to_update = self.updated_properties()
        try:
            book = self.__crbook

            if 'series_s' in ok_to_update:
                book.Series = self._series_s

            if 'number_s' in ok_to_update:
                book.Number = self._number_s

            if 'title_s' in ok_to_update:
                book.Title = self._title_s

            if 'volume_n' in ok_to_update and self._volume_n > 0:
                book.Volume = self._volume_n

            if 'publisher_s' in ok_to_update:
                book.Publisher = self._publisher_s

            if 'imprint_s' in ok_to_update and hasattr(book, 'Imprint'):
                book.Imprint = self._imprint_s

            if 'format_s' in ok_to_update and hasattr(book, 'Format'):
                book.Format = self._format_s

            # Date: ComicRack keeps the publication date in three int fields,
            # Year / Month / Day (-1 = blank), as the Comic Vine and
            # Bedetheque scrapers write it. The scraped date replaces the
            # book's whole date, so a missing month/day ("1986", "X-2003")
            # clears the old one instead of leaving it next to the new year.
            if 'pub_year_n' in ok_to_update and self._pub_year_n > 0:
                month = self._pub_month_n if self._pub_month_n > 0 else -1
                day = self._pub_day_n if month > 0 and self._pub_day_n > 0 else -1
                book.Year = self._pub_year_n
                book.Month = month
                book.Day = day

            if 'page_count_n' in ok_to_update and self._page_count_n > 0:
                if hasattr(book, 'PageCount'):
                    book.PageCount = self._page_count_n

            if 'summary_s' in ok_to_update:
                book.Summary = self._summary_s

            if 'webpage_s' in ok_to_update:
                book.Web = self._webpage_s

            # Author lists: ComicRack stores comma-separated
            if 'writers_sl' in ok_to_update:
                book.Writer = ', '.join(self._writers_sl)
            if 'pencillers_sl' in ok_to_update:
                book.Penciller = ', '.join(self._pencillers_sl)
            if 'inkers_sl' in ok_to_update and hasattr(book, 'Inker'):
                book.Inker = ', '.join(self._inkers_sl)
            if 'colorists_sl' in ok_to_update and hasattr(book, 'Colorist'):
                book.Colorist = ', '.join(self._colorists_sl)
            if 'letterers_sl' in ok_to_update and hasattr(book, 'Letterer'):
                book.Letterer = ', '.join(self._letterers_sl)
            if 'cover_artists_sl' in ok_to_update and hasattr(book, 'CoverArtist'):
                book.CoverArtist = ', '.join(self._cover_artists_sl)
            if 'editors_sl' in ok_to_update and hasattr(book, 'Editor'):
                book.Editor = ', '.join(self._editors_sl)

            # Genre and characters
            if 'genres_sl' in ok_to_update and hasattr(book, 'Genre'):
                book.Genre = ', '.join(self._genres_sl)
            if 'characters_sl' in ok_to_update and hasattr(book, 'Characters'):
                book.Characters = ', '.join(self._characters_sl)

            # ISSN/ISBN
            if 'issn_s' in ok_to_update and hasattr(book, 'ISSN'):
                book.ISSN = self._issn_s
            if 'isbn_s' in ok_to_update and hasattr(book, 'ISBN'):
                book.ISBN = self._isbn_s

            if 'language_s' in ok_to_update and hasattr(book, 'LanguageISO'):
                book.LanguageISO = self._language_s

            # BlackAndWhite is ComicRack's YesNo enum; build the value from
            # the field's own type so we don't need ComicRack's assembly.
            if 'black_and_white' in ok_to_update and \
                    self._black_and_white is not None and \
                    hasattr(book, 'BlackAndWhite'):
                book.BlackAndWhite = Enum.Parse(
                    book.BlackAndWhite.GetType(),
                    'Yes' if self._black_and_white else 'No')

            log.debug('Updated %d fields on book: %s' %
                       (len(ok_to_update), self._series_s))

        except Exception, ex:
            log.debug('Error writing book data: %s' % sstr(ex))
            log.debug_exc()

    # =========================================================================
    def create_image_of_page(self, page_num):
        '''
        Returns a Bitmap of the given page of this book, or None. Uses
        ComicRack's plugin API (ComicRack.App, as the Comic Vine Scraper
        does); call it on ComicRack's own (main) thread. Fileless books
        have no pages, so their thumbnail is used instead.
        '''
        try:
            app = self.__scraper.comicrack.App
            if self._path_s:
                return app.GetComicPage(self.__crbook, page_num)
            return app.GetComicThumbnail(self.__crbook, page_num)
        except Exception, ex:
            # e.g. the page count is 0 after "clear data"
            log.debug('Error getting page image: %s' % sstr(ex))
        return None

    # =========================================================================
    @staticmethod
    def __split_list(val):
        '''Splits a comma-separated string into a list of trimmed strings.'''
        if not val:
            return []
        return [s.strip() for s in sstr(val).split(',') if s.strip()]
