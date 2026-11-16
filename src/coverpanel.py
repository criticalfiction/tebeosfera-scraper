''' ===========================================================================

This module defines CoverPanel, the cover preview shown beside the series
and issue lists, so the user can see which match is the right comic.

Covers are downloaded on a background thread so the dialog stays
responsive, and cached for the life of the panel so moving back to a row
shows its cover immediately.

License: Apache 2.0

=========================================================================== '''
import clr
import log
import utils
from utils import sstr
import tbfscraper

clr.AddReference('System.Windows.Forms')
from System.Windows.Forms import Panel, PictureBox, PictureBoxSizeMode, \
    Label, BorderStyle, DockStyle

clr.AddReference('System.Drawing')
from System.Drawing import Color, ContentAlignment

clr.AddReference('System')
from System.Threading import Thread, ThreadStart


# ===========================================================================
class CoverPanel(Panel):
    '''
    Shows the cover of a SeriesRef or IssueRef. Call show_cover(ref) when the
    selection changes; only call it once the owning form's window exists
    (e.g. from its Shown event or later), since results are delivered back
    to the UI thread through this panel's window handle.
    '''

    def __init__(self):
        self.BorderStyle = BorderStyle.FixedSingle
        self.BackColor = Color.White

        self.__picture = PictureBox()
        self.__picture.Dock = DockStyle.Fill
        self.__picture.SizeMode = PictureBoxSizeMode.Zoom
        self.Controls.Add(self.__picture)

        self.__label = Label()
        self.__label.Dock = DockStyle.Fill
        self.__label.TextAlign = ContentAlignment.MiddleCenter
        self.__label.ForeColor = Color.Gray
        self.Controls.Add(self.__label)

        # key -> Image, or None when the comic has no cover
        self.__cache = {}
        # key of the ref the user is looking at now
        self.__wanted = None

        # Optional callable(ref, details): called on the UI thread when a
        # preview had to read the ref's own page and found its details
        # (see tbfscraper.query_preview), so the list can show them.
        self.on_details = None

        self.Disposed += self.__on_disposed
        self.__show_text('')

    # =========================================================================
    def show_cover(self, ref):
        '''Shows the cover for ref (a SeriesRef/IssueRef, or None).'''
        if ref is None:
            self.__wanted = None
            self.__show_text('')
            return

        key = type(ref).__name__ + ':' + ref._cmpkey_s
        self.__wanted = key
        if key in self.__cache:
            self.__show_image(self.__cache[key])
            return

        self.__show_text('Loading cover...')

        def download():
            img, details = None, None
            try:
                img, details = tbfscraper.query_preview(ref)
            except Exception, ex:
                log.debug('cover preview failed for %s: %s' % (key, sstr(ex)))

            def deliver():
                if self.IsDisposed:
                    if img is not None:
                        img.Dispose()
                    return
                if details and self.on_details:
                    try:
                        self.on_details(ref, details)
                    except Exception, ex:
                        log.debug('preview details not shown: %s' % sstr(ex))
                if key in self.__cache:
                    # another download for the same cover finished first
                    if img is not None:
                        img.Dispose()
                else:
                    self.__cache[key] = img
                # ignore it if the user has moved to another row meanwhile
                if self.__wanted == key:
                    self.__show_image(self.__cache[key])

            utils.invoke(self, deliver, False)

        thread = Thread(ThreadStart(download))
        thread.IsBackground = True
        thread.Start()

    # =========================================================================
    def __show_image(self, img):
        if img is None:
            self.__show_text('No cover available')
            return
        self.__picture.Image = img
        self.__label.Visible = False
        self.__picture.Visible = True

    # =========================================================================
    def __show_text(self, text):
        self.__picture.Image = None
        self.__picture.Visible = False
        self.__label.Text = text
        self.__label.Visible = True

    # =========================================================================
    def __on_disposed(self, sender, event):
        del sender, event
        self.__picture.Image = None
        for img in self.__cache.values():
            if img is not None:
                img.Dispose()
        self.__cache = {}
