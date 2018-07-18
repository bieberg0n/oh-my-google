import ohmygoogle
# import socket
import http_utils
from utils import log


def ensure(b, e):
    assert b, e


def test_headers_by_str():
    t1 = 'GET / HTTP/1.1\r\nHost: 127.0.0.1:8080\r\nUser-Agent: curl/7.51.0\r\n\r\nAccept: */*\r\n\r\n'
    good_h1 = dict(
        method='GET',
        path='/',
        args={
            'Host': '127.0.0.1:8080',
            'User-Agent': 'curl/7.51.0',
            'Accept': '*/*',
        }
    )
    t2 = 'POST / HTTP/1.1\r\nHost: 127.0.0.1:8080\r\nUser-Agent: curl/7.51.0\r\n\r\nAccept: */*\r\nContent-Length: 3\r\n\r\n'
    good_h2 = dict(
        method='POST',
        path='/',
        args={
            'Host': '127.0.0.1:8080',
            'User-Agent': 'curl/7.51.0',
            'Accept': '*/*',
            'Content-Length': '3',
        },
    )

    h1 = ohmygoogle.headers_by_str(t1)
    ensure(good_h1 == h1, 'headers str to dict error.')
    h2 = ohmygoogle.headers_by_str(t2)
    ensure(good_h2 == h2, 'headers str to dict error.')


def test_response_by_conn():
    data = 'HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=UTF-8\r\nContent-Length: 86400\r\n\r\n'
    print(ohmygoogle.headers_by_str(data))


# def test_headers_by_conn():
#     s = socket.socket()
#     s.bind(('127.0.0.1', 8080))
#     c = socket.socket()


# def test_chunked_length():
#     ...


def test_make_headers():
    headers = {
            'args':
            {
                    'accept-ranges': 'none',
                    'alt-svc': 'quic=":443"; ma=2592000; v="44,43,39,35"',
                    'cache-control': 'private, max-age=0',
                    'content-type': 'text/html; charset=UTF-8',
                    'date': 'Wed, 18 Jul 2018 03:20:22 GMT',
                    'expires': '-1',
                    'p3p': 'CP="This is not a P3P policy! See g.co/p3phelp for more '
                    'info."',
                    'server': 'gws',
                    'set-cookie': 'NID=134=zRHcflhENjEXFSK-M5qy5uaetfOHlZrT8NsKun9ZDyS0vTiSn7Eroc-XoNKRqQgSpyqyMl8KQo8nMj9odqskx6wth4cZQMjl-zzIU-yCy84CqI9DaVdJoii9pRmQD-1n; '
                    'expires=Thu, 17-Jan-2019 03:20:22 GMT; path=/; '
                    'domain=.google.com; HttpOnly',
                    'strict-transport-security': 'max-age=86400',
                    'transfer-encoding': 'chunked',
                    'vary': 'Accept-Encoding',
                    'x-frame-options': 'SAMEORIGIN',
                    'x-xss-protection': '1; mode=block'
            },
            'http_type': 'HTTP/1.1',
            'status_code': '200',
            'head_raw': 'HTTP/1.1 200 OK',
    }
    headers_str = http_utils.make_headers(headers)
    log(headers_str)


if __name__ == '__main__':
    # test_headers_by_str()
    # test_response_by_conn()
    test_make_headers()
