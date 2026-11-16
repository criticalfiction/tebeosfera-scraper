''' ===========================================================================

This module is home to the ScrapeEngine class, which contains the main
processing loop for the Tebeosfera Scraper.

License: Apache 2.0

=========================================================================== '''
import clr
import log
import utils
from utils import sstr
from resources import Resources
from configuration import Configuration
from comicbook import ComicBook
from searchform import SearchForm
from seriesform import SeriesForm, SeriesFormResult
from issueform import IssueForm, IssueFormResult
from comicform import ComicForm
from configform import ConfigForm
import tbfscraper

clr.AddReference('System.Windows.Forms')
from System.Windows.Forms import Application, MessageBox, \
    MessageBoxButtons, MessageBoxIcon, DialogResult

clr.AddReference('System')
from System import GC, DateTime
from System.Threading import Thread, ThreadStart
from System.IO import Path


# ===========================================================================
class ScrapedSeries(object):
    '''
    Engine-internal helper: holds a SeriesRef and a set of IssueRefs,
    cached per unique-series-key so repeated books in the same series
    skip re-searching.
    '''

    def __init__(self, series_ref):
        self.series_ref = series_ref
        self.issue_refs = set()


# ===========================================================================
class BookStatus(object):
    '''
    A status enum for the main processing loop.
    '''

    def __init__(self, status_id, failed_search_terms_s=None):
        self.__id = status_id
        self.__failed_search_terms_s = failed_search_terms_s

    def equals(self, id_s):
        return self.__id == id_s

    def get_failed_search_terms_s(self):
        return self.__failed_search_terms_s


# ===========================================================================
class ScrapeEngine(object):
    '''
    The main processing engine for the Tebeosfera Scraper.

    Once initialized, pass a collection of books to the ScrapeEngine via
    the 'scrape' method. Those books will be processed one at a time,
    with windows and dialogs popping up to interact with the user as needed.
    '''

    # =========================================================================
    def __init__(self, comicrack):
        self.config = Configuration()
        self.comicrack = comicrack
        self.start_scrape_listeners = []
        self.cancel_listeners = []
        self.__cancelled_b = False
        self.status = [0, 0]  # [scraped_count, total_count]

    # =========================================================================
    def cancel(self):
        '''Cancels the current scrape operation.'''
        if not self.__cancelled_b:
            self.__cancelled_b = True
            def delegate():
                for cancel_listener in self.cancel_listeners:
                    cancel_listener()
            utils.invoke(self.comicrack.MainWindow, delegate, False)

    # =========================================================================
    def scrape(self, books):
        '''Entry point: processes the given list of books.'''
        try:
            log.debug()
            log.debug('-' * 80)
            log.debug('Tebeosfera Scraper v%s' % Resources.SCRIPT_VERSION)
            log.debug('Cache Directory: %s' % Resources.LOCAL_CACHE_DIRECTORY)
            log.debug('Settings File: %s' % Resources.SETTINGS_FILE)
            log.debug('-' * 80)
            log.debug()

            if books:
                self.__scrape(books)

            log.debug('Scraper terminated (scraped %d, skipped %d).' % \
                (self.status[0], self.status[1]))

        except Exception, ex:
            log.handle_error(ex)

    # =========================================================================
    def __scrape(self, books):
        '''The private implementation of the scrape method.'''

        self.status = [0, len(books)]

        # 1. Load configuration
        self.config = Configuration()
        self.config.load_defaults()

        # 2. Show the comic form (status window) on its own thread
        comic_form = ComicForm.show_threadsafe(self)

        try:
            scrape_cache = {}

            # 3. Sort and wrap books
            books = [ComicBook(book, self) for book in books]
            books = self.__sort_books(books)

            # 4. Main processing loop
            i = 0
            orig_length = len(books)
            while i < len(books):
                if self.__cancelled_b:
                    break

                book = books[i]
                delayed_b = i >= orig_length

                # Inter-scrape delay
                if i != 0 and not delayed_b:
                    self.__wait_until_ready()
                    if self.__cancelled_b:
                        break

                # Notify listeners
                num_remaining = len(books) - i
                for start_scrape in self.start_scrape_listeners:
                    start_scrape(book, num_remaining)

                # Scrape this book
                manual_search_b = False
                fast_rescrape_b = self.config.fast_rescrape_b and not delayed_b
                autoscrape_b = self.config.autochoose_series_b and \
                    not self.config.confirm_issue_b and not delayed_b
                bookstatus = BookStatus("DELAYED") if delayed_b \
                    else BookStatus("UNSCRAPED")

                while not self.__cancelled_b:
                    bookstatus = self.__scrape_book(
                        book, scrape_cache, manual_search_b,
                        fast_rescrape_b, autoscrape_b, bookstatus)

                    if bookstatus.equals("UNSCRAPED"):
                        manual_search_b = True
                        continue
                    elif bookstatus.equals("SCRAPED"):
                        self.status[0] += 1
                        self.status[1] -= 1
                        break
                    elif bookstatus.equals("SKIPPED"):
                        break
                    elif bookstatus.equals("DELAYED"):
                        if not delayed_b:
                            books.append(book)
                        break

                GC.Collect()
                GC.WaitForPendingFinalizers()
                i += 1

        finally:
            self.comicrack.MainWindow.Activate()
            if comic_form:
                comic_form.close_threadsafe()

    # =========================================================================
    def __scrape_book(self, book, scrape_cache, manual_search_b,
                      fast_rescrape_b, autoscrape_b, prev_status=None):
        '''
        The heart of the main processing loop. Scrapes a single book by
        finding the matching series and issue on tebeosfera.com.
        '''

        Application.DoEvents()
        if self.__cancelled_b:
            return BookStatus("SKIPPED")
        if prev_status is None:
            prev_status = BookStatus("UNSCRAPED")

        # 1. Skip if tagged
        if book.skip_b:
            log.debug('Book tagged for skip, skipping.')
            return BookStatus("SKIPPED")

        # 2. Fast rescrape: if the book already knows its issue URL
        issue_ref = book.issue_ref
        if issue_ref and fast_rescrape_b:
            log.debug('Fast rescrape: %s' % sstr(issue_ref))
            try:
                issue = tbfscraper.query_issue(issue_ref)
                book.update(issue)
                return BookStatus("SCRAPED")
            except:
                log.debug_exc('Error during fast rescrape')
                return BookStatus("DELAYED")

        # 3. Try to find the series for this book
        key = book.unique_series_s

        # 3a. Check if book already knows its series URL
        if key not in scrape_cache and not manual_search_b:
            series_ref = book.series_ref
            if series_ref and fast_rescrape_b:
                log.debug('Rescraping series: %s' % sstr(series_ref))
                scrape_cache[key] = ScrapedSeries(series_ref)

        # 3b. Search tebeosfera for the series
        search_terms_s = None
        series_refs = None
        if key not in scrape_cache:
            search_terms_s = book.series_s
            if manual_search_b or not search_terms_s:
                # Show search dialog
                log.debug('Asking user for search terms...')
                with SearchForm(self.comicrack.MainWindow, search_terms_s,
                        prev_status.get_failed_search_terms_s() \
                            if prev_status else None) as search_form:
                    search_form_result = search_form.show_form()

                log.debug('User chose: %s' % \
                    search_form_result.get_debug_string())

                if search_form_result.equals("SEARCH"):
                    search_terms_s = search_form_result.get_search_terms_s()
                elif search_form_result.equals("CANCEL"):
                    self.__cancelled_b = True
                    return BookStatus("SKIPPED")
                elif search_form_result.equals("SKIP"):
                    return BookStatus("SKIPPED")
                elif search_form_result.equals("PERMSKIP"):
                    book.skip_forever()
                    return BookStatus("SKIPPED")

            # Query tebeosfera for matching collections
            series_refs = tbfscraper.search_collections(
                search_terms_s, self.config.max_search_results_n)
            if self.__cancelled_b:
                return BookStatus("SKIPPED")
            if not series_refs:
                return BookStatus("UNSCRAPED", search_terms_s)

        # 3c. Show series selection dialog
        while True:
            force_issue_dialog_b = self.config.confirm_issue_b
            if key not in scrape_cache:
                if not series_refs or not search_terms_s:
                    return BookStatus("UNSCRAPED")

                # Show the series selection dialog
                with SeriesForm(self.comicrack.MainWindow, search_terms_s,
                    series_refs) as series_form:
                    series_form_result = series_form.show_form()

                if series_form_result.equals("CANCEL") or self.__cancelled_b:
                    self.__cancelled_b = True
                    return BookStatus("SKIPPED")
                elif series_form_result.equals("SKIP"):
                    return BookStatus("SKIPPED")
                elif series_form_result.equals("PERMSKIP"):
                    book.skip_forever()
                    return BookStatus("SKIPPED")
                elif series_form_result.equals("SEARCH"):
                    return BookStatus("UNSCRAPED")
                elif series_form_result.equals("SHOW") or \
                     series_form_result.equals("OK"):
                    selected_ref = series_form_result.get_ref()
                    scraped_series = ScrapedSeries(selected_ref)
                    force_issue_dialog_b = series_form_result.equals("SHOW")
                    scrape_cache[key] = scraped_series

            # 4. Now that we know the series, find the issue
            scraped_series = scrape_cache[key]
            series_ref = scraped_series.series_ref

            # 4a. Try to find the issue automatically
            issue_ref = None
            if autoscrape_b:
                if book.issue_num_s:
                    issue_ref = tbfscraper.query_issue_ref(
                        series_ref, book.issue_num_s)
                if issue_ref is None:
                    log.debug('Auto-scrape could not find issue.')
                    del scrape_cache[key]
                    return BookStatus("DELAYED")

            else:
                # 4b. Interactive issue selection
                issue_form_result = self.__choose_issue_ref(
                    book, scraped_series, force_issue_dialog_b)

                if issue_form_result.equals("CANCEL") or self.__cancelled_b:
                    self.__cancelled_b = True
                    return BookStatus("SKIPPED")
                elif issue_form_result.equals("SKIP"):
                    if force_issue_dialog_b:
                        del scrape_cache[key]
                    return BookStatus("SKIPPED")
                elif issue_form_result.equals("PERMSKIP"):
                    book.skip_forever()
                    return BookStatus("SKIPPED")
                elif issue_form_result.equals("BACK"):
                    del scrape_cache[key]
                    continue  # re-enter the while True loop for series selection
                else:
                    issue_ref = issue_form_result.get_ref()

            if issue_ref is not None:
                # Fetch and apply the issue data
                log.debug('Querying tebeosfera for issue details...')
                issue = tbfscraper.query_issue(issue_ref)
                book.update(issue)
                return BookStatus("SCRAPED")

        # Should never get here
        raise Exception('Unexpected exit from __scrape_book')

    # =========================================================================
    def __choose_issue_ref(self, book, scraped_series, force_dialog_b):
        '''
        Tries to find the right issue in a series, either by auto-matching
        the issue number, or by showing the IssueForm dialog to the user.
        '''
        series_ref = scraped_series.series_ref

        # Try to auto-match the issue number first
        if not force_dialog_b and book.issue_num_s:
            try:
                issue_ref = tbfscraper.query_issue_ref(
                    series_ref, book.issue_num_s)
                if issue_ref:
                    log.debug('Auto-matched issue #%s' % book.issue_num_s)
                    return IssueFormResult(DialogResult.OK,
                                           issue_ref)
            except:
                log.debug_exc('Error auto-matching issue')

        # Fetch all issues for this series
        issue_refs = scraped_series.issue_refs
        if not issue_refs:
            issue_refs = tbfscraper.query_issue_refs(series_ref)
            scraped_series.issue_refs = issue_refs

        if not issue_refs:
            # No issues found; show a message and return BACK
            MessageBox.Show(self.comicrack.MainWindow,
                'No issues found for this series.',
                'No Issues', MessageBoxButtons.OK, MessageBoxIcon.Warning)
            return IssueFormResult(DialogResult.Retry)

        # Show the issue selection dialog
        with IssueForm(self.comicrack.MainWindow,
            series_ref.series_name_s, issue_refs,
            book.issue_num_s) as issue_form:
            return issue_form.show_form()

    # =========================================================================
    def __wait_until_ready(self):
        '''Waits for the inter-scrape delay to pass.'''
        delay = self.config.scrape_delay_n
        if delay <= 0:
            return
        log.debug('Waiting %d seconds before scraping next book...' % delay)
        for _ in range(delay):
            if self.__cancelled_b:
                return
            # ComicRack's UI thread: Join, unlike Sleep, keeps it responsive
            Thread.CurrentThread.Join(1000)

    # =========================================================================
    def __sort_books(self, books):
        '''
        Sorts books by series name and issue number, putting
        quickly-rescrapable books first.
        '''
        slow_books = []
        fast_books = []

        if self.config.fast_rescrape_b:
            for book in books:
                if book.skip_b or book.issue_ref:
                    fast_books.append(book)
                else:
                    slow_books.append(book)
        else:
            slow_books = list(books)

        def cmp_books(book1, book2):
            result = cmp(book1.unique_series_s, book2.unique_series_s)
            if result == 0:
                n1 = book1.issue_num_s or ''
                n2 = book2.issue_num_s or ''
                def pad(num):
                    try:
                        f = float(num.lower().strip('abcdefgh'))
                        if f < 10:
                            return '000' + num
                        elif f < 100:
                            return '00' + num
                        elif f < 1000:
                            return '0' + num
                        return num
                    except:
                        return num
                result = cmp(pad(n1), pad(n2))
            return result

        slow_books.sort(cmp_books)
        fast_books.sort(cmp_books)
        return fast_books + slow_books
