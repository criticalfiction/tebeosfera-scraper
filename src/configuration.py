''' ===========================================================================

This module contains the Configuration class, which manages all settings
for the Tebeosfera Scraper. Settings are persisted to .dat files in the
user's AppData directory.

License: Apache 2.0

=========================================================================== '''
import re
import log
import utils
from utils import sstr, load_map, persist_map, load_string, persist_string
from resources import Resources


# ===========================================================================
class Configuration(object):
    '''
    Contains all configurable settings for the Tebeosfera Scraper.
    Basic settings are persisted via load_map/persist_map to settings.dat.
    Advanced settings are parsed from a free-text string in advanced.dat.
    '''

    def __init__(self):
        self.load_defaults()

    # --- Field update flags (which metadata fields to scrape) ---
    update_series_b = True
    update_number_b = True
    update_title_b = True
    update_writer_b = True
    update_penciller_b = True
    update_inker_b = True
    update_colorist_b = True
    update_letterer_b = True
    update_cover_artist_b = True
    update_editor_b = True
    update_translator_b = False
    update_publisher_b = True
    update_pub_date_b = True
    update_page_count_b = True
    update_format_b = True
    update_summary_b = True
    update_webpage_b = True
    update_genre_b = True
    update_characters_b = True
    update_issn_b = False
    update_cover_b = True
    update_black_and_white_b = True

    # --- Behavior flags ---
    ow_existing_b = True
    ignore_blanks_b = True
    autochoose_series_b = False
    confirm_issue_b = True
    download_thumbs_b = True
    preserve_thumbs_b = True
    fast_rescrape_b = True
    rescrape_notes_b = True
    rescrape_tags_b = True
    summary_dialog_b = True
    welcome_dialog_b = True

    # If the penciller (dibujante/historietista) is credited but the inker,
    # cover artist or colorist isn't, credit the penciller for that role.
    copy_penciller_to_inker_b = False
    copy_penciller_to_cover_artist_b = False
    copy_penciller_to_colorist_b = False

    # Leave Title alone when the scraped title is just the series name.
    title_only_if_different_b = True

    # ComicRack has no translator field: list translators as writers,
    # after the original writers.
    translators_as_writers_b = True

    # Set the book's language to Spanish ('es') if it has none.
    set_spanish_language_b = True

    # --- Search/scrape behavior ---
    max_search_results_n = 25
    scrape_delay_n = 2  # seconds between scraping books
    # How to write credits whose author has a signature different from
    # their real name: 0 signature, 1 real name, 2 "signature (real name)",
    # 3 "real name (signature)", 4 and 5 the same two shortened
    # (see tbfscraper.NAME_*).
    credit_name_style_n = 0

    # --- Advanced settings (parsed from advanced_settings_s) ---
    advanced_settings_s = ''
    _ignored_publishers_sl = []
    _publisher_aliases_sm = {}

    # --- Session-only data (not persisted) ---
    session_data_map = {}

    # --- All recognized setting keys (for load/save) ---
    _BOOL_KEYS = [
        'update_series_b', 'update_number_b', 'update_title_b',
        'update_writer_b', 'update_penciller_b', 'update_inker_b',
        'update_colorist_b', 'update_letterer_b', 'update_cover_artist_b',
        'update_editor_b', 'update_translator_b', 'update_publisher_b',
        'update_pub_date_b', 'update_page_count_b', 'update_format_b',
        'update_summary_b', 'update_webpage_b', 'update_genre_b',
        'update_characters_b', 'update_issn_b', 'update_cover_b',
        'update_black_and_white_b',
        'ow_existing_b', 'ignore_blanks_b', 'autochoose_series_b',
        'confirm_issue_b', 'download_thumbs_b', 'preserve_thumbs_b',
        'fast_rescrape_b', 'rescrape_notes_b', 'rescrape_tags_b',
        'summary_dialog_b', 'welcome_dialog_b',
        'copy_penciller_to_inker_b', 'copy_penciller_to_cover_artist_b',
        'copy_penciller_to_colorist_b', 'title_only_if_different_b',
        'translators_as_writers_b',
        'set_spanish_language_b',
    ]

    # Replaced by the three copy_penciller_to_* settings (see load_defaults)
    _OLD_COPY_PENCILLER_KEY = 'copy_penciller_credits_b'

    _INT_KEYS = [
        'max_search_results_n', 'scrape_delay_n', 'credit_name_style_n',
    ]

    # =========================================================================
    def load_defaults(self):
        '''Loads all settings from the settings file.'''
        # Start with defaults
        self.__init_defaults()

        # Load from file
        data = load_map(Resources.SETTINGS_FILE)
        for key in self._BOOL_KEYS:
            if key in data:
                setattr(self, key, bool(data[key]))
        for key in self._INT_KEYS:
            if key in data:
                setattr(self, key, int(data[key]))
        if not 0 <= self.credit_name_style_n <= 5:
            self.credit_name_style_n = 0

        # Settings saved before the penciller copy option was split in three
        # carry over to all three.
        old = self._OLD_COPY_PENCILLER_KEY
        new = ['copy_penciller_to_inker_b', 'copy_penciller_to_cover_artist_b',
               'copy_penciller_to_colorist_b']
        if old in data and not any(k in data for k in new):
            for key in new:
                setattr(self, key, bool(data[old]))

        # Load advanced settings
        self.advanced_settings_s = load_string(Resources.ADVANCED_FILE)
        self.__parse_advanced_settings()

    # =========================================================================
    def save_defaults(self):
        '''Saves all settings to the settings file.'''
        data = {}
        for key in self._BOOL_KEYS:
            data[key] = getattr(self, key)
        for key in self._INT_KEYS:
            data[key] = getattr(self, key)
        persist_map(Resources.SETTINGS_FILE, data)
        persist_string(Resources.ADVANCED_FILE, self.advanced_settings_s)

    # =========================================================================
    def __init_defaults(self):
        '''Resets all settings to their default values.'''
        cls = Configuration
        for key in self._BOOL_KEYS:
            setattr(self, key, getattr(cls, key))
        for key in self._INT_KEYS:
            setattr(self, key, getattr(cls, key))
        self.advanced_settings_s = ''
        self.session_data_map = {}

    # =========================================================================
    def __parse_advanced_settings(self):
        '''Parses the advanced settings string for special options.'''
        self._ignored_publishers_sl = []
        self._publisher_aliases_sm = {}

        if not self.advanced_settings_s:
            return

        try:
            for line in self.advanced_settings_s.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # Parse KEY = VALUE
                m = re.match(r'(\w+)\s*=\s*(.*)', line)
                if not m:
                    continue
                key = m.group(1).upper()
                value = m.group(2).strip()

                if key == 'IGNORE_PUBLISHER':
                    self._ignored_publishers_sl.append(value)
                elif key == 'PUBLISHER_ALIAS':
                    # X --> Y
                    am = re.match(r'(.+?)\s*-->\s*(.+)', value)
                    if am:
                        self._publisher_aliases_sm[am.group(1).strip()] = \
                            am.group(2).strip()
                elif key == 'SCRAPE_DELAY':
                    try:
                        self.scrape_delay_n = max(0, int(value))
                    except:
                        pass
                elif key == 'MAX_SEARCH_RESULTS':
                    try:
                        self.max_search_results_n = int(value)
                    except:
                        pass
        except:
            log.debug_exc('Error parsing advanced settings')

    # =========================================================================
    def parse_advanced_settings(self):
        '''Public wrapper - re-parses advanced_settings_s after editing.'''
        self.__parse_advanced_settings()

    # =========================================================================
    @property
    def ignored_publishers_sl(self):
        return self._ignored_publishers_sl

    @property
    def publisher_aliases_sm(self):
        return self._publisher_aliases_sm

    # =========================================================================
    def __eq__(self, other):
        if other is None or not isinstance(other, Configuration):
            return False
        for key in self._BOOL_KEYS + self._INT_KEYS:
            if getattr(self, key) != getattr(other, key):
                return False
        return self.advanced_settings_s == other.advanced_settings_s

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        lines = ['Configuration:']
        for key in self._BOOL_KEYS:
            lines.append('  %s = %s' % (key, getattr(self, key)))
        for key in self._INT_KEYS:
            lines.append('  %s = %s' % (key, getattr(self, key)))
        if self.advanced_settings_s:
            lines.append('  advanced_settings:')
            for line in self.advanced_settings_s.split('\n'):
                lines.append('    %s' % line)
        return '\n'.join(lines)
