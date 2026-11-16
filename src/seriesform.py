''' ===========================================================================

This module defines SeriesForm, the dialog where the user selects which
series (collection) matches their comic book from a list of search results
from tebeosfera.com.

License: Apache 2.0

=========================================================================== '''
import clr
import log
import utils
from utils import sstr
from cvform import CVForm
from coverpanel import CoverPanel

clr.AddReference('System.Windows.Forms')
from System.Windows.Forms import DataGridView, DataGridViewColumn, \
    DataGridViewTextBoxColumn, DataGridViewButtonColumn, \
    DataGridViewAutoSizeColumnsMode, DataGridViewSelectionMode, \
    DataGridViewCellEventArgs, Button, Label, DialogResult, \
    DockStyle, ScrollBars, DataGridViewColumnHeadersHeightSizeMode, \
    DataGridViewCellMouseEventArgs, Keys, Control, MessageBox, MessageBoxButtons, \
    MessageBoxIcon

clr.AddReference('System.Drawing')
from System.Drawing import Size, Point, Font, FontStyle, Color, FontFamily


# ===========================================================================
class SeriesFormResult(object):
    '''
    The result of the SeriesForm dialog.
    id: 'OK'|'SHOW'|'SKIP'|'PERMSKIP'|'SEARCH'|'CANCEL'
    '''

    def __init__(self, dialog_result, series_ref=None):
        self.__id = ''
        self.__series_ref = series_ref

        if dialog_result == DialogResult.OK:
            self.__id = 'OK'
        elif dialog_result == DialogResult.Yes:
            self.__id = 'SHOW'
        elif dialog_result == DialogResult.Ignore:
            self.__id = 'SKIP'
        elif dialog_result == DialogResult.Abort:
            self.__id = 'PERMSKIP'
        elif dialog_result == DialogResult.Retry:
            self.__id = 'SEARCH'
        elif dialog_result == DialogResult.Cancel:
            self.__id = 'CANCEL'
        else:
            self.__id = 'CANCEL'

    def equals(self, id_s):
        return self.__id == id_s

    def get_ref(self):
        return self.__series_ref

    def get_debug_string(self):
        if self.__series_ref:
            return '%s: %s' % (self.__id.lower(), sstr(self.__series_ref))
        return self.__id.lower()


# ===========================================================================
class SeriesForm(CVForm):
    '''
    A dialog that shows a list of matching series (collections) from
    tebeosfera.com and lets the user select one.
    '''

    def __init__(self, parent, search_terms_s, series_refs):
        super(SeriesForm, self).__init__(parent, 'seriesform_loc', 'seriesform_sz')
        self.Text = 'Select Series'
        # Inner area: grid x 10-580, cover x 590-790, y 35-315;
        # buttons y 325-355.
        self.ClientSize = Size(800, 365)
        self.__search_terms_s = search_terms_s or ''
        # Already ranked best-match-first by tbfscraper.search_collections
        self.__series_refs = list(series_refs)
        self.__selected_ref = None
        self.__dgv = None
        self.__cover = None
        self.__shown = False

        self.__build_ui()

        # Covers are loaded once the window exists (see CoverPanel).
        self.Shown += self.__on_shown

    # =========================================================================
    def __build_ui(self):
        '''Builds the form's UI.'''

        # Header label
        header = Label()
        header.Text = 'Found %d matching series for "%s". Select the correct one:' % \
            (len(self.__series_refs), self.__search_terms_s)
        header.Location = Point(10, 5)
        header.Size = Size(780, 25)
        header.Font = Font(FontFamily.GenericSansSerif, 9, FontStyle.Bold)
        self.Controls.Add(header)

        # DataGridView for series results
        self.__dgv = DataGridView()
        self.__dgv.Location = Point(10, 35)
        self.__dgv.Size = Size(570, 280)
        self.__dgv.AllowUserToAddRows = False
        self.__dgv.AllowUserToDeleteRows = False
        self.__dgv.ReadOnly = True
        self.__dgv.SelectionMode = DataGridViewSelectionMode.FullRowSelect
        self.__dgv.MultiSelect = False
        self.__dgv.AutoSizeColumnsMode = \
            DataGridViewAutoSizeColumnsMode.Fill
        self.__dgv.ColumnHeadersHeightSizeMode = \
            DataGridViewColumnHeadersHeightSizeMode.AutoSize
        self.__dgv.ScrollBars = ScrollBars.Vertical
        self.__dgv.RowHeadersVisible = False
        self.__dgv.CellDoubleClick += self.__on_double_click
        self.__dgv.KeyDown += self.__on_dgv_key_down
        self.__dgv.SelectionChanged += self.__on_selection_changed

        # Cover preview of the selected series
        self.__cover = CoverPanel()
        self.__cover.Location = Point(590, 35)
        self.__cover.Size = Size(200, 280)
        self.Controls.Add(self.__cover)

        # Add columns
        col_series = DataGridViewTextBoxColumn()
        col_series.Name = 'Series'
        col_series.HeaderText = 'Series'
        col_series.FillWeight = 200
        self.__dgv.Columns.Add(col_series)

        col_year = DataGridViewTextBoxColumn()
        col_year.Name = 'Year'
        col_year.HeaderText = 'Year'
        col_year.FillWeight = 50
        self.__dgv.Columns.Add(col_year)

        col_count = DataGridViewTextBoxColumn()
        col_count.Name = 'Issues'
        col_count.HeaderText = 'Issues'
        col_count.FillWeight = 50
        self.__dgv.Columns.Add(col_count)

        col_publisher = DataGridViewTextBoxColumn()
        col_publisher.Name = 'Publisher'
        col_publisher.HeaderText = 'Publisher'
        col_publisher.FillWeight = 120
        self.__dgv.Columns.Add(col_publisher)

        # Populate rows
        for ref in self.__series_refs:
            idx = self.__dgv.Rows.Add()
            row = self.__dgv.Rows[idx]
            row.Cells[0].Value = ref.series_name_s
            row.Cells[1].Value = str(ref.volume_year_n) if ref.volume_year_n > 0 else ''
            row.Cells[2].Value = str(ref.issue_count_n) if ref.issue_count_n > 0 else ''
            row.Cells[3].Value = ref.publisher_s
            row.Tag = ref

        if self.__dgv.Rows.Count > 0:
            self.__dgv.Rows[0].Selected = True

        self.Controls.Add(self.__dgv)

        # Buttons
        btn_y = 325

        ok_btn = Button()
        ok_btn.Text = 'OK'
        ok_btn.Location = Point(10, btn_y)
        ok_btn.Size = Size(90, 30)
        ok_btn.Click += self.__on_ok
        self.Controls.Add(ok_btn)

        show_btn = Button()
        show_btn.Text = 'Show Issues'
        show_btn.Location = Point(110, btn_y)
        show_btn.Size = Size(100, 30)
        show_btn.Click += self.__on_show_issues
        self.Controls.Add(show_btn)

        search_btn = Button()
        search_btn.Text = 'Search Again'
        search_btn.Location = Point(220, btn_y)
        search_btn.Size = Size(100, 30)
        search_btn.Click += self.__on_search_again
        self.Controls.Add(search_btn)

        skip_btn = Button()
        skip_btn.Text = 'Skip'
        skip_btn.Location = Point(330, btn_y)
        skip_btn.Size = Size(90, 30)
        skip_btn.Click += self.__on_skip
        self.Controls.Add(skip_btn)

        cancel_btn = Button()
        cancel_btn.Text = 'Cancel'
        cancel_btn.Location = Point(430, btn_y)
        cancel_btn.Size = Size(90, 30)
        cancel_btn.Click += self.__on_cancel
        self.Controls.Add(cancel_btn)

        self.AcceptButton = ok_btn

    # =========================================================================
    def __get_selected_ref(self):
        '''Returns the SeriesRef for the currently selected row.'''
        if self.__dgv.SelectedRows.Count > 0:
            return self.__dgv.SelectedRows[0].Tag
        return None

    # =========================================================================
    def __on_shown(self, sender, event):
        self.__shown = True
        self.__cover.show_cover(self.__get_selected_ref())

    # =========================================================================
    def __on_selection_changed(self, sender, event):
        # Selection also changes while the rows are being filled in, before
        # the window exists; the Shown handler covers that first row.
        if self.__shown:
            self.__cover.show_cover(self.__get_selected_ref())

    # =========================================================================
    def __on_ok(self, sender, event):
        ref = self.__get_selected_ref()
        if ref:
            self.__selected_ref = ref
            self.DialogResult = DialogResult.OK
            self.Close()
        else:
            MessageBox.Show(
                self, 'Please select a series first.', 'No Selection',
                MessageBoxButtons.OK,
                MessageBoxIcon.Warning)

    # =========================================================================
    def __on_show_issues(self, sender, event):
        ref = self.__get_selected_ref()
        if ref:
            self.__selected_ref = ref
            self.DialogResult = DialogResult.Yes  # SHOW
            self.Close()

    # =========================================================================
    def __on_search_again(self, sender, event):
        self.DialogResult = DialogResult.Retry  # SEARCH
        self.Close()

    # =========================================================================
    def __on_skip(self, sender, event):
        if Control.ModifierKeys == Keys.Control:
            self.DialogResult = DialogResult.Abort  # PERMSKIP
        else:
            self.DialogResult = DialogResult.Ignore  # SKIP
        self.Close()

    # =========================================================================
    def __on_cancel(self, sender, event):
        self.DialogResult = DialogResult.Cancel
        self.Close()

    # =========================================================================
    def __on_double_click(self, sender, event):
        '''Handle double-click on a row: treat as OK.'''
        ref = self.__get_selected_ref()
        if ref:
            self.__selected_ref = ref
            self.DialogResult = DialogResult.OK
            self.Close()

    # =========================================================================
    def __on_dgv_key_down(self, sender, event):
        '''Handle Enter key in the grid: treat as OK.'''
        if event.KeyCode == Keys.Enter:
            self.__on_ok(sender, event)
            event.Handled = True

    # =========================================================================
    def show_form(self):
        '''Shows the form and returns a SeriesFormResult.'''
        dialog_result = self.ShowDialog()
        return SeriesFormResult(dialog_result, self.__selected_ref)
