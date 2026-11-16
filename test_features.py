# -*- coding: utf-8 -*-
'''Checks title-casing, credit fallbacks, Spanish language and B&W, using the
plugin's own code (CPython, .NET stubbed, live tebeosfera pages).'''
import sys, types
exec(open('test_live.py', encoding='utf-8').read().split('def show_search')[0])

fails = []
def check(label, got, want):
    ok = got == want
    print('%s %-48s %r' % ('ok  ' if ok else 'FAIL', label, got))
    if not ok:
        print('     expected %r' % (want,))
        fails.append(label)

utils = sys.modules['utils']
print('--- title case')
for raw, want in [('EL CAPITAN TRUENO', 'El Capitan Trueno'),
                  ('MARI CARMEN DE LA FUENTE', 'Mari Carmen de la Fuente'),
                  ('L. BERMEJO', 'L. Bermejo'), ('VÍCTOR MORA', 'Víctor Mora'),
                  ('TOMO II', 'Tomo II'), ('X-MEN', 'X-Men'),
                  ("D'ARTAGNAN Y LOS TRES", "D'Artagnan y los Tres"),
                  ('LIBRO / CARTONÉ', 'Libro / Cartoné'),
                  ('DuBouillon', 'DuBouillon'), ('Mari Carmen Otero', 'Mari Carmen Otero')]:
    check(raw, utils.smart_title(raw), want)

print('--- black and white rules')
bw = tbf._black_and_white
for field, text, want in [
        ('', 'Libro de 48 páginas en color, más guardas', False),
        ('', 'Cuadernos grapados con 28 páginas en blanco y negro, con la cubierta en color', True),
        ('', 'Libros con 96 páginas en blanco y negro (los veinte primeros fueron en color)', True),
        ('COLOR (portada) BLANCO Y NEGRO (interior)', '', True),
        ('COLOR (portada, interior)', '', False),
        ('BLANCO Y NEGRO', '', True),
        ('', 'Una historia de amor y aventuras.', None)]:
    check((field or text)[:48], bw(field, text), want)

print('--- live: Miedo (2003, Glenat)')
miedo = tbf.query_issue(tbf.IssueRef('1', 'miedo_2003_glenat',
                        url_s='https://www.tebeosfera.com/numeros/miedo_2003_glenat.html'))
check('series', miedo.series_name_s, 'Miedo')
check('title', miedo.title_s, 'Miedo')
check('format', miedo.format_s, 'Libro / Cartoné')
check('writers', miedo.writers_sl, ['Antonio Trashorras', 'David Muñoz'])
check('pencillers', miedo.pencillers_sl, ['Javi Rodríguez'])
check('black and white', miedo.black_and_white, False)

print('--- live: Capitan Trueno (1986) #10')
ct = tbf.query_issue(tbf.IssueRef('10', 'x', url_s=
     'https://www.tebeosfera.com/numeros/capitan_trueno_el_1986_bruguera_-nuevas_aventuras-_10.html'))
check('series', ct.series_name_s, 'El Capitan Trueno')
check('guionistas are writers', ct.writers_sl[-2:], ['Echevarria', 'Víctor Mora'])
check('historietistas are writers too', 'DuBouillon' in ct.writers_sl, True)
check('cover artist', ct.cover_artists_sl, ['L. Bermejo'])
check('translator (site casing)', ct.translators_sl, ['Mari Carmen Otero'])
print('     pencillers:', ct.pencillers_sl)
check('historietistas now credited', 'DuBouillon' in ct.pencillers_sl, True)
check('directora de publicacion now credited', 'Montserrat Vives' in ct.editors_sl, True)
check('black and white', ct.black_and_white, False)

print('--- live: a black-and-white comic')
bwref = tbf.IssueRef('1', 'x', url_s=
     'https://www.tebeosfera.com/numeros/capitan_trueno_el_1964_bruguera_-album_gigante-_1.html')
bwi = tbf.query_issue(bwref)
check('black and white', bwi.black_and_white, True)

# --- ComicBook.update against a fake ComicRack book
print('--- ComicBook.update')
sys.modules['System'].__dict__.update(DateTime=lambda y, m, d: (y, m, d),
    Enum=types.SimpleNamespace(Parse=lambda t, name: name),
    String=str, BitConverter=None)
stub('System.Security'); stub('System.Security.Cryptography', MD5CryptoServiceProvider=None)
for n in ('bookdata', 'pluginbookdata', 'configuration', 'comicbook'):
    load(n)
cfgmod = sys.modules['configuration']
cfgmod.load_map = lambda p: {}
cfgmod.load_string = lambda p: ''
ComicBook = sys.modules['comicbook'].ComicBook

class YesNo(object):
    def __init__(self, v): self.v = v
    def __str__(self): return self.v
    def GetType(self): return 'YesNo'

class FakeBook(object):
    '''Like ComicRack's ComicBook: Year/Month/Day ints (-1 = blank), and a
    read-only Published date that can't be assigned.'''
    @property
    def Published(self):
        return None

def fake_book(**kw):
    b = FakeBook()
    b.__dict__.update(dict(Series='', Number='', Title='', Volume=0, Publisher='',
        Imprint='', Format='', Year=-1, Month=-1, Day=-1, PageCount=0, Summary='',
        Web='', Writer='', Penciller='', Inker='', Colorist='', Letterer='',
        CoverArtist='', Editor='', Genre='', Characters='', ISSN='', ISBN='',
        FilePath='C:\\comics\\miedo.cbz', LanguageISO='', BlackAndWhite=YesNo('Unknown'),
        Notes=''))
    b.__dict__.update(kw)
    return b

def scrape(issue, crbook, **opts):
    cfg = cfgmod.Configuration()
    for k, v in opts.items():
        setattr(cfg, k, v)
    scraper = types.SimpleNamespace(config=cfg, comicrack=None)
    ComicBook(crbook, scraper).update(issue)
    return crbook

b = scrape(miedo, fake_book(Series='miedo (typed by hand)'), copy_penciller_to_inker_b=True, copy_penciller_to_cover_artist_b=True, copy_penciller_to_colorist_b=True)
check('series replaced (was the name mix-up)', b.Series, 'Miedo')
check('number', b.Number, '1')
check('inker <- penciller', b.Inker, 'Javi Rodríguez')
check('cover artist <- penciller', b.CoverArtist, 'Javi Rodríguez')
check('colorist <- penciller (colour comic)', b.Colorist, 'Javi Rodríguez')
check('language', b.LanguageISO, 'es')
check('black and white', str(b.BlackAndWhite), 'No')

check('Miedo date: year, month (X-2003)', (b.Year, b.Month, b.Day), (2003, 10, -1))

b = scrape(ct, fake_book())
check('Capitan Trueno #10 date (12-V-1986)', (b.Year, b.Month, b.Day), (1986, 5, 12))

year_only = sys.modules['dbmodels'].Issue(tbf.IssueRef('1', 'y', url_s='http://x'))
year_only.series_name_s = 'X'
year_only.pub_year_n = 1986
b = scrape(year_only, fake_book(Year=1990, Month=6, Day=15))
check('year-only date clears old month/day', (b.Year, b.Month, b.Day), (1986, -1, -1))

b = scrape(miedo, fake_book())
check('copy option off: inker stays empty', b.Inker, '')

b = scrape(miedo, fake_book(LanguageISO='ca'))
check('existing language kept', b.LanguageISO, 'ca')

b = scrape(bwi, fake_book(), copy_penciller_to_inker_b=True, copy_penciller_to_cover_artist_b=True, copy_penciller_to_colorist_b=True)
check('B&W comic: no colorist from penciller', b.Colorist, '')
check('B&W comic: flag', str(b.BlackAndWhite), 'Yes')

print('--- separate penciller copy settings')
b = scrape(miedo, fake_book(), copy_penciller_to_inker_b=True)
check('inker only: inker <- penciller', b.Inker, 'Javi Rodríguez')
check('inker only: cover artist stays empty', b.CoverArtist, '')
check('inker only: colorist stays empty', b.Colorist, '')
b = scrape(miedo, fake_book(), copy_penciller_to_colorist_b=True)
check('colorist only: colorist <- penciller', b.Colorist, 'Javi Rodríguez')
check('colorist only: inker stays empty', b.Inker, '')

print('--- old combined setting carries over to all three')
cfgmod.load_map = lambda p: {'copy_penciller_credits_b': True}
c = cfgmod.Configuration()
check('migrated', (c.copy_penciller_to_inker_b, c.copy_penciller_to_cover_artist_b,
                   c.copy_penciller_to_colorist_b), (True, True, True))
cfgmod.load_map = lambda p: {'copy_penciller_credits_b': True,
                             'copy_penciller_to_inker_b': False}
c = cfgmod.Configuration()
check('new settings win once saved', c.copy_penciller_to_cover_artist_b, False)
cfgmod.load_map = lambda p: {}

print('--- title only if different from the series')
check('#10 title is the series name', (ct.title_s, ct.series_name_s),
      ('El Capitan Trueno', 'El Capitan Trueno'))
b = scrape(ct, fake_book())
check('option on (default): title not set', b.Title, '')
b = scrape(ct, fake_book(Title='keep me'))
check('option on: existing title left alone', b.Title, 'keep me')
b = scrape(ct, fake_book(), title_only_if_different_b=False)
check('option off: title set', b.Title, 'El Capitan Trueno')
own = tbf.query_issue(tbf.IssueRef('55', 'x', url_s=
      'https://www.tebeosfera.com/numeros/capitan_trueno_el_2017_salvat_-60_aniversario-_55.html'))
b = scrape(own, fake_book())
check('different title is set', b.Title, u'\xa1El Combate por Sigridsholm!')
own.title_s = 'CAPITAN TRUENO, EL'      # article moved, no accent: still the same
b = scrape(own, fake_book())
check('same title in other form: not set', b.Title, '')

print('--- proposed series used when Series is blank')
ComicBookCls = sys.modules['comicbook'].ComicBook
cfg = cfgmod.Configuration()
scraper = types.SimpleNamespace(config=cfg, comicrack=None)
cb = ComicBookCls(fake_book(ProposedSeries='Miedo'), scraper)
check('search term is the proposed series', cb.series_s, 'Miedo')
cb = ComicBookCls(fake_book(Series='Real', ProposedSeries='Guess'), scraper)
check('a set Series wins over the proposal', cb.series_s, 'Real')
b = scrape(miedo, fake_book(ProposedSeries='miedo guess'), ow_existing_b=False)
check('blank Series still filled in (no overwrite)', b.Series, 'Miedo')

print('--- historietista does everything; translator after the writer')
bm = tbf.query_issue(tbf.IssueRef('1', 'x', url_s=
     'https://www.tebeosfera.com/numeros/buenos_modales_los_2023_nuevo_nueve.html'))
for f in ('writers_sl', 'pencillers_sl', 'inkers_sl', 'letterers_sl', 'colorists_sl'):
    check('historietista -> ' + f, getattr(bm, f), ['Daniel Cuello'])
check('historietista is not cover artist', bm.cover_artists_sl, [])
check('translator', bm.translators_sl, ['Inés Sánchez Mesonero'])
b = scrape(bm, fake_book())
check('Writer: original, then translator', b.Writer, 'Daniel Cuello, Inés Sánchez Mesonero')
check('Penciller/Inker/Colorist/Letterer', (b.Penciller, b.Inker, b.Colorist, b.Letterer),
      ('Daniel Cuello',) * 4)
b = scrape(bm, fake_book(), translators_as_writers_b=False)
check('translator option off', b.Writer, 'Daniel Cuello')

bw_page = (u'<div id="cuerpo2_ficha"><div class="row-fluid"><div class="span3 etiqueta">Color:</div>'
           u'<div class="span9 dato">BLANCO Y NEGRO</div></div>'
           u'<div class="row-fluid tab_datos"><span class="tab_subtitulo">Historietista '
           u'<span class="peque">1</span></span>: <a href="/autores/x.html" title="ANA">ANA</a></div></div>')
bwi2 = sys.modules['dbmodels'].Issue(tbf.IssueRef('1', 'z', url_s='http://x'))
tbf.parse_issue_page(bw_page, bwi2)
check('B&W historietista: no colorist', (bwi2.black_and_white, bwi2.colorists_sl), (True, []))
check('B&W historietista: still inker', bwi2.inkers_sl, ['Ana'])

print('--- summary: description + synopsis (div_recension)')
cn = tbf.query_issue(tbf.IssueRef('1', 'x', url_s=
     'https://www.tebeosfera.com/numeros/cuando_no_sabes_que_decir_2023_andana.html'))
summ = cn.summary_s
check('starts with the physical description',
      summ.startswith(u'Libro de historieta de 128 p\xe1ginas'), True)
check('includes the synopsis', u'Una gran amistad se acaba' in summ, True)
check('includes the last paragraph', u'Andana Gr\xe0fica recupera esta obra' in summ, True)
check('no control characters left', any(u'\x80' <= c <= u'\x9f' for c in summ), False)
check('0x97 became an em dash', u'soledad\u2014 comienza' in summ, True)
check('Miedo summary unchanged', miedo.summary_s.startswith(u'Libro de 48 p\xe1ginas en color'), True)

print('\n%d failure(s)' % len(fails))
sys.exit(1 if fails else 0)
