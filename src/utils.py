''' ===========================================================================

This module contains utility functions used throughout the Tebeosfera Scraper.

License: Apache 2.0

=========================================================================== '''
import re
import clr
import sys

clr.AddReference('System')
from System.IO import Path as SysPath

clr.AddReference('System.Windows.Forms')
from System.Windows.Forms import Control, MethodInvoker

try:
    clr.AddReference('System.Web')
    from System.Net import WebUtility
except:
    WebUtility = None


# ===========================================================================
def sstr(obj):
    '''
    Converts the given object to a string in a maximally safe way.
    None becomes '<None>', strings are returned as-is (to avoid a unicode
    str() bug in IronPython), and everything else is str()'d.
    '''
    if obj is None:
        return '<None>'
    if is_string(obj):
        return obj
    return str(obj)


# ===========================================================================
def is_string(obj):
    '''Returns True iff the given object is a string (str or unicode).'''
    return isinstance(obj, str) or isinstance(obj, unicode)


# ===========================================================================
def is_blank(val):
    '''
    Returns True if the given value is "blank": None, empty string, empty
    list, -1 (the sentinel for unknown dates/counts), or whitespace-only.
    '''
    if val is None:
        return True
    if isinstance(val, (list, tuple, set, frozenset)):
        return len(val) == 0
    if isinstance(val, int):
        return val == -1
    if isinstance(val, float):
        return val < 0
    if is_string(val):
        return val.strip() == ''
    return False


# ===========================================================================
def is_number(obj):
    '''Returns True iff the given object is a number (int or float).'''
    return isinstance(obj, (int, long, float))


# ===========================================================================
def invoke(control, delegate, synchronous=True):
    '''
    Executes the given no-argument delegate method on the thread that owns
    the given WinForms control. If 'synchronous' is True, this method blocks
    until the delegate finishes executing; otherwise it returns immediately.
    '''
    if control is None or control.IsDisposed:
        return
    try:
        # Control.Invoke/BeginInvoke take the abstract System.Delegate type,
        # so IronPython can't convert a Python function automatically; it
        # must be wrapped in a concrete delegate type first.
        if synchronous:
            if control.InvokeRequired:
                control.Invoke(MethodInvoker(delegate))
            else:
                delegate()
        else:
            control.BeginInvoke(MethodInvoker(delegate))
    except SystemError:
        # "Invoke or BeginInvoke cannot be called on a control until the
        # window handle has been created" (or it was just disposed).
        # Same handling as the Comic Vine Scraper.
        pass


# ===========================================================================
def natural_key(s):
    '''
    Returns a key that can be used to sort strings in "natural" order, where
    numeric runs within the string are compared numerically (so "issue 2"
    comes before "issue 10").
    '''
    def convert(text):
        return int(text) if text.isdigit() else text.lower()
    return [convert(c) for c in re.split(r'(\d+)', sstr(s))]


# ===========================================================================
def natural_compare(a, b):
    '''
    Compares two strings in natural order. Returns -1, 0, or 1.
    '''
    ka, kb = natural_key(a), natural_key(b)
    for i in range(min(len(ka), len(kb))):
        ca, cb = ka[i], kb[i]
        if type(ca) != type(cb):
            # one is int, other is str; ints sort before strings
            if isinstance(ca, int):
                return -1
            return 1
        if ca < cb:
            return -1
        if ca > cb:
            return 1
    return cmp(len(ka), len(kb))


# ===========================================================================
def load_map(filepath):
    '''
    Reads a settings file as a map of key:value pairs. The file format is
    one 'key : value' per line, UTF-8 encoded. Boolean values are stored as
    'True'/'False', numbers as their string representation.
    Returns a dict with auto-converted types.
    '''
    result = {}
    try:
        clr.AddReference('System')
        from System.IO import File
        if File.Exists(filepath):
            lines = File.ReadAllLines(filepath)
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if ' : ' in line:
                    parts = line.split(' : ', 1)
                    key = parts[0].strip()
                    val = parts[1].strip() if len(parts) > 1 else ''
                    result[key] = __auto_convert(val)
                elif ':' in line:
                    parts = line.split(':', 1)
                    key = parts[0].strip()
                    val = parts[1].strip() if len(parts) > 1 else ''
                    result[key] = __auto_convert(val)
    except:
        pass
    return result


# ===========================================================================
def persist_map(filepath, data):
    '''
    Writes a map (dict) of key:value pairs to the given file in the same
    format that load_map reads.
    '''
    try:
        from System.IO import Directory, StreamWriter
        dir_path = SysPath.GetDirectoryName(filepath)
        if dir_path and not Directory.Exists(dir_path):
            Directory.CreateDirectory(dir_path)
        writer = StreamWriter(filepath, False)  # False = overwrite
        try:
            for key in sorted(data.keys()):
                val = data[key]
                if val is None:
                    val = ''
                writer.WriteLine('%s : %s' % (key, val))
        finally:
            writer.Close()
    except:
        pass


# ===========================================================================
def load_string(filepath):
    '''Reads an entire file as a single string. Returns '' if file is missing.'''
    try:
        from System.IO import File
        if File.Exists(filepath):
            return File.ReadAllText(filepath)
    except:
        pass
    return ''


# ===========================================================================
def persist_string(filepath, text):
    '''Writes a string to a file, overwriting any existing content.'''
    try:
        from System.IO import File, Directory
        dir_path = SysPath.GetDirectoryName(filepath)
        if dir_path and not Directory.Exists(dir_path):
            Directory.CreateDirectory(dir_path)
        File.WriteAllText(filepath, text)
    except:
        pass


# ===========================================================================
def html_decode(text):
    '''
    Decodes HTML entities in the given text. Uses .NET's WebUtility if
    available, falls back to a manual decoder.
    '''
    if not text:
        return ''
    if WebUtility:
        return WebUtility.HtmlDecode(text)
    # Manual fallback
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#039;', "'")
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&aacute;', 'a')
    text = text.replace('&eacute;', 'e')
    text = text.replace('&iacute;', 'i')
    text = text.replace('&oacute;', 'o')
    text = text.replace('&uacute;', 'u')
    text = text.replace('&ntilde;', 'n')
    return text


# ===========================================================================
def strip_tags(html):
    '''Removes all HTML tags from the given text, returning plain text.'''
    if not html:
        return ''
    return re.sub(r'<[^>]+>', '', html).strip()


# ===========================================================================
def strip_accents(text):
    '''
    Removes accented characters from text, converting them to their
    plain ASCII equivalents. Useful for accent-insensitive matching.
    '''
    if not text:
        return ''
    replacements = {
        u'\u00e1': 'a', u'\u00e9': 'e', u'\u00ed': 'i', u'\u00f3': 'o',
        u'\u00fa': 'u', u'\u00f1': 'n',
        u'\u00c1': 'A', u'\u00c9': 'E', u'\u00cd': 'I', u'\u00d3': 'O',
        u'\u00da': 'U', u'\u00d1': 'N',
        u'\u00e0': 'a', u'\u00e8': 'e', u'\u00ec': 'i', u'\u00f2': 'o',
        u'\u00f9': 'u',
        u'\u00c0': 'A', u'\u00c8': 'E', u'\u00cc': 'I', u'\u00d2': 'O',
        u'\u00d9': 'U',
        u'\u00e4': 'a', u'\u00eb': 'e', u'\u00ef': 'i', u'\u00f6': 'o',
        u'\u00fc': 'u',
        u'\u00c4': 'A', u'\u00cb': 'E', u'\u00cf': 'I', u'\u00d6': 'O',
        u'\u00dc': 'U',
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text


# ===========================================================================
def parse_date(date_str):
    '''
    Parses a tebeosfera date string like "12-V-1986" or "26-II-2017"
    and returns (day, month, year) as integers, or (-1, -1, year) if
    only the year can be determined.
    '''
    if not date_str:
        return -1, -1, -1
    roman_map = {
        'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6,
        'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10, 'XI': 11, 'XII': 12,
    }
    parts = re.split(r'[-/]', date_str.strip())
    day, month, year = -1, -1, -1
    try:
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if part.isdigit() and len(part) >= 4:
                year = int(part)
            elif part.isdigit():
                num = int(part)
                if num > 31:
                    year = num
                elif num > 12 or (month != -1 and day == -1):
                    day = num
                else:
                    if month == -1:
                        day = num
                    else:
                        month = num
            elif part.upper() in roman_map:
                month = roman_map[part.upper()]
    except:
        pass
    # If we only found a year, that's fine
    if year == -1 and len(parts) == 1:
        try:
            year = int(parts[0].strip())
        except:
            pass
    return day, month, year


# ===========================================================================
def clamp(val, min_val, max_val):
    '''Clamps a numeric value to the given range.'''
    if val < min_val:
        return min_val
    if val > max_val:
        return max_val
    return val


# ===========================================================================
def __auto_convert(val):
    '''Converts a string value to bool, int, float, or leaves as string.'''
    if not isinstance(val, str):
        return val
    val = val.strip()
    if val.lower() == 'true':
        return True
    if val.lower() == 'false':
        return False
    if val.lower() == 'none':
        return None
    try:
        return int(val)
    except:
        pass
    try:
        return float(val)
    except:
        pass
    return val


# ===========================================================================
# Words kept lower-case inside a title-cased string (Spanish articles,
# prepositions and conjunctions), unless they're the first word.
_SMALL_WORDS = frozenset(
    'a al con de del e el en la las lo los o para por sin u un una unas unos y'
    .split())
# Roman numerals made of I/V/X only ("II", "XIV"), kept upper-case.
_ROMAN = re.compile(r'^(?=[IVX]{2,}$)X{0,3}(IX|IV|V?I{0,3})$')
# A letter at the start of a word or after punctuation ("l.", "d'", "x-")
_WORD_START = re.compile(r'(^|[^\w])(\w)', re.UNICODE)


def is_all_caps(text):
    '''True if text has letters and none of them are lower-case.'''
    letters = [c for c in (text or '') if c.isalpha()]
    return bool(letters) and not any(c.islower() for c in letters)


def smart_title(text):
    '''
    Converts ALL-CAPS text (as tebeosfera shows titles and names) to title
    case, Spanish style: "EL CAPITAN TRUENO" -> "El Capitan Trueno",
    "MARI CARMEN DE LA FUENTE" -> "Mari Carmen de la Fuente",
    "L. BERMEJO" -> "L. Bermejo", "TOMO II" -> "Tomo II".
    Text that already has lower-case letters is returned unchanged.
    '''
    if not is_all_caps(text):
        return text
    out = []
    for i, word in enumerate(text.split(' ')):
        bare = word.strip(u'.,;:()[]"\'!?\xa1\xbf')   # \xa1 = inverted !, \xbf = inverted ?
        if _ROMAN.match(bare):
            out.append(word)
        elif i > 0 and bare.lower() in _SMALL_WORDS:
            out.append(word.lower())
        else:
            out.append(_WORD_START.sub(
                lambda m: m.group(1) + m.group(2).upper(), word.lower()))
    return ' '.join(out)
