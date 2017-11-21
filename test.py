import ohmygoogle
import socket


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



def test_headers_by_conn():
    s = socket.socket()
    s.bind(('127.0.0.1', 8080))
    c = socket.socket()
    # TODO


def test_chunked_length():
    pass


if __name__ == '__main__':
    # test_headers_by_str()
    test_response_by_conn()
