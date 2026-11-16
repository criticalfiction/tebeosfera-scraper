''' ===========================================================================

This module defines CVForm, the base class for all Tebeosfera Scraper
forms. It extends PersistentForm with common defaults and the context-
manager protocol used by the scrape engine.

License: Apache 2.0

=========================================================================== '''
import clr
import log

from persistentform import PersistentForm

clr.AddReference('System.Windows.Forms')
from System.Windows.Forms import Form, FormBorderStyle, AutoScaleMode, \
    Keys, MessageBox, MessageBoxButtons, MessageBoxIcon

clr.AddReference('System.Drawing')
from System.Drawing import SizeF


# ===========================================================================
class CVForm(PersistentForm):
    '''
    The base class for all scraper forms. Provides common window settings,
    a context-manager protocol (used as `with FormClass(...) as f:`), and
    global keyboard shortcuts.
    '''

    def __init__(self, parent=None, persist_loc_key_s=None,
                 persist_size_key_s=None):
        # All CVForms are fixed-size, so only the location is persisted;
        # persist_size_key_s is accepted for compatibility but ignored.
        del persist_size_key_s
        super(CVForm, self).__init__(persist_loc_key_s, None, parent)

        # Layouts are written in pixels at 96 DPI. ComicRack runs DPI-aware,
        # so tell WinForms to scale everything (positions, sizes and
        # ClientSize) to the current display, as the Bedetheque plugin does.
        self.AutoScaleDimensions = SizeF(96.0, 96.0)
        self.AutoScaleMode = AutoScaleMode.Dpi

        # Common defaults for all scraper forms
        self.FormBorderStyle = FormBorderStyle.FixedSingle
        self.MaximizeBox = False
        self.MinimizeBox = False
        self.ShowInTaskbar = False
        self.KeyPreview = True

    # =========================================================================
    def ShowDialog(self, owner=None):
        '''Overrides ShowDialog to default the owner to our parent.'''
        if owner is None:
            owner = self.Owner
        return super(CVForm, self).ShowDialog(owner)

    # =========================================================================
    def show_form(self):
        '''
        Shows this form as a modal dialog and returns a form-specific result.
        Subclasses must override this.
        '''
        raise NotImplementedError('show_form() must be implemented by subclass')

    # =========================================================================
    def ProcessCmdKey(self, msg, keyData):
        '''Handles global keyboard shortcuts.'''
        # Escape closes the form
        if keyData == Keys.Escape:
            self.Close()
            return True
        # Ctrl+Shift+L saves the log (for debugging)
        if keyData == (Keys.Control | Keys.Shift | Keys.L):
            try:
                cache_dir = getattr(Resources, 'LOCAL_CACHE_DIRECTORY', '')
                MessageBox.Show(self, 'Debug log available in:\n' +
                               str(cache_dir),
                               'Log Location',
                               MessageBoxButtons.OK, MessageBoxIcon.Information)
            except:
                pass
            return True
        return super(CVForm, self).ProcessCmdKey(msg, keyData)

    # =========================================================================
    # Context manager protocol (used as: with SeriesForm(...) as f: result = f.show_form())
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.Close()
            self.Dispose()
        except:
            pass
        return False  # don't suppress exceptions


# ===========================================================================
# Allow access to Resources in the module scope (used by ProcessCmdKey)
from resources import Resources
