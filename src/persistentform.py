''' ===========================================================================

This module defines PersistentForm, a WinForms Form subclass that
saves and restores its window position (and optionally size) between runs.

Follows the same approach as the Comic Vine Scraper's PersistentForm:
StartPosition is Manual, the form centres itself on its parent in the Load
handler unless a saved location exists, and geometry is only written back
if the user actually moved/resized the window after it appeared.

License: Apache 2.0

=========================================================================== '''
import clr
import log
from utils import load_map, persist_map

clr.AddReference('System.Windows.Forms')
from System.Windows.Forms import Form, FormStartPosition, Screen

clr.AddReference('System.Drawing')
from System.Drawing import Point, Size, Rectangle

from resources import Resources

# Prefix applied to every geometry key. Earlier builds saved a location for
# every dialog the first time it opened (even if the user never moved it),
# and saved sizes that didn't fit the content. Changing the prefix makes
# those stale entries in geometry.dat get ignored.
GEOMETRY_KEY_PREFIX = 'v2.'


# ===========================================================================
class PersistentForm(Form):
    '''
    A Form subclass that saves/restores its window location (and optionally
    size) to the geometry.dat settings file.

    persist_loc_key_s  -- key for the window position, or None to always
                          centre on the parent
    persist_size_key_s -- key for the window size, or None to keep the
                          form's natural size (use None for fixed-size forms)
    parent             -- the owning window; the form is centred on it
    '''

    def __init__(self, persist_loc_key_s=None, persist_size_key_s=None,
                 parent=None):
        self.__loc_key_s = (GEOMETRY_KEY_PREFIX + persist_loc_key_s) \
            if persist_loc_key_s else None
        self.__size_key_s = (GEOMETRY_KEY_PREFIX + persist_size_key_s) \
            if persist_size_key_s else None

        # True once the user has moved/resized the window after it appeared
        self.__bounds_changed = False

        # We position the window ourselves in the Load handler.
        self.StartPosition = FormStartPosition.Manual
        if parent:
            self.Owner = parent

        self.Load += self.__on_load
        self.Move += self.__on_bounds_changed
        self.Resize += self.__on_bounds_changed
        self.FormClosing += self.__on_closing

    # =========================================================================
    def __on_load(self, sender, event):
        '''Restores saved geometry, or centres on the parent.'''
        del sender, event
        centred = False
        try:
            prefs = load_map(Resources.GEOMETRY_FILE) \
                if (self.__loc_key_s or self.__size_key_s) else {}

            if self.__size_key_s and self.__size_key_s in prefs:
                w, h = [int(v) for v in str(prefs[self.__size_key_s]).split(',')]
                if w > 100 and h > 50:
                    self.Size = Size(w, h)

            if self.__loc_key_s and self.__loc_key_s in prefs:
                x, y = [int(v) for v in str(prefs[self.__loc_key_s]).split(',')]
                self.Location = Point(x, y)
            else:
                self.__centre()
                centred = True
        except:
            log.debug_exc('could not restore window geometry')
            if not centred:
                self.__centre()

        # If the window's centre is off every screen (e.g. a monitor was
        # unplugged since it was saved), bring it back.
        try:
            b = self.Bounds
            centre = Point(b.X + b.Width / 2, b.Y + b.Height / 2)
            screens = Screen.AllScreens
            all_bounds = screens[0].Bounds
            for s in screens:
                all_bounds = Rectangle.Union(all_bounds, s.Bounds)
            if not all_bounds.Contains(centre):
                self.CenterToScreen()
        except:
            pass

        # Anything that moved/resized the window up to now was us, not the
        # user, so don't treat it as a change worth saving.
        self.__bounds_changed = False

    # =========================================================================
    def __centre(self):
        '''Centres on the owning window if there is one, else the screen.'''
        if self.Owner is not None:
            self.CenterToParent()
        else:
            self.CenterToScreen()

    # =========================================================================
    def __on_bounds_changed(self, sender, event):
        del sender, event
        self.__bounds_changed = True

    # =========================================================================
    def __on_closing(self, sender, event):
        '''Saves geometry if the user moved/resized the window.'''
        del sender, event
        if not self.__bounds_changed:
            return
        if not (self.__loc_key_s or self.__size_key_s):
            return
        try:
            prefs = load_map(Resources.GEOMETRY_FILE)
            if self.__loc_key_s:
                prefs[self.__loc_key_s] = '%d,%d' % \
                    (self.Location.X, self.Location.Y)
            if self.__size_key_s:
                prefs[self.__size_key_s] = '%d,%d' % (self.Width, self.Height)
            persist_map(Resources.GEOMETRY_FILE, prefs)
        except:
            log.debug_exc('could not save window geometry')
