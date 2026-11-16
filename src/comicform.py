''' ===========================================================================

This module defines ComicForm, the always-visible status window that shows
the current progress of the scrape operation. It runs on its own application
thread so it stays responsive while the main thread does network IO.

License: Apache 2.0

=========================================================================== '''
import clr
import log
import utils
from cvform import CVForm

clr.AddReference('System.Windows.Forms')
from System.Windows.Forms import ProgressBar, Label, Button, \
    ProgressBarStyle, DockStyle, FormBorderStyle, Application, \
    DialogResult, PictureBox, \
    PictureBoxSizeMode, Control

clr.AddReference('System.Drawing')
from System.Drawing import Size, Point, Font, FontStyle, \
    FontFamily, ContentAlignment, Image, Color

clr.AddReference('System')
from System.Threading import Thread, ThreadStart, ApartmentState
from System import IDisposable  # noqa: kept for potential future use


# ===========================================================================
class ComicForm(CVForm):
    '''
    The always-visible status window shown during a scrape operation.
    Displays the current book's cover, progress bar, and remaining count.
    '''

    def __init__(self, scraper):
        super(ComicForm, self).__init__(scraper.comicrack.MainWindow,
                                         'comicform_loc', 'comicform_sz')
        self.Text = 'Tebeosfera Scraper'
        # Inner area: progress bar ends at y 315, x up to 310.
        self.ClientSize = Size(320, 325)
        self.FormBorderStyle = FormBorderStyle.FixedSingle
        self.ControlBox = True  # allow the X button (acts as cancel)
        self.MaximizeBox = False
        self.MinimizeBox = False
        self.ShowInTaskbar = True  # this form is shown during scraping
        self.__scraper = scraper
        self.__progress_bar = None
        self.__status_label = None
        self.__count_label = None
        self.__cover_pic = None
        self.__closed_by_thread = False
        self.__books_started = 0

        self.__build_ui()

        # Closing via the X button cancels the scrape
        self.FormClosing += self.__on_closing

        # Register as listeners with the scrape engine
        scraper.start_scrape_listeners.append(self.__start_scrape)
        scraper.cancel_listeners.append(self.close_threadsafe)

    # =========================================================================
    def __build_ui(self):
        '''Builds the form's UI.'''

        # Title label
        title = Label()
        title.Text = 'Tebeosfera Scraper'
        title.Location = Point(10, 10)
        title.Size = Size(300, 25)
        title.Font = Font(FontFamily.GenericSansSerif, 12, FontStyle.Bold)
        title.TextAlign = ContentAlignment.MiddleCenter
        self.Controls.Add(title)

        # Cover of the book being scraped; hidden until there is one
        self.__cover_pic = PictureBox()
        self.__cover_pic.Location = Point(90, 40)
        self.__cover_pic.Size = Size(140, 200)
        self.__cover_pic.SizeMode = PictureBoxSizeMode.Zoom  # keep proportions
        self.__cover_pic.Visible = False
        self.Controls.Add(self.__cover_pic)

        # Status label
        self.__status_label = Label()
        self.__status_label.Text = 'Preparing to scrape...'
        self.__status_label.Location = Point(10, 250)
        self.__status_label.Size = Size(300, 20)
        self.__status_label.TextAlign = ContentAlignment.MiddleCenter
        self.Controls.Add(self.__status_label)

        # Count label
        self.__count_label = Label()
        self.__count_label.Text = ''
        self.__count_label.Location = Point(10, 270)
        self.__count_label.Size = Size(300, 20)
        self.__count_label.ForeColor = Color.Gray
        self.__count_label.TextAlign = ContentAlignment.MiddleCenter
        self.Controls.Add(self.__count_label)

        # Progress bar
        self.__progress_bar = ProgressBar()
        self.__progress_bar.Location = Point(10, 295)
        self.__progress_bar.Size = Size(300, 20)
        self.__progress_bar.Style = ProgressBarStyle.Continuous
        self.__progress_bar.Minimum = 0
        self.__progress_bar.Maximum = 100
        self.__progress_bar.Value = 0
        self.Controls.Add(self.__progress_bar)

    # =========================================================================
    def __start_scrape(self, book, num_remaining):
        '''
        Called by the scrape engine when starting to scrape a new book.
        Updates the UI to show the current book's status.
        '''
        # The cover comes from ComicRack's plugin API, so get it here, on the
        # scrape engine's (ComicRack's) thread, as the Comic Vine Scraper
        # does. Only the finished image is handed to this window's thread.
        img = None
        try:
            img = book.create_image_of_page(0)
        except Exception, ex:
            log.debug('ComicForm cover error: %s' % utils.sstr(ex))

        # Progress: books already started vs. total. num_remaining includes
        # this book, and grows if a book is put back for a retry at the end.
        self.__books_started += 1
        done = self.__books_started - 1
        total = done + num_remaining
        percent = min(100, 100 * done // max(1, total))

        def update_ui():
            if self.IsDisposed:
                if img is not None:
                    img.Dispose()
                return
            try:
                self.__status_label.Text = 'Scraping: %s #%s' % (
                    book.series_s, book.issue_num_s)
                self.__count_label.Text = '%d books remaining' % num_remaining
                self.__progress_bar.Value = percent

                old = self.__cover_pic.Image
                self.__cover_pic.Image = img
                # nothing to show (e.g. no pages): hide it, not a grey box
                self.__cover_pic.Visible = img is not None
                if old is not None:
                    old.Dispose()
            except Exception, ex:
                log.debug('ComicForm update error: %s' % utils.sstr(ex))

        utils.invoke(self, update_ui, False)

    # =========================================================================
    def __on_closing(self, sender, event):
        '''
        Called when the user closes the form via the X button.
        Cancels the scrape operation (unless we're closing programmatically).
        '''
        if not self.__closed_by_thread:
            # The user clicked X, so cancel the scrape
            self.__scraper.cancel()

    # =========================================================================
    def close_threadsafe(self):
        '''Closes this form from any thread (used by the scrape engine).'''
        self.__closed_by_thread = True
        def do_close():
            try:
                img = self.__cover_pic.Image
                self.__cover_pic.Image = None
                if img is not None:
                    img.Dispose()
                self.Close()
                self.Dispose()
            except:
                pass
        utils.invoke(self, do_close, False)

    # =========================================================================
    @classmethod
    def show_threadsafe(cls, scraper):
        '''
        Creates and shows this form on its own UI thread so it stays
        responsive while the main thread performs network IO.
        Returns the form instance.
        '''
        form = cls(scraper)

        def run_form():
            try:
                Application.Run(form)
            except Exception, ex:
                log.debug('ComicForm thread error: %s' % utils.sstr(ex))

        thread = Thread(ThreadStart(run_form))
        thread.IsBackground = True
        thread.SetApartmentState(ApartmentState.STA)
        thread.Start()

        # Give the form time to initialize. This runs on ComicRack's UI
        # thread; Join (unlike Sleep) keeps it handling window messages.
        Thread.CurrentThread.Join(200)

        return form

    # =========================================================================
    def show_form(self):
        '''Shows this form (blocking). Used for standalone testing.'''
        self.ShowDialog()
