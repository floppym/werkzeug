# -*- coding: utf-8 -*-
"""
    werkzeug.http test
    ~~~~~~~~~~~~~~~~~~~

    :license: BSD license.
"""
from datetime import datetime

from nose.tools import assert_raises

from werkzeug.http import *
from werkzeug.utils import redirect
from werkzeug.test import create_environ
from werkzeug.datastructures import *


def test_accept():
    """Regular accept header parsing and behavior"""
    a = parse_accept_header('en-us,ru;q=0.5')
    assert a.values() == ['en-us', 'ru']
    assert a.best == 'en-us'
    assert a.find('ru') == 1
    assert_raises(ValueError, lambda: a.index('de'))
    assert a.to_header() == 'en-us,ru;q=0.5'


def test_mime_accept():
    """MIME accept header parsing and behavior"""
    a = parse_accept_header('text/xml,application/xml,application/xhtml+xml,'
                            'text/html;q=0.9,text/plain;q=0.8,'
                            'image/png,*/*;q=0.5', MIMEAccept)
    assert_raises(ValueError, lambda: a['missing'])
    assert a['image/png'] == 1
    assert a['text/plain'] == 0.8
    assert a['foo/bar'] == 0.5
    assert a[a.find('foo/bar')] == ('*/*', 0.5)

    # was a bug in 0.6
    parse_accept_header('foo=,application/xml,application/xhtml+xml,'
                        'text/html;q=0.9,text/plain;q=0.8,'
                        'image/png,*/*;q=0.5', MIMEAccept).best_match(['foo/bar'])


def test_accept_matches():
    """The `best_match` feature of accept objects"""
    a = parse_accept_header('text/xml,application/xml,application/xhtml+xml,'
                            'text/html;q=0.9,text/plain;q=0.8,'
                            'image/png', MIMEAccept)
    assert a.best_match(['text/html', 'application/xhtml+xml']) == \
        'application/xhtml+xml'
    assert a.best_match(['text/html']) == 'text/html'
    assert a.best_match(['foo/bar']) is None
    assert a.best_match(['foo/bar', 'bar/foo'],
                        default='foo/bar') == 'foo/bar'
    assert a.best_match(['application/xml', 'text/xml']) == 'application/xml'


def test_charset_accept():
    """Charset accept header parsing and behavior"""
    a = parse_accept_header('ISO-8859-1,utf-8;q=0.7,*;q=0.7', CharsetAccept)
    assert a['iso-8859-1'] == a['iso8859-1'] == 1
    assert a['UTF8'] == 0.7
    assert a['ebcdic'] == 0.7


def test_language_accept():
    """Language accept header parsing and behavior"""
    a = parse_accept_header('de-AT,de;q=0.8,en;q=0.5', LanguageAccept)
    assert a.best == 'de-AT'
    assert 'de_AT' in a
    assert 'en' in a
    assert a['de-at'] == 1
    assert a['en'] == 0.5


def test_set_header():
    """Set header parsing and behavior"""
    hs = parse_set_header('foo, Bar, "Blah baz", Hehe')
    assert 'blah baz' in hs
    assert 'foobar' not in hs
    assert 'foo' in hs
    assert list(hs) == ['foo', 'Bar', 'Blah baz', 'Hehe']
    hs.add('Foo')
    assert hs.to_header() == 'foo, Bar, "Blah baz", Hehe'


def test_list_header():
    """List header parsing"""
    hl = parse_list_header('foo baz, blah')
    assert hl == ['foo baz', 'blah']


def test_dict_header():
    """Dict header parsing"""
    d = parse_dict_header('foo="bar baz", blah=42')
    assert d == {'foo': 'bar baz', 'blah': '42'}


def test_cache_control_header():
    """Cache control header parsing and behavior"""
    cc = parse_cache_control_header('max-age=0, no-cache')
    assert cc.max_age == 0
    assert cc.no_cache
    cc = parse_cache_control_header('private, community="UCI"', None,
                                    ResponseCacheControl)
    assert cc.private
    assert cc['community'] == 'UCI'

    c = ResponseCacheControl()
    assert c.no_cache is None
    assert c.private is None
    c.no_cache = True
    assert c.no_cache == '*'
    c.private = True
    assert c.private == '*'
    del c.private
    assert c.private is None
    assert c.to_header() == 'no-cache'


def test_authorization_header():
    """Authorization header parsing and behavior"""
    a = parse_authorization_header('Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ==')
    assert a.type == 'basic'
    assert a.username == 'Aladdin'
    assert a.password == 'open sesame'

    a = parse_authorization_header('''Digest username="Mufasa",
                 realm="testrealm@host.invalid",
                 nonce="dcd98b7102dd2f0e8b11d0f600bfb0c093",
                 uri="/dir/index.html",
                 qop=auth,
                 nc=00000001,
                 cnonce="0a4f113b",
                 response="6629fae49393a05397450978507c4ef1",
                 opaque="5ccc069c403ebaf9f0171e9517f40e41"''')
    assert a.type == 'digest'
    assert a.username == 'Mufasa'
    assert a.realm == 'testrealm@host.invalid'
    assert a.nonce == 'dcd98b7102dd2f0e8b11d0f600bfb0c093'
    assert a.uri == '/dir/index.html'
    assert 'auth' in a.qop
    assert a.nc == '00000001'
    assert a.cnonce == '0a4f113b'
    assert a.response == '6629fae49393a05397450978507c4ef1'
    assert a.opaque == '5ccc069c403ebaf9f0171e9517f40e41'
    
    a = parse_authorization_header('''Digest username="Mufasa",
                 realm="testrealm@host.invalid",
                 nonce="dcd98b7102dd2f0e8b11d0f600bfb0c093",
                 uri="/dir/index.html",
                 response="e257afa1414a3340d93d30955171dd0e",
                 opaque="5ccc069c403ebaf9f0171e9517f40e41"''')
    assert a.type == 'digest'
    assert a.username == 'Mufasa'
    assert a.realm == 'testrealm@host.invalid'
    assert a.nonce == 'dcd98b7102dd2f0e8b11d0f600bfb0c093'
    assert a.uri == '/dir/index.html'
    assert a.response == 'e257afa1414a3340d93d30955171dd0e'
    assert a.opaque == '5ccc069c403ebaf9f0171e9517f40e41'
    
    assert parse_authorization_header('') is None
    assert parse_authorization_header(None) is None
    assert parse_authorization_header('foo') is None


def test_www_authenticate_header():
    """WWW Authenticate header parsing and behavior"""
    wa = parse_www_authenticate_header('Basic realm="WallyWorld"')
    assert wa.type == 'basic'
    assert wa.realm == 'WallyWorld'
    wa.realm = 'Foo Bar'
    assert wa.to_header() == 'Basic realm="Foo Bar"'

    wa = parse_www_authenticate_header('''Digest
                 realm="testrealm@host.com",
                 qop="auth,auth-int",
                 nonce="dcd98b7102dd2f0e8b11d0f600bfb0c093",
                 opaque="5ccc069c403ebaf9f0171e9517f40e41"''')
    assert wa.type == 'digest'
    assert wa.realm == 'testrealm@host.com'
    assert 'auth' in wa.qop
    assert 'auth-int' in wa.qop
    assert wa.nonce == 'dcd98b7102dd2f0e8b11d0f600bfb0c093'
    assert wa.opaque == '5ccc069c403ebaf9f0171e9517f40e41'

    wa = parse_www_authenticate_header('broken')
    assert wa.type == 'broken'

    assert not parse_www_authenticate_header('').type
    assert not parse_www_authenticate_header('')


def test_etags():
    """ETag tools"""
    assert quote_etag('foo') == '"foo"'
    assert quote_etag('foo', True) == 'w/"foo"'
    assert unquote_etag('"foo"') == ('foo', False)
    assert unquote_etag('w/"foo"') == ('foo', True)
    es = parse_etags('"foo", "bar", w/"baz", blar')
    assert sorted(es) == ['bar', 'blar', 'foo']
    assert 'foo' in es
    assert 'baz' not in es
    assert es.contains_weak('baz')
    assert 'blar' in es
    assert es.contains_raw('w/"baz"')
    assert es.contains_raw('"foo"')
    assert sorted(es.to_header().split(', ')) == ['"bar"', '"blar"', '"foo"', 'w/"baz"']


def test_parse_date():
    """Date parsing"""
    assert parse_date('Sun, 06 Nov 1994 08:49:37 GMT    ') == datetime(1994, 11, 6, 8, 49, 37)
    assert parse_date('Sunday, 06-Nov-94 08:49:37 GMT') == datetime(1994, 11, 6, 8, 49, 37)
    assert parse_date(' Sun Nov  6 08:49:37 1994') == datetime(1994, 11, 6, 8, 49, 37)
    assert parse_date('foo') is None


def test_parse_date_overflows():
    """Test for problematic days."""
    assert parse_date(' Sun 02 Feb 1343 08:49:37 GMT') == datetime(1343, 2, 2, 8, 49, 37)
    assert parse_date('Thu, 01 Jan 1970 00:00:00 GMT') == datetime(1970, 1, 1, 0, 0)
    assert parse_date('Thu, 33 Jan 1970 00:00:00 GMT') is None


def test_remove_entity_headers():
    """Entity header removing function"""
    now = http_date()
    headers1 = [('Date', now), ('Content-Type', 'text/html'), ('Content-Length', '0')]
    headers2 = Headers(headers1)

    remove_entity_headers(headers1)
    assert headers1 == [('Date', now)]

    remove_entity_headers(headers2)
    assert headers2 == Headers([('Date', now)])


def test_remove_hop_by_hop_headers():
    """Hop-by-Hop header removing function"""
    headers1 = [('Connection', 'closed'), ('Foo', 'bar'),
                ('Keep-Alive', 'wtf')]
    headers2 = Headers(headers1)

    remove_hop_by_hop_headers(headers1)
    assert headers1 == [('Foo', 'bar')]

    remove_hop_by_hop_headers(headers2)
    assert headers2 == Headers([('Foo', 'bar')])


def test_redirect():
    """Tests the redirecting"""
    resp = redirect(u'/füübär')
    assert '/f%C3%BC%C3%BCb%C3%A4r' in resp.data
    assert resp.headers['Location'] == '/f%C3%BC%C3%BCb%C3%A4r'
    assert resp.status_code == 302

    resp = redirect(u'http://☃.net/', 307)
    assert 'http://xn--n3h.net/' in resp.data
    assert resp.headers['Location'] == 'http://xn--n3h.net/'
    assert resp.status_code == 307

    resp = redirect('http://example.com/', 305)
    assert resp.headers['Location'] == 'http://example.com/'
    assert resp.status_code == 305


def test_dump_options_header():
    """Test options header dumping alone"""
    assert dump_options_header('foo', {'bar': 42}) == \
        'foo; bar=42'
    assert dump_options_header('foo', {'bar': 42, 'fizz': None}) == \
        'foo; bar=42; fizz'


def test_dump_header():
    """Test the header dumping function alone"""
    assert dump_header([1, 2, 3]) == '1, 2, 3'
    assert dump_header([1, 2, 3], allow_token=False) == '"1", "2", "3"'
    assert dump_header({'foo': 'bar'}, allow_token=False) == 'foo="bar"'
    assert dump_header({'foo': 'bar'}) == 'foo=bar'


def test_parse_options_header():
    """Parse options header"""
    assert parse_options_header('something; foo="other\"thing"') == \
        ('something', {'foo': 'other"thing'})
    assert parse_options_header('something; foo="other\"thing"; meh=42') == \
        ('something', {'foo': 'other"thing', 'meh': '42'})
    assert parse_options_header('something; foo="other\"thing"; meh=42; bleh') == \
        ('something', {'foo': 'other"thing', 'meh': '42', 'bleh': None})


def test_is_resource_modified():
    """Test is_resource_modified alone"""
    env = create_environ()

    # ignore POST
    env['REQUEST_METHOD'] = 'POST'
    assert not is_resource_modified(env, etag='testing')
    env['REQUEST_METHOD'] = 'GET'

    # etagify from data
    assert_raises(TypeError, is_resource_modified, env, data='42', etag='23')
    env['HTTP_IF_NONE_MATCH'] = generate_etag('awesome')
    assert not is_resource_modified(env, data='awesome')

    env['HTTP_IF_MODIFIED_SINCE'] = http_date(datetime(2008, 1, 1, 12, 30))
    assert not is_resource_modified(env,
        last_modified=datetime(2008, 1, 1, 12, 00))
    assert is_resource_modified(env,
        last_modified=datetime(2008, 1, 1, 13, 00))


def test_dates():
    """Date formatting"""
    assert cookie_date(0) == 'Thu, 01-Jan-1970 00:00:00 GMT'
    assert cookie_date(datetime(1970, 1, 1)) == 'Thu, 01-Jan-1970 00:00:00 GMT'
    assert http_date(0) == 'Thu, 01 Jan 1970 00:00:00 GMT'
    assert http_date(datetime(1970, 1, 1)) == 'Thu, 01 Jan 1970 00:00:00 GMT'


def test_cookies():
    """Cookie parsing"""
    assert parse_cookie('dismiss-top=6; CP=null*; PHPSESSID=0a539d42abc001cd'
                        'c762809248d4beed; a=42') == {
        'CP':           u'null*',
        'PHPSESSID':    u'0a539d42abc001cdc762809248d4beed',
        'a':            u'42',
        'dismiss-top':  u'6'
    }
    assert set(dump_cookie('foo', 'bar baz blub', 360, httponly=True,
                           sync_expires=False).split('; ')) == \
           set(['HttpOnly', 'Max-Age=360', 'Path=/', 'foo="bar baz blub"'])
    assert parse_cookie('fo234{=bar blub=Blah') == {'blub': 'Blah'}


def test_cookie_quoting():
    """Cookie value quoting."""
    val = dump_cookie("foo", "?foo")
    assert val == 'foo="?foo"; Path=/'
    assert parse_cookie(val) == {'foo': '?foo'}

    assert parse_cookie(r'foo="foo\054bar"') == {'foo': 'foo,bar'}


def test_if_range_parsing():
    """Basic If-Range parsing."""
    rv = parse_if_range_header('"Test"')
    assert rv.etag == 'Test'
    assert rv.date is None
    assert rv.to_header() == '"Test"'

    # weak information is dropped
    rv = parse_if_range_header('w/"Test"')
    assert rv.etag == 'Test'
    assert rv.date is None
    assert rv.to_header() == '"Test"'

    # broken etags are supported too
    rv = parse_if_range_header('bullshit')
    assert rv.etag == 'bullshit'
    assert rv.date is None
    assert rv.to_header() == '"bullshit"'

    rv = parse_if_range_header('Thu, 01 Jan 1970 00:00:00 GMT')
    assert rv.etag is None
    assert rv.date == datetime(1970, 1, 1)
    assert rv.to_header() == 'Thu, 01 Jan 1970 00:00:00 GMT'

    for x in '', None:
        rv = parse_if_range_header(x)
        assert rv.etag is None
        assert rv.date is None
        assert rv.to_header() == ''


def test_range_parsing():
    """Parsing of the range header."""
    rv = parse_range_header('bytes=52')
    assert rv is None

    rv = parse_range_header('bytes=52-')
    assert rv.units == 'bytes'
    assert rv.ranges == [(52, None)]
    assert rv.to_header() == 'bytes=52-'

    rv = parse_range_header('bytes=52-99')
    assert rv.units == 'bytes'
    assert rv.ranges == [(52, 100)]
    assert rv.to_header() == 'bytes=52-99'

    rv = parse_range_header('bytes=52-99,-1000')
    assert rv.units == 'bytes'
    assert rv.ranges == [(52, 100), (-1000, None)]
    assert rv.to_header() == 'bytes=52-99,-1000'

    rv = parse_range_header('bytes = 1 - 100')
    assert rv.units == 'bytes'
    assert rv.ranges == [(1, 101)]
    assert rv.to_header() == 'bytes=1-100'

    rv = parse_range_header('AWesomes=0-999')
    assert rv.units == 'awesomes'
    assert rv.ranges == [(0, 1000)]
    assert rv.to_header() == 'awesomes=0-999'


def test_content_range_parsing():
    """Content-Range header parsing"""
    rv = parse_content_range_header('bytes 0-98/*')
    assert rv.units == 'bytes'
    assert rv.start == 0
    assert rv.stop == 99
    assert rv.length is None
    assert rv.to_header() == 'bytes 0-98/*'

    rv = parse_content_range_header('bytes 0-98/*asdfsa')
    assert rv is None

    rv = parse_content_range_header('bytes 0-99/100')
    assert rv.to_header() == 'bytes 0-99/100'
    rv.start = None
    rv.stop = None
    assert rv.units == 'bytes'
    assert rv.to_header() == 'bytes */100'

    rv = parse_content_range_header('bytes */100')
    assert rv.start is None
    assert rv.stop is None
    assert rv.length == 100
    assert rv.units == 'bytes'
