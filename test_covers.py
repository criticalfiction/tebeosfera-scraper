# -*- coding: utf-8 -*-
'''Checks that every series/issue in the result lists resolves to a real,
downloadable preview image (plugin code, CPython, .NET stubbed).'''
import sys, urllib.request
exec(open('test_live.py', encoding='utf-8').read().split('def show_search')[0])

fetched = []
def fake_fetch_image(url):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60)
        if not r.headers.get('Content-Type', '').startswith('image/'):
            return None
        data = r.read()
        fetched.append(url)
        return ('IMAGE', len(data))
    except Exception:
        return None
tbf.fetch_image = fake_fetch_image

fails = []
def check(label, ok, detail=''):
    print('%s %s %s' % ('ok  ' if ok else 'FAIL', label, detail))
    if not ok:
        fails.append(label)

print('--- series results: preview for the top 5 "Miedo" matches')
for ref in tbf.search_collections('Miedo', 25)[:5]:
    del fetched[:]
    img, _ = tbf.query_preview(ref)
    check(ref.series_name_s, img is not None, fetched[-1] if fetched else '(none)')
    if img and 'w-200_' not in fetched[-1]:
        print('     note: used the full-size image, no w-200 copy')

def issues_of(slug):
    return sorted(tbf.query_issue_refs(tbf.SeriesRef(
        slug, url_s='https://www.tebeosfera.com/colecciones/%s.html' % slug)),
        key=lambda r: sys.modules['utils'].natural_key(r.issue_num_s))

print('--- issues of Miedo (single issue)')
for ref in issues_of('miedo_2003_glenat'):
    del fetched[:]
    check('#' + ref.issue_num_s + ' thumb from gallery', ref.thumb_url_s is not None, ref.thumb_url_s or '')
    check('#' + ref.issue_num_s + ' preview', tbf.query_preview(ref)[0] is not None, fetched[-1] if fetched else '')

print('--- issues of Capitan Trueno 2017 Salvat (61, gallery shows 51)')
refs = issues_of('capitan_trueno_el_2017_salvat_-60_aniversario-')
missing = [r for r in refs if not r.thumb_url_s]
print('     %d issues, %d with gallery cover, missing: %s'
      % (len(refs), len(refs) - len(missing), [r.issue_num_s for r in missing]))
for ref in [refs[0], refs[-1]] + missing[:2]:
    del fetched[:]
    img, _ = tbf.query_preview(ref)
    check('#%s preview (%s)' % (ref.issue_num_s, 'gallery' if ref.thumb_url_s else 'from issue page'),
          img is not None, fetched[-1] if fetched else '')

print('--- a page with no cover of its own must not borrow a sidebar image')
side = '<div id="sidebar"><img id="img_principal" src="/T3content/img/x/y/promo.jpg" /></div>'
check('no cover -> None', tbf._main_cover_url('<div id="cuerpo2_ficha"></div>' + side) is None)

print('\n%d failure(s)' % len(fails))
sys.exit(1 if fails else 0)
