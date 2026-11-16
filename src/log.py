''' ===========================================================================

This module provides simple debug logging for the Tebeosfera Scraper.

License: Apache 2.0

=========================================================================== '''
import sys
import clr

clr.AddReference('System.Windows.Forms')
from System.Windows.Forms import MessageBox, MessageBoxButtons, MessageBoxIcon

clr.AddReference('System')
from System import DateTime
from System.IO import Path as SysPath

import utils
from utils import sstr

# ===========================================================================
# module-level globals
__writer = None
__logfile = None
__indent = 0


# ===========================================================================
def install(main_window):
    '''
    Initializes the logging system. Creates a debug log file in the user's
    AppData directory and sets up a stream writer for it.
    '''
    global __writer, __logfile
    try:
        from resources import Resources
        log_dir = Resources.LOCAL_CACHE_DIRECTORY
        if not log_dir:
            return
        from System.IO import Directory
        if not Directory.Exists(log_dir):
            Directory.CreateDirectory(log_dir)
        __logfile = SysPath.Combine(log_dir, 'debug.log')
        __writer = open(__logfile, 'a')
    except:
        pass


# ===========================================================================
def uninstall():
    '''Shuts down the logging system, closing the log file.'''
    global __writer
    try:
        if __writer:
            __writer.close()
            __writer = None
    except:
        pass


# ===========================================================================
def debug(*args):
    '''Writes a debug message to the log file.'''
    global __writer, __indent
    if not __writer:
        return
    try:
        prefix = '   ' * __indent
        msg = prefix + ' '.join(sstr(a) for a in args)
        timestamp = DateTime.Now.ToString('yyyy-MM-dd HH:mm:ss')
        __writer.write('[%s] %s\n' % (timestamp, msg))
        __writer.flush()
    except:
        pass


# ===========================================================================
def debug_exc(msg=''):
    '''Logs an exception with the given message prefix.'''
    global __writer
    if not __writer:
        return
    try:
        exc = sys.exc_info()[1]
        if exc:
            debug('%s: %s' % (msg, sstr(exc)))
        else:
            debug(msg)
    except:
        pass


# ===========================================================================
def handle_error(exception):
    '''
    Displays an error message to the user and logs it. This is the main
    error-handling entry point for uncaught exceptions.
    '''
    try:
        debug('ERROR: %s' % sstr(exception))
        debug_exc('Exception details')
        MessageBox.Show(
            'An error occurred while running Tebeosfera Scraper:\n\n%s' % \
                sstr(exception),
            'Tebeosfera Scraper Error',
            MessageBoxButtons.OK,
            MessageBoxIcon.Error)
    except:
        pass


# ===========================================================================
def push_indent():
    '''Increases the debug log indentation by one level.'''
    global __indent
    __indent += 1


# ===========================================================================
def pop_indent():
    '''Decreases the debug log indentation by one level.'''
    global __indent
    if __indent > 0:
        __indent -= 1
