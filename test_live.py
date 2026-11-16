# -*- coding: utf-8 -*-
'''Runs the plugin's tebeosfera code under CPython against the live site.
.NET is stubbed; HTTP is done with urllib in place of HttpWebRequest.'''
import sys, types, re, html, urllib.request, urllib.parse

def stub(name, **attrs):
    m = types.ModuleType(name); m.__dict__.update(attrs); sys.modules[name] = m

class _Any(object):
    def __getattr__(self, k): return _Any()
    def __call__(self, *a, **k): return _Any()

stub('clr', AddReference=lambda *a: None)
stub('System', Environment=_Any(), DateTime=_Any(), Uri=_Any())
stub('System.IO', Path=_Any(), Directory=_Any(), File=_Any(), StreamReader=_Any())
stub('System.Text', Encoding=_Any())
stub('System.Windows'); stub('System.Windows.Forms', Control=_Any(), MethodInvoker=_Any(),
     MessageBox=_Any(), MessageBoxButtons=_Any(), MessageBoxIcon=_Any())
stub('System.Drawing', Image=_Any(), Bitmap=_Any(), Color=_Any(), ContentAlignment=_Any())
stub('System.Net', WebUtility=types.SimpleNamespace(HtmlDecode=html.unescape),
     HttpWebRequest=_Any(), CookieContainer=_Any())

def load(name):
    src = open('src/%s.py' % name, encoding='utf-8').read()
    src = re.sub(r'except\s+(\w+)\s*,\s*(\w+)\s*:', r'except \1 as \2:', src)
    src = re.sub(r'^(\s*)print (.+)$', r'\1print(\2)', src, flags=re.M)
    mod = types.ModuleType(name)
    mod.__dict__.update(unicode=str, long=int, cmp=lambda a, b: (a > b) - (a < b))
    sys.modules[name] = mod
    exec(compile(src, name, 'exec'), mod.__dict__)
    return mod

for n in ('utils', 'log', 'resources', 'dbmodels'):
    load(n)
tbf = load('tbfscraper')

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
def fetch_url(url, encoding='utf-8'):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode(encoding)
def post_url(url, fields, encoding='utf-8'):
    data = urllib.parse.urlencode(fields).encode('utf-8')
    # same headers as the plugin's post_url sends
    req = urllib.request.Request(url, data=data, headers=dict(UA, **{
        'X-Requested-With': 'XMLHttpRequest', 'Referer': 'https://www.tebeosfera.com/'}))
    return urllib.request.urlopen(req, timeout=120).read().decode(encoding)
tbf.fetch_url = fetch_url
tbf.post_url = post_url

def show_search(term, n=8):
    refs = tbf.search_collections(term, 25)
    print('\nSEARCH %r -> %d results (capped at 25); top %d:' % (term, len(refs), n))
    for r in refs[:n]:
        print('   %-45s year=%-5s pub=%-14s issues=%-3s key=%s'
              % (r.series_name_s[:45], r.volume_year_n, r.publisher_s[:14], r.issue_count_n, r.series_key))
    return refs

refs = show_search('Miedo')
target = [r for r in refs if r.series_key == 'miedo_2003_glenat']
assert target, 'miedo_2003_glenat not in results'
print('   -> miedo_2003_glenat is at position %d' % (refs.index(target[0]) + 1))

issues = tbf.query_issue_refs(target[0])
print('\nISSUES of miedo_2003_glenat:', [(i.issue_num_s, i.url_s) for i in issues])
assert len(issues) == 1


def show_issue(issue):
    for f in ('series_name_s', 'series_key', 'issue_num_s', 'title_s', 'publisher_s',
              'pub_year_n', 'pub_month_n', 'pub_day_n', 'page_count_n', 'format_s',
              'writers_sl', 'pencillers_sl', 'cover_artists_sl', 'translators_sl',
              'editors_sl', 'genres_sl', 'characters_sl', 'issn_s', 'isbn_s'):
        print('   %-16s %r' % (f, getattr(issue, f)))
    print('   %-16s %r' % ('summary_s', issue.summary_s[:160]))

print('\nISSUE DETAILS (re-run with new parser):')
show_issue(tbf.query_issue(list(issues)[0]))

# a richer issue: full date, distributor + printer entities, ISSN, other tabs
cap = tbf.SeriesRef('capitan_trueno_el_1986_bruguera_-nuevas_aventuras-',
                    url_s='https://www.tebeosfera.com/colecciones/capitan_trueno_el_1986_bruguera_-nuevas_aventuras-.html')
cap_issues = tbf.query_issue_refs(cap)
print('\nISSUES of capitan trueno 1986:', len(cap_issues))
ten = tbf.query_issue_ref(cap, '10')
print('ISSUE #10:')
show_issue(tbf.query_issue(ten))

# multi-issue collection uses the jumper
salvat = tbf.SeriesRef('capitan_trueno_el_2017_salvat_-60_aniversario-',
                       url_s='https://www.tebeosfera.com/colecciones/capitan_trueno_el_2017_salvat_-60_aniversario-.html')
print('\nISSUES of capitan trueno 2017 salvat:', len(tbf.query_issue_refs(salvat)))

# accented search, timed
import time
t = time.time()
show_search(u'Capitán Trueno', 5)
print('   (took %.1fs)' % (time.time() - t))
