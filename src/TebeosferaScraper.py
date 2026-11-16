''' ===========================================================================

This module is the entry point into the 'Tebeosfera Scraper' add-on for
ComicRack. It conforms to ComicRack add-on specifications.

The plugin scrapes comic book metadata from tebeosfera.com, the Spanish
comic encyclopedia. It does not use an API; instead it scrapes HTML pages
directly, following patterns from the Bedetheque scraper.

License: Apache 2.0

=========================================================================== '''
#@Name  Tebeosfera Scraper
#@Key   tebeosfera-scraper
#@Hook  Books, Editor
#@Image tebeosfera.png
#@Description Scrapes comic book info from Tebeosfera.com.

import re
import clr
import log
from scrapeengine import ScrapeEngine
from configform import ConfigForm
from resources import Resources
from utils import sstr

clr.AddReference('System')
from System.Threading import ThreadExceptionEventHandler

clr.AddReference('System.Windows.Forms')
from System.Windows.Forms import Application, MessageBox, \
    MessageBoxButtons, MessageBoxIcon

# Suppress the undefined ComicRack variable warning
if False and True:
    ComicRack = None


# ============================================================================
#@Key   tebeosfera-scraper
#@Hook  Books, Editor
#@Image tebeosfera.png
# ============================================================================
def tbf_scrape(books):
    '''Scrapes metadata from tebeosfera.com for the given ComicRack books.'''
    def delegate():
        if books:
            engine = ScrapeEngine(ComicRack)
            engine.scrape(books)
    __launch(delegate)


# ============================================================================
#@Key   tebeosfera-scraper
#@Hook  ConfigScript
# ============================================================================
def tbf_config():
    '''Opens the configuration dialog for the Tebeosfera Scraper.'''
    def delegate():
        with ConfigForm(ComicRack.MainWindow) as config_form:
            config_form.show_form()  # blocks
    __launch(delegate)


# =============================================================================
def __launch(delegate):
    '''
    Runs the given (no-argument) delegate method in a 'safe' script environment.
    '''
    try:
        Resources.initialize()
        log.install(ComicRack.MainWindow)

        def exception_handler(sender, event):
            del sender
            log.handle_error(event.Exception)

        Application.ThreadException += \
            ThreadExceptionEventHandler(exception_handler)

        if __validate_environment():
            delegate()

    except Exception, ex:
        log.handle_error(ex)

    finally:
        try:
            Application.ThreadException -= \
                ThreadExceptionEventHandler(exception_handler)
        except:
            pass
        log.uninstall()


# =============================================================================
def __validate_environment():
    '''
    Checks if the current ComicRack environment is valid for this script.
    Returns True if valid, False otherwise.
    '''
    REQUIRED_MAJOR = 0
    REQUIRED_MINOR = 9
    REQUIRED_BUILD = 0

    valid = True
    try:
        version = re.split(r'\.', ComicRack.App.ProductVersion)

        def vhash(major, minor, build):
            return float(sstr(major * 5000 + minor) + '.' + sstr(build))

        valid = vhash(int(version[0]), int(version[1]), int(version[2])) >= \
            vhash(REQUIRED_MAJOR, REQUIRED_MINOR, REQUIRED_BUILD)

        if not valid:
            MessageBox.Show(ComicRack.MainWindow,
                'Tebeosfera Scraper requires ComicRack %d.%d.%d or higher.' % \
                    (REQUIRED_MAJOR, REQUIRED_MINOR, REQUIRED_BUILD),
                'ComicRack Too Old',
                MessageBoxButtons.OK, MessageBoxIcon.Warning)

    except Exception:
        log.debug('Could not validate ComicRack version')
        valid = True

    return valid
