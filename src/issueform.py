''' ===========================================================================

This module defines IssueForm, the dialog where the user selects which
issue (numero) matches their comic book from a list of issues in a collection.

License: Apache 2.0

=========================================================================== '''
import clr
import log
import utils
from utils import sstr, natural_compare
from cvform import CVForm
from coverpanel import CoverPanel

clr.AddReference('System.Windows.Forms')
from System.Windows.Forms import DataGridView, DataGridViewTextBoxColumn, \
    DataGridViewAutoSizeColumnsMode, DataGridViewSelectionMode, \
    Button, Label, DialogResult, ScrollBars, \
    DataGridViewColumnHeadersHeightSizeMode, Keys, Control, MessageBox, MessageBoxButtons, \
    MessageBoxIcon

clr.AddReference('System.Drawing')
from System.Drawing import Size, Point, Font, FontStyle, FontFamily


# ===========================================================================
class IssueFormResult(object):
    '''
    The result of the IssueForm dialog.
    id: 'OK'|'BACK'|'SKIP'|'PERMSKIP'|'CANCEL'
    '''

    def __init__(self, dialog_result, issue_ref=None):
        self.__id = ''
        self.__issue_ref = issue_ref

        if dialog_result == DialogResult.OK:
            self.__id = 'OK'
        elif dialog_result == DialogResult.Retry:
            self.__id = 'BACK'
        elif dialog_result == DialogResult.Ignore:
            self.__id = 'SKIP'
        elif dialog_result == DialogResult.Abort:
            self.__id = 'PERMSKIP'
        elif dialog_result == DialogResult.Cancel:
            self.__id = 'CANCEL'
        else:
            self.__id = 'CANCEL'

    def equals(self, id_s):
        return self.__id == id_s

    def get_ref(self):
        return self.__issue_ref

    def get_debug_string(self):
        if self.__issue_ref:
            return '%s: %s' % (self.__id.lower(), sstr(self.__issue_ref))
        return self.__id.lower()


# ===========================================================================
class IssueForm(CVForm):
    '''
    A dialog that shows a list of issues (numeros) for a series and lets
    the user select one.
    '''

    def __init__(self, parent, series_name_s, issue_refs, book_issue_num_s=None):
        super(IssueForm, self).__init__(parent, 'issueform_loc', 'issueform_sz')
        self.Text = 'Select Issue'
        # Inner area: grid x 10-480, cover x 490-690, y 35-315;
        # buttons y 325-355.
        self.ClientSize = Size(700, 365)
        self.__series_name_s = series_name_s or ''
        self.__issue_refs = list(issue_refs)
        # Sort by natural order of issue number
        self.__issue_refs.sort(lambda a, b: natural_compare(a.issue_num_s, b.issue_num_s))
        self.__book_issue_num_s = book_issue_num_s or ''
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
        header.Text = 'Issues in "%s". Select the correct one:' % \
            self.__series_name_s
        header.Location = Point(10, 5)
        header.Size = Size(680, 25)
        header.Font = Font(FontFamily.GenericSansSerif, 9, FontStyle.Bold)
        self.Controls.Add(header)

        # DataGridView for issues
        self.__dgv = DataGridView()
        self.__dgv.Location = Point(10, 35)
        self.__dgv.Size = Size(470, 280)
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

        # Cover preview of the selected issue
        self.__cover = CoverPanel()
        self.__cover.Location = Point(490, 35)
        self.__cover.Size = Size(200, 280)
        self.Controls.Add(self.__cover)
        # Issues past the gallery's first 50 have no title/date yet; they
        # arrive with the cover when the row is selected.
        self.__cover.on_details = self.__on_details

        # Add columns
        col_num = DataGridViewTextBoxColumn()
        col_num.Name = 'Number'
        col_num.HeaderText = '#'
        col_num.FillWeight = 40
        self.__dgv.Columns.Add(col_num)

        col_title = DataGridViewTextBoxColumn()
        col_title.Name = 'Title'
        col_title.HeaderText = 'Title'
        col_title.FillWeight = 220
        self.__dgv.Columns.Add(col_title)

        col_date = DataGridViewTextBoxColumn()
        col_date.Name = 'Date'
        col_date.HeaderText = 'Date'
        col_date.FillWeight = 80
        self.__dgv.Columns.Add(col_date)

        # Populate rows
        selected_idx = 0
        for i, ref in enumerate(self.__issue_refs):
            idx = self.__dgv.Rows.Add()
            row = self.__dgv.Rows[idx]
            row.Cells[0].Value = ref.issue_num_s
            row.Cells[1].Value = ref.title_s
            row.Cells[2].Value = ref.date_s
            row.Tag = ref
            # Try to pre-select the matching issue number
            if self.__book_issue_num_s and \
               ref.issue_num_s == self.__book_issue_num_s:
                selected_idx = idx

        # Selecting now doesn't stick: the grid resets to the first row when
        # its window is created. __on_shown applies it.
        self.__preselect_idx = selected_idx

        self.Controls.Add(self.__dgv)

        # Buttons
        btn_y = 325

        ok_btn = Button()
        ok_btn.Text = 'OK'
        ok_btn.Location = Point(10, btn_y)
        ok_btn.Size = Size(90, 30)
        ok_btn.Click += self.__on_ok
        self.Controls.Add(ok_btn)

        back_btn = Button()
        back_btn.Text = 'Go Back'
        back_btn.Location = Point(110, btn_y)
        back_btn.Size = Size(90, 30)
        back_btn.Click += self.__on_back
        self.Controls.Add(back_btn)

        skip_btn = Button()
        skip_btn.Text = 'Skip'
        skip_btn.Location = Point(210, btn_y)
        skip_btn.Size = Size(90, 30)
        skip_btn.Click += self.__on_skip
        self.Controls.Add(skip_btn)

        cancel_btn = Button()
        cancel_btn.Text = 'Cancel'
        cancel_btn.Location = Point(310, btn_y)
        cancel_btn.Size = Size(90, 30)
        cancel_btn.Click += self.__on_cancel
        self.Controls.Add(cancel_btn)

        self.AcceptButton = ok_btn

    # =========================================================================
    def __get_selected_ref(self):
        if self.__dgv.SelectedRows.Count > 0:
            return self.__dgv.SelectedRows[0].Tag
        return None

    # =========================================================================
    def __on_shown(self, sender, event):
        # Select (and scroll to) the row matching the book's issue number.
        rows = self.__dgv.Rows
        if rows.Count > 0:
            row = rows[self.__preselect_idx]
            self.__dgv.ClearSelection()
            self.__dgv.CurrentCell = row.Cells[0]
            row.Selected = True
            self.__dgv.FirstDisplayedScrollingRowIndex = max(
                0, self.__preselect_idx - 3)
        self.__shown = True
        self.__cover.show_cover(self.__get_selected_ref())

    # =========================================================================
    def __on_details(self, ref, details):
        '''Fills in the title/date of a row once its preview has found them.'''
        for i in range(self.__dgv.Rows.Count):
            row = self.__dgv.Rows[i]
            if row.Tag == ref:
                if not row.Cells[1].Value:
                    row.Cells[1].Value = details.get('title', '')
                if not row.Cells[2].Value:
                    row.Cells[2].Value = details.get('date', '')
                break

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
                self, 'Please select an issue first.', 'No Selection',
                MessageBoxButtons.OK,
                MessageBoxIcon.Warning)

    # =========================================================================
    def __on_back(self, sender, event):
        self.DialogResult = DialogResult.Retry  # BACK
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
        ref = self.__get_selected_ref()
        if ref:
            self.__selected_ref = ref
            self.DialogResult = DialogResult.OK
            self.Close()

    # =========================================================================
    def __on_dgv_key_down(self, sender, event):
        if event.KeyCode == Keys.Enter:
            self.__on_ok(sender, event)
            event.Handled = True

    # =========================================================================
    def show_form(self):
        dialog_result = self.ShowDialog()
        return IssueFormResult(dialog_result, self.__selected_ref)
