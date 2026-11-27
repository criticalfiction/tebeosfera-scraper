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

print('--- issue titles')
T = tbf._issue_title
check('just a title', T('MIEDO'), 'Miedo')
check('series, line break, own title',
      T('<span style="color:#999">EL CAPITAN TRUENO</span><br>EL COMBATE POR SIGRIDSHOLM'),
      'El Combate por Sigridsholm')
check('edition note in its own div: the note is the title',
      T('CALAVERA LUNAR<div><strong>especial 25 aniversario</strong></div>'),
      'Especial 25 aniversario')
check('own title and a note', T('<span>X</span><br>OWN TITLE<div>NOTA</div>'),
      'Own Title (Nota)')
check('empty note div ignored', T('MIEDO<div></div>'), 'Miedo')
cal = tbf.query_issue(tbf.IssueRef('1', 'x', url_s=
      'https://www.tebeosfera.com/numeros/calavera_lunar_2022_astiberri.html'))
check('live: the note is the title', cal.title_s, 'Especial 25 aniversario')
check('live: series', cal.series_name_s, 'Calavera Lunar')
b = scrape(cal, fake_book())
check('title differs from the series, so it is set', b.Title,
      'Especial 25 aniversario')
print('--- live: Yo, Julio Cesar (2025, Reservoir)')
yjc_ref = tbf.IssueRef('1', 'x', url_s=
    'https://www.tebeosfera.com/numeros/yo_julio_cesar_2025_reservoir.html')
yjc = tbf.query_issue(yjc_ref)
check('publisher is the imprint, not the group', yjc.publisher_s, 'Reservoir Books')
check('trailing dash dropped from the name', yjc.pencillers_sl, [u'N\xe9vil'])
check('colorist (signature, the default)', yjc.colorists_sl, [u'1ver2\xe2nes'])
for style, want in [(tbf.NAME_REAL, u'V\xe9rane \xd3tero'),
                    (tbf.NAME_SIGNATURE_REAL, u'1ver2\xe2nes (V\xe9rane \xd3tero)'),
                    (tbf.NAME_REAL_SIGNATURE, u'V\xe9rane \xd3tero (1ver2\xe2nes)')]:
    check('colorist, name style %d' % style,
          tbf.query_issue(yjc_ref, name_style=style).colorists_sl, [want])
real = tbf.query_issue(yjc_ref, name_style=tbf.NAME_REAL)
check('no separate real name: name kept', (real.pencillers_sl, real.writers_sl),
      ([u'N\xe9vil'], ['Alfred De Montesquiou']))
b = scrape(yjc, fake_book(), copy_penciller_to_inker_b=True,
           copy_penciller_to_cover_artist_b=True, copy_penciller_to_colorist_b=True)
check('dibujante -> inker, cover artist', (b.Inker, b.CoverArtist), (u'N\xe9vil',) * 2)
check('credited colorist not replaced', b.Colorist, u'1ver2\xe2nes')
b = scrape(yjc, fake_book())
check('Publisher on the book', b.Publisher, 'Reservoir Books')
print('--- credit name styles (offline)')
cn_ = tbf._credit_name
dub = ('DuBouillon -Alain Bouillon-', 'DUBOUILLON')
check('signature, site casing', cn_(*dub), 'DuBouillon')
check('real name', cn_(*dub, style=tbf.NAME_REAL), 'Alain Bouillon')
check('signature (real name)', cn_(*dub, style=tbf.NAME_SIGNATURE_REAL),
      'DuBouillon (Alain Bouillon)')
check('real name (signature)', cn_(*dub, style=tbf.NAME_REAL_SIGNATURE),
      'Alain Bouillon (DuBouillon)')
check('no real name in the title', cn_('ANA', 'ANA', tbf.NAME_SIGNATURE_REAL), 'Ana')
check('real name same as signature',
      cn_(u'N\xe9vil - -N\xe9vil-', u'N\xc9VIL -', tbf.NAME_SIGNATURE_REAL), u'N\xe9vil')
print('--- name casing: initials stay upper-case')
for raw, want in [('JMV', 'JMV'), ('JOSE A. SERRANO', 'Jose A. Serrano'),
                  ('J.M. BEAZ', 'J.M. Beaz'), ('L. BERMEJO', 'L. Bermejo'),
                  ('JOSE A SERRANO', 'Jose A Serrano'),
                  ('ORTEGA Y GASSET', 'Ortega y Gasset'),
                  ('PUIG I CADAFALCH', 'Puig i Cadafalch'),
                  ('MARI CARMEN DE LA FUENTE', 'Mari Carmen de la Fuente'),
                  ('GLYNN', 'Glynn'), ('Mari Carmen Otero', 'Mari Carmen Otero')]:
    check('name ' + raw, utils.smart_name(raw), want)
check('titles unchanged', utils.smart_title('JMV'), 'Jmv')
print('--- smart credit name styles (offline, titles as the site gives them)')
SR, RS = tbf.NAME_SIGNATURE_REAL_SMART, tbf.NAME_REAL_SIGNATURE_SMART
for title, text, want_sr, want_rs in [
        # signature word inside the name: surnames after it dropped
        ('MONTEYS -Albert Monteys Homar-', 'MONTEYS',
         'Monteys (Albert Monteys)', 'Albert Monteys'),
        # the shortened name is the signature: said once
        (u'FERM\xcdN SOL\xcdS -Ferm\xedn Sol\xeds Campos-', u'FERM\xcdN SOL\xcdS',
         u'Ferm\xedn Sol\xeds', u'Ferm\xedn Sol\xeds'),
        # an initial says no more than the name
        ('MANEL F. -Manel Fontdevila Subirana-', 'MANEL F.',
         'Manel F. (Manel Fontdevila)', 'Manel Fontdevila'),
        ('JOSE A. SERRANO -Jose Antonio Serrano-', 'JOSE A. SERRANO',
         'Jose A. Serrano (Jose Antonio Serrano)', 'Jose Antonio Serrano'),
        # not taken from the name: whole name, both parts
        (u'JMV -Jes\xfas Mart\xednez Del Vas-', 'JMV',
         u'JMV (Jes\xfas Mart\xednez Del Vas)', u'Jes\xfas Mart\xednez Del Vas (JMV)'),
        # one signature word in the name: cut there, the other word kept
        (u'PEPO P\xc9REZ -Juan Carlos P\xe9rez Garc\xeda-', u'PEPO P\xc9REZ',
         u'Pepo P\xe9rez (Juan Carlos P\xe9rez)', u'Juan Carlos P\xe9rez (Pepo P\xe9rez)'),
        # a given name (two parts still after it): not cut there
        (u'Daniel Ausente -Jorge Daniel Fern\xe1ndez Castany-', 'DANIEL AUSENTE',
         u'Daniel Ausente (Jorge Daniel Fern\xe1ndez Castany)',
         u'Jorge Daniel Fern\xe1ndez Castany (Daniel Ausente)'),
        # particles join the next word: Del Vas, San Martin are one part each
        (u'MART\xcdNEZ -Jes\xfas Mart\xednez Del Vas-', u'MART\xcdNEZ',
         u'Mart\xednez (Jes\xfas Mart\xednez)', u'Jes\xfas Mart\xednez'),
        (u'OCTAVIO BEARES -Octavio Beares San Mart\xedn-', 'OCTAVIO BEARES',
         'Octavio Beares', 'Octavio Beares'),
        # just the first name: whole name, both parts
        ('GUILLERMO -Guillermo Torres Meana-', 'GUILLERMO',
         'Guillermo (Guillermo Torres Meana)', 'Guillermo Torres Meana (Guillermo)'),
        # a short form of a surname is kept
        (u'FER -Jos\xe9 Antonio Fern\xe1ndez Fern\xe1ndez-', 'FER',
         u'Fer (Jos\xe9 Antonio Fern\xe1ndez)', u'Jos\xe9 Antonio Fern\xe1ndez (Fer)'),
        # accents differ only: the real name's spelling
        ('ALBERTO GARCIA -Alberto Garc\xeda Marcos-', 'ALBERTO GARCIA',
         u'Alberto Garc\xeda', u'Alberto Garc\xeda'),
        # no real name
        ('BORJA CRESPO', 'BORJA CRESPO', 'Borja Crespo', 'Borja Crespo')]:
    check(text + ', signature first', cn_(title, text, SR), want_sr)
    check(text + ', real name first', cn_(title, text, RS), want_rs)
check('non-smart style unchanged',
      cn_('MONTEYS -Albert Monteys Homar-', 'MONTEYS', tbf.NAME_REAL_SIGNATURE),
      'Albert Monteys Homar (Monteys)')
print('--- ilustrador credits')
for label in ('Ilustrador', 'Ilustradora 2', 'Ilustradores'):
    check(label, tbf._credit_type(label), 'penciller')
il_page = (u'<div id="cuerpo2_ficha"><div class="row-fluid tab_datos"><span class="tab_subtitulo">'
           u'Ilustradora <span class="peque">1</span></span>: '
           u'<a href="/autores/x.html" title="EVA">EVA</a></div></div>')
il = sys.modules['dbmodels'].Issue(tbf.IssueRef('1', 'z', url_s='http://x'))
tbf.parse_issue_page(il_page, il)
check('ilustradora is the penciller', (il.pencillers_sl, il.inkers_sl), (['Eva'], []))
b = scrape(il, fake_book(), copy_penciller_to_inker_b=True)
check('ilustrador -> inker by the copy setting', b.Inker, 'Eva')
print('--- credit name style setting')
check('default', cfgmod.Configuration().credit_name_style_n, 0)
cfgmod.load_map = lambda p: {'credit_name_style_n': 3}
check('saved value read', cfgmod.Configuration().credit_name_style_n, 3)
cfgmod.load_map = lambda p: {'credit_name_style_n': 5}
check('smart style read', cfgmod.Configuration().credit_name_style_n, 5)
cfgmod.load_map = lambda p: {'credit_name_style_n': 9}
check('out of range -> default', cfgmod.Configuration().credit_name_style_n, 0)
cfgmod.load_map = lambda p: {}
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
