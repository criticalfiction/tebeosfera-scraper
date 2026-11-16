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
    CheckState, DockStyle, ScrollBars, Keys

clr.AddReference('System.Drawing')
from System.Drawing import Size, Point, Font, FontStyle, FontFamily


# ===========================================================================
class ConfigForm(CVForm):
    '''
    A tabbed configuration dialog for the Tebeosfera Scraper.
    '''

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
        self.__add_checkboxes(tab_behavior, behavior_items)
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
        self.__add_checkboxes(tab_credits, credits_items, top=48)
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
        '''Adds one checkbox per (setting, label) to the tab, 24px apart.'''
        for i, (key, label) in enumerate(items):
            cb = CheckBox()
            cb.Text = label
            cb.Location = Point(10, top + i * 24)
            cb.Size = Size(480, 23)
            cb.Checked = getattr(self.__config, key, False)
            self.__behavior_checks[key] = cb   # all saved by __on_ok
            tab.Controls.Add(cb)

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
