''' ===========================================================================

This module contains the Resources class, which provides static access to
path constants and resource locations for the Tebeosfera Scraper.

License: Apache 2.0

=========================================================================== '''
import sys
import clr

clr.AddReference('System')
from System import Environment
from System.IO import Directory, File, Path as SysPath

# ===========================================================================
class Resources(object):
    '''
    This class provides static access to "constants" for all the non-code
    resources that this app uses (i.e. pathnames and locations, mostly).
    '''

    # The location of our scraper 'cache' files.
    LOCAL_CACHE_DIRECTORY = None

    # The location of the app's settings file.
    SETTINGS_FILE = None

    # The location of the app's advanced settings file.
    ADVANCED_FILE = None

    # The location of the app's geometry settings file.
    GEOMETRY_FILE = None

    # The app's version number/string
    SCRIPT_VERSION = "!DEV!"
    if SCRIPT_VERSION.startswith("!"):
        SCRIPT_VERSION = "0.0.0"

    # The full name of the app, including version string
    SCRIPT_FULLNAME = 'Tebeosfera Scraper - v' + SCRIPT_VERSION

    # The base URL for tebeosfera.com
    BASE_URL = 'https://www.tebeosfera.com'

    # The user agent string used for HTTP requests
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

    # =========================================================================
    @classmethod
    def initialize(cls):
        '''
        Initialize the Resources class. This method MUST be called exactly
        once before you try to make use of this class in any other way.
        '''
        try:
            cls.__initialize()
        except:
            print sys.exc_info()[1]
            sys.exit()

    # =========================================================================
    @classmethod
    def __initialize(cls):
        # Get the basic locations that the other locations build on
        script_dir = Directory.GetParent(__file__).FullName

        # The profile directory is in AppData
        profile_dir = Environment.GetFolderPath(
            Environment.SpecialFolder.ApplicationData) + \
            r"\Tebeosfera Scraper"

        # Set the standard locations for settings files
        cls.SETTINGS_FILE = profile_dir + r'\settings.dat'
        cls.ADVANCED_FILE = profile_dir + r'\advanced.dat'
        cls.GEOMETRY_FILE = profile_dir + r'\geometry.dat'
        cls.LOCAL_CACHE_DIRECTORY = profile_dir + r'\localCache'

        # Ensure profile directory exists
        if not File.Exists(profile_dir):
            Directory.CreateDirectory(profile_dir)
        if not File.Exists(cls.LOCAL_CACHE_DIRECTORY):
            Directory.CreateDirectory(cls.LOCAL_CACHE_DIRECTORY)
