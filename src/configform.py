''' ===========================================================================

This module defines ConfigForm, the settings dialog for the Tebeosfera
Scraper. It uses a tabbed layout with sections for metadata field selection,
behavior options, and advanced settings.

License: Apache 2.0

=========================================================================== '''
import clr
import log
import utils
from cvform import CVForm
from configuration import Configuration

clr.AddReference('System.Windows.Forms')
from System.Windows.Forms import TabControl, TabPage, CheckedListBox, \
    CheckBox, TextBox, Label, Button, DialogResult, GroupBox, \
    CheckState, DockStyle, ScrollBars, Keys, ComboBox, ComboBoxStyle

from System.Windows.Forms import TextRenderer, TextFormatFlags

clr.AddReference('System.Drawing')
from System.Drawing import Size, Point, Font, FontStyle, FontFamily, \
    Rectangle, ContentAlignment


# ===========================================================================
# Text that fits at 96 DPI can need more room on other displays: if the font
# is scaled for the display but the layout isn't (or less), a fixed-size
# label hides its last line and a checkbox cuts off the end of its text.
# The Behavior and Credits tabs are laid out by stack_layout instead, which
# gives each label and checkbox the height its wrapped text needs.
def _text_height(control, width):
    '''The height control needs to show all its text, wrapped at width.'''
    if isinstance(control, Label):
        return control.GetPreferredSize(Size(width, 0)).Height
    if isinstance(control, CheckBox):
        one_line = control.GetPreferredSize(Size.Empty)
        text = TextRenderer.MeasureText(control.Text, control.Font)
        box = one_line.Width - text.Width        # the tick box and spacing
        wrapped = TextRenderer.MeasureText(control.Text, control.Font,
                                           Size(width - box, 0),
                                           TextFormatFlags.WordBreak)
        # at least a normal checkbox row (23 px at 96 DPI for an 8pt font)
        return max(control.Font.Height + 10,
                   wrapped.Height + one_line.Height - text.Height)
    return control.Height
def stack_layout(page, items):
    '''
    Places items, a list of (control, space above it at 96 DPI), one under
    another down the page, each as wide as the page allows (keeping its
    left margin; a ComboBox keeps its own width) and, for labels and
    checkboxes, as tall as its text needs. Re-done whenever the page lays
    out, so a font or DPI change is followed.
    '''
    busy = []
    def layout(sender, event):
        if busy:
            return                  # moving controls lays the page out again
        busy.append(True)
        try:
            scale = page.Font.Height / 13.0     # 13 px: 8pt font at 96 DPI
            y = 0
            for control, space in items:
                y += int(round(space * scale))
                x = control.Left
                width = control.Width if isinstance(control, ComboBox) \
                    else page.ClientSize.Width - 2 * x
                if width <= 0:
                    return
                height = _text_height(control, width)
                if isinstance(control, CheckBox):
                    wraps = height > control.Font.Height + 10
                    control.CheckAlign = ContentAlignment.TopLeft if wraps \
                        else ContentAlignment.MiddleLeft
                    control.TextAlign = control.CheckAlign
                if control.Bounds != Rectangle(x, y, width, height):
                    control.SetBounds(x, y, width, height)
                y += height
        finally:
            del busy[:]
    page.Layout += layout


# ===========================================================================
class ConfigForm(CVForm):
    '''
    A tabbed configuration dialog for the Tebeosfera Scraper.
    '''

    # In the order of the credit_name_style_n setting
    NAME_STYLES = ['Signature', 'Real name', 'Signature (Real name)',
                   'Real name (Signature)', 'Signature (Real name) [Smart]',
                   'Real name (Signature) [Smart]']

    def __init__(self, parent=None):
        super(ConfigForm, self).__init__(parent, 'configform_loc', 'configform_sz')
        self.Text = 'Tebeosfera Scraper Configuration'
        # Inner area: tabs span y 5-400, buttons y 405-435, x up to 510.
        self.ClientSize = Size(515, 445)
        self.__config = Configuration()
        self.__tabs = None
        self.__field_checks = {}
        self.__behavior_checks = {}

        self.__build_ui()

    # =========================================================================
    def __build_ui(self):
        '''Builds the form's UI.'''

        # Tab control
        self.__tabs = TabControl()
        self.__tabs.Location = Point(5, 5)
        self.__tabs.Size = Size(505, 395)
        self.__tabs.SelectedIndex = 0

        # --- Tab 1: Metadata Fields ---
        tab_fields = TabPage()
        tab_fields.Text = 'Fields'

        fields_label = Label()
        fields_label.Text = 'Select which metadata fields to scrape:'
        fields_label.Location = Point(10, 5)
        fields_label.Size = Size(480, 20)
        tab_fields.Controls.Add(fields_label)

        field_list = [
            ('update_series_b', 'Series'),
            ('update_number_b', 'Number'),
            ('update_title_b', 'Title'),
            ('update_writer_b', 'Writer'),
            ('update_penciller_b', 'Penciller'),
            ('update_inker_b', 'Inker'),
            ('update_colorist_b', 'Colorist'),
            ('update_letterer_b', 'Letterer'),
            ('update_cover_artist_b', 'Cover Artist'),
            ('update_editor_b', 'Editor'),
            ('update_translator_b', 'Translator'),
            ('update_publisher_b', 'Publisher'),
            ('update_pub_date_b', 'Publication Date'),
            ('update_page_count_b', 'Page Count'),
            ('update_format_b', 'Format'),
            ('update_summary_b', 'Summary'),
            ('update_webpage_b', 'Web Page'),
            ('update_genre_b', 'Genre'),
            ('update_characters_b', 'Characters'),
            ('update_issn_b', 'ISSN'),
            ('update_cover_b', 'Cover Image'),
            ('update_black_and_white_b', 'Black and White'),
        ]

        check_list = CheckedListBox()
        check_list.Location = Point(10, 30)
        check_list.Size = Size(480, 200)
        for i, (key, label) in enumerate(field_list):
            checked = getattr(self.__config, key, False)
            idx = check_list.Items.Add(label)
            check_list.SetItemCheckState(idx,
                CheckState.Checked if checked else CheckState.Unchecked)
            self.__field_checks[key] = label

        check_list.ItemCheck += self.__on_field_check
        tab_fields.Controls.Add(check_list)
        self.__check_list = check_list  # keep reference for OK handler

        self.__tabs.Controls.Add(tab_fields)

        # --- Tab 2: Behavior ---
        tab_behavior = TabPage()
        tab_behavior.Text = 'Behavior'

        behavior_items = [
            ('ow_existing_b', 'Overwrite existing data'),
            ('ignore_blanks_b', 'Don\'t overwrite non-blank with blank'),
            ('autochoose_series_b', 'Auto-choose series (no dialog)'),
            ('confirm_issue_b', 'Confirm issue selection'),
            ('fast_rescrape_b', 'Fast rescrape of previously scraped books'),
            ('rescrape_notes_b', 'Write scrape notes'),
            ('rescrape_tags_b', 'Write rescrape tags'),
            ('summary_dialog_b', 'Show summary dialog after scraping'),
            ('welcome_dialog_b', 'Show welcome dialog before scraping'),
            ('title_only_if_different_b',
             'Only set Title if it differs from the Series'),
            ('set_spanish_language_b', 'Set language to Spanish if the book has none'),
        ]
        boxes = self.__add_checkboxes(tab_behavior, behavior_items)
        stack_layout(tab_behavior, [(cb, 8 if i == 0 else 1)
                                    for i, cb in enumerate(boxes)])
        self.__tabs.Controls.Add(tab_behavior)

        # --- Tab 3: Credits ---
        tab_credits = TabPage()
        tab_credits.Text = 'Credits'

        credits_note = Label()
        credits_note.Text = ('A historietista (who does all the work) is always '
                             'credited as writer, penciller, inker, letterer and '
                             'colorist (colorist only for colour comics).')
        credits_note.Location = Point(10, 8)
        credits_note.Size = Size(480, 34)
        tab_credits.Controls.Add(credits_note)

        credits_items = [
            ('translators_as_writers_b',
             'List translators as writers, after the original writers'),
            ('copy_penciller_to_inker_b',
             'Use penciller as inker if no inker is credited'),
            ('copy_penciller_to_cover_artist_b',
             'Use penciller as cover artist if no cover artist is credited'),
            ('copy_penciller_to_colorist_b',
             'Use penciller as colorist if none is credited (colour comics only)'),
        ]
        boxes = self.__add_checkboxes(tab_credits, credits_items, top=48)
        # Some authors sign their work with a name other than their own
        style_label = Label()
        style_label.Text = ('Authors whose signature differs from their real '
                            'name are credited as:')
        style_label.Location = Point(10, 160)
        style_label.Size = Size(480, 20)
        tab_credits.Controls.Add(style_label)
        self.__style_label = style_label
        self.__name_style = ComboBox()
        self.__name_style.DropDownStyle = ComboBoxStyle.DropDownList
        self.__name_style.Location = Point(10, 183)
        self.__name_style.Size = Size(300, 24)
        for text in self.NAME_STYLES:
            self.__name_style.Items.Add(text)
        style = self.__config.credit_name_style_n
        self.__name_style.SelectedIndex = \
            style if 0 <= style < len(self.NAME_STYLES) else 0
        tab_credits.Controls.Add(self.__name_style)
        # Fixed positions above are the 96 DPI layout before the first
        # layout pass; from then on stack_layout places everything.
        stack_layout(tab_credits, [(credits_note, 8)] +
                     [(cb, 8 if i == 0 else 1) for i, cb in enumerate(boxes)] +
                     [(style_label, 16), (self.__name_style, 3)])
        self.__tabs.Controls.Add(tab_credits)

        # --- Tab 3: Advanced ---
        tab_advanced = TabPage()
        tab_advanced.Text = 'Advanced'

        adv_label = Label()
        adv_label.Text = 'Advanced settings (one KEY = VALUE per line):'
        adv_label.Location = Point(10, 5)
        adv_label.Size = Size(480, 20)
        tab_advanced.Controls.Add(adv_label)

        help_label = Label()
        help_label.Text = ('Supported keys:\n'
                          'IGNORE_PUBLISHER = name\n'
                          'PUBLISHER_ALIAS = old --> new\n'
                          'SCRAPE_DELAY = seconds\n'
                          'MAX_SEARCH_RESULTS = number')
        help_label.Location = Point(10, 60)
        help_label.Size = Size(480, 80)
        tab_advanced.Controls.Add(help_label)

        self.__adv_text = TextBox()
        self.__adv_text.Location = Point(10, 25)
        self.__adv_text.Size = Size(480, 30)
        self.__adv_text.Multiline = True
        self.__adv_text.ScrollBars = ScrollBars.Vertical
        self.__adv_text.Text = self.__config.advanced_settings_s
        self.__adv_text.Font = Font(FontFamily.GenericMonospace, 9)
        tab_advanced.Controls.Add(self.__adv_text)

        self.__tabs.Controls.Add(tab_advanced)

        self.Controls.Add(self.__tabs)

        # OK and Cancel buttons
        ok_btn = Button()
        ok_btn.Text = 'OK'
        ok_btn.Location = Point(320, 405)
        ok_btn.Size = Size(90, 30)
        ok_btn.Click += self.__on_ok
        self.Controls.Add(ok_btn)

        cancel_btn = Button()
        cancel_btn.Text = 'Cancel'
        cancel_btn.Location = Point(420, 405)
        cancel_btn.Size = Size(90, 30)
        cancel_btn.Click += self.__on_cancel
        self.Controls.Add(cancel_btn)

        self.AcceptButton = ok_btn

    # =========================================================================
    def __add_checkboxes(self, tab, items, top=8):
        '''
        Adds one checkbox per (setting, label) to the tab, 24px apart, and
        returns them.
        '''
        boxes = []
        for i, (key, label) in enumerate(items):
            cb = CheckBox()
            cb.Text = label
            cb.Location = Point(10, top + i * 24)
            cb.Size = Size(480, 23)
            cb.Checked = getattr(self.__config, key, False)
            self.__behavior_checks[key] = cb   # all saved by __on_ok
            tab.Controls.Add(cb)
            boxes.append(cb)
        return boxes

    # =========================================================================
    def __on_field_check(self, sender, event):
        '''Track field checkbox changes.'''
        pass  # Changes are read from the CheckedListBox on OK

    # =========================================================================
    def __on_ok(self, sender, event):
        '''Saves configuration and closes the dialog.'''
        # Read field checkboxes from the stored reference
        check_list = self.__check_list
        for i in range(check_list.Items.Count):
            label = check_list.Items[i]
            checked = check_list.GetItemCheckState(i) == CheckState.Checked
            for key, lbl in self.__field_checks.items():
                if lbl == label:
                    setattr(self.__config, key, checked)

        # Read behavior checkboxes
        for key, cb in self.__behavior_checks.items():
            setattr(self.__config, key, cb.Checked)

        self.__config.credit_name_style_n = self.__name_style.SelectedIndex
        # Read advanced settings
        self.__config.advanced_settings_s = self.__adv_text.Text
        self.__config.parse_advanced_settings()

        # Save
        self.__config.save_defaults()
        self.DialogResult = DialogResult.OK
        self.Close()

    # =========================================================================
    def __on_cancel(self, sender, event):
        self.DialogResult = DialogResult.Cancel
        self.Close()

    # =========================================================================
    def show_form(self):
        '''Shows the config dialog.'''
        return self.ShowDialog()
