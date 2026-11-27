# IronPython 2.7 script, run by test_ui.ps1 inside ComicRack CE's IronPython.
# Opens the real series/issue dialogs with live data, waits for the cover
# previews, switches rows, and saves screenshots.
import sys, clr
SRC, OUT = sys.argv[1], sys.argv[2]
sys.path.append(SRC)

clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Drawing')
from System.Windows.Forms import Application
from System.Drawing import Bitmap, Rectangle
from System.Drawing.Imaging import ImageFormat
from System.Threading import Thread
from System import DateTime

from resources import Resources
Resources.initialize()
import tbfscraper
from seriesform import SeriesForm
from issueform import IssueForm

results = []
def check(label, ok, detail=''):
    results.append(ok)
    print('%s %s %s' % ('ok  ' if ok else 'FAIL', label, detail))

def pump(seconds, until=None):
    end = DateTime.Now.AddSeconds(seconds)
    while DateTime.Now < end:
        Application.DoEvents()
        if until and until():
            return True
        Thread.CurrentThread.Join(50)   # waits while still pumping (STA)
    return bool(until and until())

def cover_state(form, name):
    panel = getattr(form, '_%s__cover' % name)
    pic = panel._CoverPanel__picture
    label = panel._CoverPanel__label
    return pic, label

def snapshot(form, path):
    bmp = Bitmap(form.Width, form.Height)
    form.DrawToBitmap(bmp, Rectangle(0, 0, form.Width, form.Height))
    bmp.Save(path, ImageFormat.Png)
    bmp.Dispose()

def select_row(form, name, index):
    dgv = getattr(form, '_%s__dgv' % name)
    dgv.ClearSelection()
    dgv.Rows[index].Selected = True
    dgv.CurrentCell = dgv.Rows[index].Cells[0]

# ---------------------------------------------------------------- series
refs = tbfscraper.search_collections('Miedo', 25)   # real .NET POST
check('search via .NET HttpWebRequest', len(refs) > 0, '%d results' % len(refs))

form = SeriesForm(None, 'Miedo', refs)
form.Show()
pic, label = cover_state(form, 'SeriesForm')
loaded = pump(30, lambda: pic.Visible and pic.Image is not None)
check('series: first row cover shown', loaded,
      '%sx%s' % (pic.Image.Width, pic.Image.Height) if loaded else label.Text)
first = pic.Image

select_row(form, 'SeriesForm', 1)        # MIEDO (2003, GLENAT)
changed = pump(30, lambda: pic.Image is not None and pic.Image is not first)
check('series: cover follows selection (row 2)', changed)
pump(1)
snapshot(form, OUT + '\\series_form.png')

select_row(form, 'SeriesForm', 0)        # back: should come from cache at once
Application.DoEvents()
check('series: revisited row shown from cache', pic.Image is first)
form.Close()
pump(1)

# ---------------------------------------------------------------- issues
salvat = tbfscraper.SeriesRef('capitan_trueno_el_2017_salvat_-60_aniversario-',
    series_name_s='CAPITAN TRUENO, EL (2017, SALVAT) -60 ANIVERSARIO-',
    url_s='https://www.tebeosfera.com/colecciones/capitan_trueno_el_2017_salvat_-60_aniversario-.html')
issues = tbfscraper.query_issue_refs(salvat)
form = IssueForm(None, salvat.series_name_s, issues, '3')
form.Show()
pic, label = cover_state(form, 'IssueForm')
loaded = pump(30, lambda: pic.Visible and pic.Image is not None)
sel = form._IssueForm__dgv.SelectedRows
selected_num = sel[0].Cells[0].Value if sel.Count else None
check('issues: book #3 is the preselected row', selected_num == '3', repr(selected_num))
# the cover shown must be #3's, i.e. the cached image for that ref
panel = form._IssueForm__cover
key = 'IssueRef:' + sel[0].Tag._cmpkey_s if sel.Count else None
check('issues: cover shown is #3\'s', loaded and
      panel._CoverPanel__cache.get(key) is pic.Image)
pump(1)
snapshot(form, OUT + '\\issue_form.png')

# title/date columns, from the gallery captions
dgv = form._IssueForm__dgv
def row_of(num):
    return [i for i in range(dgv.Rows.Count) if dgv.Rows[i].Cells[0].Value == num][0]
def cells(num):
    r = dgv.Rows[row_of(num)]
    return (r.Cells[1].Value, r.Cells[2].Value)
check('issues: #3 title and date', cells('3') == (u'\xa1El Se\xf1or de la Guerra!', '12 Mar 2017'),
      repr(cells('3')))
check('issues: #55 blank before it is selected', cells('55') == ('', ''), repr(cells('55')))

# an issue the gallery doesn't cover (#55): read from its own page
before = pic.Image
select_row(form, 'IssueForm', row_of('55'))
loaded = pump(30, lambda: pic.Image is not None and pic.Image is not before)
check('issues: #55 cover (not in gallery) shown', loaded)
check('issues: #55 title and date filled in',
      cells('55') == (u'\xa1El Combate por Sigridsholm!', '11 Mar 2018'), repr(cells('55')))
pump(1)
snapshot(form, OUT + '\\issue_form_55.png')
form.Close()
pump(1)

# ---------------------------------------------------------------- text
check('cp1252 fix works in IronPython', tbfscraper._fix_cp1252(u'a\x97b\x92c') == u'a\u2014b\u2019c',
      repr(tbfscraper._fix_cp1252(u'a\x97b\x92c')))

# ---------------------------------------------------------------- status window
from comicform import ComicForm
from pluginbookdata import PluginBookData
from System.Drawing import Color, Graphics

class FakeApp(object):
    '''Stands in for ComicRack.App: records which page API was used.'''
    def __init__(self):
        self.calls = []
    def _bitmap(self, color):
        bmp = Bitmap(140, 200)
        g = Graphics.FromImage(bmp)
        g.Clear(color)
        g.Dispose()
        return bmp
    def GetComicPage(self, cb, page):
        self.calls.append(('GetComicPage', page))
        return self._bitmap(Color.Orange)
    def GetComicThumbnail(self, cb, page):
        self.calls.append(('GetComicThumbnail', page))
        return self._bitmap(Color.SteelBlue)

class FakeCR(object):
    MainWindow = None
    def __init__(self):
        self.App = FakeApp()

class FakeScraper(object):
    def __init__(self):
        self.comicrack = FakeCR()
        self.start_scrape_listeners = []
        self.cancel_listeners = []
    def cancel(self):
        pass

class FakeCRBook(object):
    Series = 'Miedo'; Number = '1'; Title = ''; Volume = 0; Publisher = ''
    Year = Month = Day = -1; Writer = Penciller = ''
    def __init__(self, path):
        self.FilePath = path

scraper = FakeScraper()
app = scraper.comicrack.App
with_file = PluginBookData(FakeCRBook('C:\\comics\\miedo.cbz'), scraper)
fileless = PluginBookData(FakeCRBook(''), scraper)
with_file.create_image_of_page(0)
fileless.create_image_of_page(0)
check('page API: book with a file uses GetComicPage', app.calls[0] == ('GetComicPage', 0), repr(app.calls))
check('page API: fileless book uses GetComicThumbnail', app.calls[1] == ('GetComicThumbnail', 0))

class ScrapedBook(object):
    def __init__(self, img):
        self.series_s, self.issue_num_s, self.__img = 'Miedo', '1', img
    def create_image_of_page(self, page):
        return self.__img

form = ComicForm.show_threadsafe(scraper)     # its own UI thread, as in a scrape
pic = form._ComicForm__cover_pic
bar = form._ComicForm__progress_bar
check('status: no box before the first book', pump(5, lambda: not pic.Visible))
start = scraper.start_scrape_listeners[0]
start(ScrapedBook(app._bitmap(Color.Orange)), 3)
check('status: cover shown for book 1', pump(5, lambda: pic.Visible and pic.Image is not None))
check('status: progress 0% at book 1 of 3', bar.Value == 0, str(bar.Value))
start(ScrapedBook(None), 2)
check('status: book without an image shows no box', pump(5, lambda: not pic.Visible))
check('status: progress 33% at book 2 of 3', pump(5, lambda: bar.Value == 33), str(bar.Value))
start(ScrapedBook(app._bitmap(Color.Orange)), 1)
pump(5, lambda: pic.Visible)
pump(1)
import utils
utils.invoke(form, lambda: snapshot(form, OUT + '\\status_window.png'), True)
form.close_threadsafe()
pump(1)

# ------------------------------------------------- credit names (IronPython)
for style, want in [(tbfscraper.NAME_SIGNATURE_REAL_SMART, u'Fer (Jos\xe9 Antonio Fern\xe1ndez)'),
                    (tbfscraper.NAME_REAL_SIGNATURE_SMART, u'Manel Fontdevila')]:
    title, text = {tbfscraper.NAME_SIGNATURE_REAL_SMART:
                       (u'FER -Jos\xe9 Antonio Fern\xe1ndez Fern\xe1ndez-', u'FER'),
                   tbfscraper.NAME_REAL_SIGNATURE_SMART:
                       (u'MANEL F. -Manel Fontdevila Subirana-', u'MANEL F.')}[style]
    got = tbfscraper._credit_name(title, text, style)
    check('smart credit name, style %d' % style, got == want, repr(got))
got = tbfscraper._credit_name(u'PEPO P\xc9REZ -Juan Carlos P\xe9rez Garc\xeda-',
                              u'PEPO P\xc9REZ', tbfscraper.NAME_REAL_SIGNATURE_SMART)
check('smart credit name, word not in the name skipped',
      got == u'Juan Carlos P\xe9rez (Pepo P\xe9rez)', repr(got))
got = tbfscraper._credit_name(u'JMV -Jes\xfas Mart\xednez Del Vas-', u'JMV',
                              tbfscraper.NAME_SIGNATURE)
check('initialism stays upper-case', got == u'JMV', repr(got))
# ---------------------------------------------------------------- config
# Opened and closed without OK, so the user's settings are not changed.
from configform import ConfigForm
form = ConfigForm(None)
form.Show()
tabs = form._ConfigForm__tabs
tabs.SelectedIndex = 1          # Behavior
pump(1)
page = tabs.TabPages[1]
lowest = max(c.Bottom for c in page.Controls)
check('config: all Behavior options inside the tab',
      lowest <= page.ClientSize.Height, '%d <= %d' % (lowest, page.ClientSize.Height))
snapshot(form, OUT + '\\config_behavior.png')
tabs.SelectedIndex = 2          # Credits
pump(1)
page = tabs.TabPages[2]
check('config: Credits tab is there', page.Text == 'Credits', page.Text)
lowest = max(c.Bottom for c in page.Controls)
check('config: all Credits options inside the tab',
      lowest <= page.ClientSize.Height, '%d <= %d' % (lowest, page.ClientSize.Height))
snapshot(form, OUT + '\\config_credits.png')
# the credit name style drop-down
combo = form._ConfigForm__name_style
check('config: name style choices',
      list(combo.Items) == ['Signature', 'Real name', 'Signature (Real name)',
                            'Real name (Signature)', 'Signature (Real name) [Smart]',
                            'Real name (Signature) [Smart]'], list(combo.Items))
check('config: name style shows the saved setting',
      combo.SelectedIndex == form._ConfigForm__config.credit_name_style_n,
      combo.SelectedIndex)
from System.Drawing import Font, Size as DSize
from System.Windows.Forms import CheckBox as WCheckBox, Label as WLabel, \
    TextRenderer, TextFormatFlags
def text_cut_off(c):
    '''None if c shows all its text, else why not.'''
    if isinstance(c, WLabel):
        need = c.GetPreferredSize(DSize(c.Width, 0)).Height
        return None if c.Height >= need else 'needs %d px, has %d' % (need, c.Height)
    one_line = c.GetPreferredSize(DSize.Empty)
    text = TextRenderer.MeasureText(c.Text, c.Font)
    box = one_line.Width - text.Width
    wrapped = TextRenderer.MeasureText(c.Text, c.Font, DSize(c.Width - box, 0),
                                       TextFormatFlags.WordBreak)
    return None if c.Height >= wrapped.Height else \
        'text needs %d px, has %d' % (wrapped.Height, c.Height)
def check_tab_text(when, index):
    tabs.SelectedIndex = index
    pump(1)
    page = tabs.TabPages[index]
    controls = sorted(page.Controls, key=lambda c: c.Top)
    cut = [(c.Text[:30], text_cut_off(c)) for c in controls
           if isinstance(c, (WLabel, WCheckBox)) and text_cut_off(c)]
    check('%s: %s text all shown' % (when, page.Text), not cut, cut)
    overlaps = [(a.Text[:20], b.Text[:20]) for a, b in zip(controls, controls[1:])
                if b.Top < a.Bottom]
    check('%s: %s controls don\'t overlap' % (when, page.Text), not overlaps, overlaps)
    lowest = max(c.Bottom for c in controls)
    check('%s: %s controls inside the tab' % (when, page.Text),
          lowest <= page.ClientSize.Height, (lowest, page.ClientSize.Height))
    return page
for index in (1, 2):
    check_tab_text('config', index)
# The reported cut-off: the font scaled for a larger display but the layout
# not (the name style label wrapped "as:" onto a hidden second line, and
# other text was cut off too). Done by making the font 1.5 times bigger:
# in Dpi scaling mode that doesn't move or resize anything.
form.Font = Font(form.Font.FontFamily, form.Font.Size * 1.5)
for index in (1, 2):
    page = check_tab_text('config 150% text', index)
    snapshot(form, OUT + '\\config_%s_150_text.png' % page.Text.lower())
form.Close()
pump(1)
# OK saves the chosen style. Settings go to temporary files, so the user's
# own settings are not changed.
# (.NET, not os/tempfile: ComicRack's IronPython has no standard library)
from System.IO import Path, Directory
from configuration import Configuration
saved = (Resources.SETTINGS_FILE, Resources.ADVANCED_FILE)
tmp = Path.Combine(Path.GetTempPath(), Path.GetRandomFileName())
Directory.CreateDirectory(tmp)
Resources.SETTINGS_FILE = Path.Combine(tmp, 'settings.dat')
Resources.ADVANCED_FILE = Path.Combine(tmp, 'advanced.dat')
try:
    check('config: name style defaults to Signature',
          Configuration().credit_name_style_n == 0,
          Configuration().credit_name_style_n)
    for index in (1, 2, 3, 4, 5, 0):
        form = ConfigForm(None)
        form.Show()
        form._ConfigForm__name_style.SelectedIndex = index
        form._ConfigForm__on_ok(None, None)
        pump(1)
        check('config: OK saves name style %d' % index,
              Configuration().credit_name_style_n == index,
              Configuration().credit_name_style_n)
finally:
    Resources.SETTINGS_FILE, Resources.ADVANCED_FILE = saved
    Directory.Delete(tmp, True)
pump(1)

print('%d failure(s)' % results.count(False))
