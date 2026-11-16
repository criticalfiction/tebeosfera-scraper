''' ===========================================================================

This module defines SearchForm, the dialog where the user enters search
terms to find a series on tebeosfera.com.

License: Apache 2.0

=========================================================================== '''
import clr
import log
from cvform import CVForm

clr.AddReference('System.Windows.Forms')
from System.Windows.Forms import TextBox, Button, Label, DialogResult, \
    Keys, Control

clr.AddReference('System.Drawing')
from System.Drawing import Point, Size, Font, FontStyle, ContentAlignment, \
    Color, FontFamily


# ===========================================================================
class SearchFormResult(object):
    '''
    The result of the SearchForm dialog. Contains an id string
    ('SEARCH'|'CANCEL'|'SKIP'|'PERMSKIP') and, for SEARCH, the search terms.
    '''

    def __init__(self, dialog_result, search_terms_s=''):
        self.__id = ''
        self.__search_terms_s = search_terms_s or ''

        if dialog_result == DialogResult.OK:
            self.__id = 'SEARCH'
        elif dialog_result == DialogResult.Cancel:
            self.__id = 'CANCEL'
        elif dialog_result == DialogResult.Ignore:
            self.__id = 'SKIP'
        elif dialog_result == DialogResult.Abort:
            self.__id = 'PERMSKIP'
        else:
            self.__id = 'CANCEL'

    def equals(self, id_s):
        return self.__id == id_s

    def get_search_terms_s(self):
        return self.__search_terms_s

    def get_debug_string(self):
        if self.__id == 'SEARCH':
            return 'search for: %s' % self.__search_terms_s
        return self.__id.lower()


# ===========================================================================
class SearchForm(CVForm):
    '''
    A dialog that lets the user enter search terms for finding a series.
    '''

    def __init__(self, parent, default_search_terms, failed_search_terms=None):
        super(SearchForm, self).__init__(parent, 'searchform_loc', 'searchform_sz')
        self.Text = 'Search Tebeosfera'

        self.__search_terms_s = default_search_terms or ''
        self.__failed_search_s = failed_search_terms or ''
        self.__result = None
        self.__text_box = None

        self.__build_ui()

    # =========================================================================
    def __build_ui(self):
        '''Builds the form's UI controls.'''

        # Failed search label (if any)
        y = 10
        if self.__failed_search_s:
            label = Label()
            label.Text = 'No results found for "%s". Try different search terms:' % \
                self.__failed_search_s
            label.Location = Point(10, y)
            label.Size = Size(420, 30)
            label.ForeColor = Color.Red
            self.Controls.Add(label)
            y = 45

        # Search label
        search_label = Label()
        search_label.Text = 'Enter series name to search on Tebeosfera:'
        search_label.Location = Point(10, y)
        search_label.Size = Size(420, 20)
        self.Controls.Add(search_label)
        y += 25

        # Search text box
        self.__text_box = TextBox()
        self.__text_box.Location = Point(10, y)
        self.__text_box.Size = Size(420, 25)
        self.__text_box.Text = self.__search_terms_s
        self.__text_box.KeyPress += self.__on_key_press
        self.Controls.Add(self.__text_box)
        y += 35

        # Buttons
        btn_y = y

        search_btn = Button()
        search_btn.Text = 'Search'
        search_btn.Location = Point(10, btn_y)
        search_btn.Size = Size(100, 30)
        search_btn.Click += self.__on_search
        self.Controls.Add(search_btn)

        skip_btn = Button()
        skip_btn.Text = 'Skip'
        skip_btn.Location = Point(120, btn_y)
        skip_btn.Size = Size(100, 30)
        skip_btn.Click += self.__on_skip
        self.Controls.Add(skip_btn)

        cancel_btn = Button()
        cancel_btn.Text = 'Cancel'
        cancel_btn.Location = Point(230, btn_y)
        cancel_btn.Size = Size(100, 30)
        cancel_btn.Click += self.__on_cancel
        self.Controls.Add(cancel_btn)

        # Size the inner area to the content (height varies with whether the
        # "no results" message is shown).
        self.ClientSize = Size(440, btn_y + 30 + 10)

        # Make the search button the default
        self.AcceptButton = search_btn

        # Focus the text box and select all text
        self.__text_box.Focus()
        self.__text_box.SelectAll()

    # =========================================================================
    def __on_key_press(self, sender, event):
        '''Handles Enter key in the text box to trigger search.'''
        if event.KeyChar == '\r':
            self.DialogResult = DialogResult.OK
            self.__search_terms_s = self.__text_box.Text.strip()
            self.Close()
            event.Handled = True

    # =========================================================================
    def __on_search(self, sender, event):
        '''Handles the Search button click.'''
        self.__search_terms_s = self.__text_box.Text.strip()
        self.DialogResult = DialogResult.OK
        self.Close()

    # =========================================================================
    def __on_skip(self, sender, event):
        '''Handles the Skip button click.'''
        # Check if Ctrl is held for permanent skip
        if Control.ModifierKeys == Keys.Control:
            self.DialogResult = DialogResult.Abort  # PERMSKIP
        else:
            self.DialogResult = DialogResult.Ignore  # SKIP
        self.Close()

    # =========================================================================
    def __on_cancel(self, sender, event):
        '''Handles the Cancel button click.'''
        self.DialogResult = DialogResult.Cancel
        self.Close()

    # =========================================================================
    def show_form(self):
        '''Shows the form and returns a SearchFormResult.'''
        dialog_result = self.ShowDialog()
        result = SearchFormResult(dialog_result, self.__search_terms_s)
        return result
