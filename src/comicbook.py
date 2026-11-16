''' ===========================================================================

This module defines the ComicBook class, which wraps a ComicRack native
ComicBook object and provides scraper-specific logic like unique series keys,
rescrape tags, and the update() method that applies scraped Issue data.

License: Apache 2.0

=========================================================================== '''
import re
import clr
import log
import utils
from utils import sstr, strip_accents
from pluginbookdata import PluginBookData
from tbfscraper import normalize_title

clr.AddReference('System')
from System import String, BitConverter
from System.Security.Cryptography import MD5CryptoServiceProvider
from System.Text import Encoding

# The tag written into a book's Notes to indicate it was skipped forever.
SKIP_TAG = 'TBFSKIP'


# ===========================================================================
class ComicBook(object):
    '''
    Wraps a native ComicRack ComicBook object and adds scraper logic.
    Provides read-only access to metadata fields, computes a unique series
    key for caching, and implements the update() method that applies scraped
    Issue data to the underlying book.
    '''

    def __init__(self, crbook, scraper):
        self.__scraper = scraper
        self.__bookdata = PluginBookData(crbook, scraper)
        self.__skip_b = False

        # Check for skip tag in notes
        notes = self.__bookdata.webpage_s or ''
        # The skip tag might be stored in the book's custom values or notes
        try:
            notes_val = ''
            if hasattr(crbook, 'Notes') and crbook.Notes:
                notes_val = sstr(crbook.Notes)
            if SKIP_TAG in notes_val:
                self.__skip_b = True
        except:
            pass

    # --- read properties (delegated to bookdata) ---

    @property
    def series_s(self):
        '''
        The series to search for: the book's Series, or if that's blank,
        the series ComicRack proposes from the file name. (Only the search
        uses the proposed value; the book's Series still counts as blank
        when scraped data is written.)
        '''
        return self.__bookdata.series_s or self.__bookdata.proposed_series_s

    @property
    def issue_num_s(self):
        return self.__bookdata.number_s

    @property
    def volume_year_n(self):
        return self.__bookdata.volume_n

    @property
    def pub_year_n(self):
        return self.__bookdata.pub_year_n

    @property
    def format_s(self):
        return self.__bookdata.format_s

    @property
    def path_s(self):
        return self.__bookdata.path_s

    @property
    def page_count_n(self):
        return self.__bookdata.page_count_n

    @property
    def bookdata(self):
        return self.__bookdata

    # --- computed properties ---

    @property
    def unique_series_s(self):
        '''
        Returns a unique key for the series this book belongs to, so that
        all books of the same series share a key (used for caching in the
        scrape engine).
        '''
        name = strip_accents(self.series_s.lower().strip())
        fmt  = strip_accents(self.__bookdata.format_s.lower().strip())
        vol  = sstr(self.__bookdata.volume_n)
        key  = name + '|' + fmt + '|' + vol

        # Use .NET MD5 (IronPython 2 doesn't ship hashlib)
        md5 = MD5CryptoServiceProvider()
        raw = md5.ComputeHash(Encoding.UTF8.GetBytes(key))
        return BitConverter.ToString(raw).Replace('-', '').lower()

    @property
    def skip_b(self):
        '''Returns True if this book has been tagged to skip forever.'''
        return self.__skip_b

    @property
    def issue_ref(self):
        '''
        Returns an IssueRef reconstructed from the book's stored webpage URL,
        or None if no previous scrape data exists.
        '''
        web = self.__bookdata.webpage_s
        if web and '/numeros/' in web:
            # Extract the slug from the URL
            try:
                slug = web.split('/numeros/')[1].split('?')[0].rstrip('/').rstrip('.html')
                slug = slug.replace('.html', '')
                from dbmodels import IssueRef
                return IssueRef(
                    issue_num_s=self.issue_num_s,
                    issue_key=slug,
                    url_s=web)
            except:
                pass
        return None

    @property
    def series_ref(self):
        '''
        Returns a SeriesRef reconstructed from the book's stored webpage URL,
        or None if no previous scrape data exists.
        '''
        web = self.__bookdata.webpage_s
        if web and '/colecciones/' in web:
            try:
                slug = web.split('/colecciones/')[1].split('?')[0].rstrip('/').rstrip('.html')
                slug = slug.replace('.html', '')
                from dbmodels import SeriesRef
                return SeriesRef(
                    series_key=slug,
                    series_name_s=self.series_s,
                    url_s=web)
            except:
                pass
        return None

    # --- methods ---

    def skip_forever(self):
        '''Tags this book so it will be skipped in future scrapes.'''
        self.__skip_b = True
        try:
            crbook = self.__bookdata._PluginBookData__crbook
            notes = sstr(crbook.Notes) if hasattr(crbook, 'Notes') and crbook.Notes else ''
            if SKIP_TAG not in notes:
                crbook.Notes = (notes + ' [' + SKIP_TAG + ']').strip()
        except:
            pass

    # =========================================================================
    def update(self, issue):
        '''
        Applies the data from the given scraped Issue to this book, respecting
        the configuration's field-update flags, overwrite rules, and
        ignore-blanks rules.
        '''
        config = self.__scraper.config
        bd = self.__bookdata

        def allowed(config_flag, current_val, new_val):
            """Field enabled + overwrite / ignore-blanks rules."""
            if not getattr(config, config_flag, False):
                return False
            new_blank = utils.is_blank(new_val)
            old_blank = utils.is_blank(current_val)
            if new_blank:
                # don't wipe a value the book already has
                return not (config.ignore_blanks_b and not old_blank)
            # don't replace a value the book already has, unless allowed
            return config.ow_existing_b or old_blank

        # Credits that fall back to the penciller (dibujante/historietista)
        # when the page doesn't name anyone for them. A black-and-white
        # comic has no colorist, so that one is skipped.
        inkers = issue.inkers_sl
        cover_artists = issue.cover_artists_sl
        colorists = issue.colorists_sl
        pencillers = list(issue.pencillers_sl)
        if pencillers:
            if config.copy_penciller_to_inker_b and not inkers:
                inkers = pencillers
            if config.copy_penciller_to_cover_artist_b and not cover_artists:
                cover_artists = pencillers
            if config.copy_penciller_to_colorist_b and not colorists and \
                    issue.black_and_white is not True:
                colorists = pencillers

        # Translators go after the original writers (ComicRack has no
        # translator field).
        writers = issue.writers_sl
        if config.translators_as_writers_b and issue.translators_sl:
            seen = set(w.lower() for w in writers)
            writers = list(writers) + [t for t in issue.translators_sl
                                       if t.lower() not in seen]

        # Many issues have no title of their own; the site then shows the
        # series name as the title. Optionally leave Title alone for those.
        # Compared against both the scraped series and the book's own one.
        skip_title = config.title_only_if_different_b and \
            normalize_title(issue.title_s) in \
            (normalize_title(issue.series_name_s), normalize_title(bd.series_s))

        # (book field, setting, scraped value)
        fields = [
            ('series_s',         'update_series_b',       issue.series_name_s),
            ('number_s',         'update_number_b',       issue.issue_num_s),
            ('title_s',          'update_title_b',        issue.title_s),
            ('publisher_s',      'update_publisher_b',    issue.publisher_s),
            ('format_s',         'update_format_b',       issue.format_s),
            ('page_count_n',     'update_page_count_b',   issue.page_count_n),
            ('summary_s',        'update_summary_b',      issue.summary_s),
            ('webpage_s',        'update_webpage_b',      issue.url_s),
            ('writers_sl',       'update_writer_b',       writers),
            ('pencillers_sl',    'update_penciller_b',    issue.pencillers_sl),
            ('inkers_sl',        'update_inker_b',        inkers),
            ('colorists_sl',     'update_colorist_b',     colorists),
            ('letterers_sl',     'update_letterer_b',     issue.letterers_sl),
            ('cover_artists_sl', 'update_cover_artist_b', cover_artists),
            ('editors_sl',       'update_editor_b',       issue.editors_sl),
            ('translators_sl',   'update_translator_b',   issue.translators_sl),
            ('genres_sl',        'update_genre_b',        issue.genres_sl),
            ('characters_sl',    'update_characters_b',   issue.characters_sl),
            ('issn_s',           'update_issn_b',         issue.issn_s),
            ('black_and_white',  'update_black_and_white_b', issue.black_and_white),
        ]
        for field, flag, value in fields:
            if field == 'title_s' and skip_title:
                bd.dont_update(field)
            elif allowed(flag, getattr(bd, field), value):
                setattr(bd, field, value)
            else:
                bd.dont_update(field)

        # The publication date is three fields that go together.
        if allowed('update_pub_date_b', bd.pub_year_n, issue.pub_year_n):
            bd.pub_year_n = issue.pub_year_n
            bd.pub_month_n = issue.pub_month_n
            bd.pub_day_n = issue.pub_day_n
        else:
            for f in ('pub_year_n', 'pub_month_n', 'pub_day_n'):
                bd.dont_update(f)

        # Language: only filled in when the book has none.
        if config.set_spanish_language_b and not bd.language_s:
            bd.language_s = 'es'
        else:
            bd.dont_update('language_s')

        # Cover image URL (for thumbnail download)
        if config.update_cover_b and issue.image_urls_sl:
            bd.cover_url_s = issue.image_urls_sl[0]
        else:
            bd.dont_update('cover_url_s')

        # Write the data back to the native book
        bd.update()

        # Download cover thumbnail if applicable (only for fileless books)
        if config.download_thumbs_b and issue.image_urls_sl:
            try:
                crbook = bd._PluginBookData__crbook
                # Only fileless books: a book with a file already shows its
                # real cover, which a downloaded thumbnail would replace.
                is_fileless = not (hasattr(crbook, 'FilePath') and crbook.FilePath)
                if is_fileless:
                    self.__download_thumbnail(crbook, issue.image_urls_sl[0])
            except Exception, ex:
                log.debug('Could not download thumbnail: %s' % sstr(ex))

    # =========================================================================
    def __download_thumbnail(self, crbook, image_url):
        '''Downloads a cover image and sets it as the book's thumbnail.'''
        try:
            import tbfscraper
            img = tbfscraper.fetch_image(image_url)
            if img:
                comicrack = self.__scraper.comicrack
                if hasattr(comicrack.App, 'SetCustomBookThumbnail'):
                    comicrack.App.SetCustomBookThumbnail(crbook, img)
                    log.debug('Set thumbnail for: %s' % self.series_s)
        except Exception, ex:
            log.debug('Thumbnail download failed: %s' % sstr(ex))

    # =========================================================================
    def create_image_of_page(self, page_num):
        '''Returns a .NET Image of the given page of this book.'''
        return self.__bookdata.create_image_of_page(page_num)
