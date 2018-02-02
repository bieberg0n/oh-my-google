from gevent import socket
from gevent import ssl
import geventsocks
from utils import log


def connect(host, proxy=None):
    _s = socket.socket()
    if proxy:
        geventsocks.set_default_proxy(*proxy)
    geventsocks.connect(_s, (host, 443))
    s = ssl.wrap_socket(_s)
    return s


def headers_raw(conn):
    headers_raw = ''
    for buf in iter(lambda: conn.recv(1024), b''):
        headers_raw += buf.decode('utf-8')
        if '\r\n\r\n' in headers_raw:
            break
    return headers_raw


def headers_by_str(str_headers):
    '''string格式的headers转成dict'''
    headers = dict(
        args={}
    )
    headers_lines = str_headers.split('\r\n')
    headers_head = headers_lines[0].split(' ')
    if len(headers_head) >= 2:
        headers['method'], headers['path'] = headers_head[:2]
    else:
        pass
    for line in headers_lines[1:]:
        if line:
            try:
                key, value = line.split(': ')[:2]
            except ValueError as e:
                log(e, line)
                continue
            else:
                headers['args'][key.lower()] = value
    return headers


def headers_by_conn(conn):
    '''在conn中获取headers并转成dict'''
    str_headers = headers_raw(conn)
    if not str_headers:
        return
    else:
        headers = headers_by_str(str_headers)
        if headers['method'] == 'POST':
            content_len = int(headers['args']['content-length'])
            current_len = len(str_headers.split('\r\n\r\n')[1])
            need_recv_len = content_len - current_len
            headers['body'] = conn.recv(need_recv_len).decode()
    return headers


def str_headers(headers):
    '''header 转成 string 格式'''
    first_line = '{} {} HTTP/1.1\r\n'.format(headers['method'],
                                             headers['path'])
    other_line = ''.join(['{}: {}\r\n'.format(k.title(), w)
                          for k, w in headers['args'].items()])
    return first_line + other_line + '\r\n'


def chunked_length(conn):
    data = b''
    for buf in iter(lambda: conn.recv(1), b''):
        # log(buf)
        data += buf
        if data.endswith(b'\r\n'):
            break
    _length = data.rstrip(b'\r\n')
    if _length:
        length = int(_length, 16)
        # log(length)
        return length
    else:
        return 0


def recv(conn, length):
    data = b''
    while length > 0:
        buf = conn.recv(length)
        if buf:
            data += buf
            length -= len(buf)
        else:
            break
    # log('实际长度', len(data))
    return data.rstrip(b'\r\n')


def response_by_chunked(conn):
    data = b''
    while True:
        ck_length = chunked_length(conn)
        if ck_length:
            data += recv(conn, ck_length+2)
            # log(ck_length, len(data))
        else:
            break
    return data


def response_by_conn(conn):
    '''从 conn 获取 response'''
    # 获取headers
    sh = []
    while len(sh) <= 4 or sh[-4:] != ['\r', '\n', '\r', '\n']:
        char = conn.recv(1).decode()
        sh.append(char)
    sh = ''.join(sh)
    h = headers_by_str(sh)
    # log('resp headers: ', h)

    # 获取body
    transfer_encoding = h['args'].get('transfer-encoding')
    content_length = int(h['args'].get('content-length', 0))
    resp_body = b''
    if transfer_encoding == 'chunked':
        resp_body = response_by_chunked(conn)
        sh = sh.replace('chunked', '')

    elif content_length != 0:
        for buf in iter(lambda: conn.recv(1024*16), b''):
            resp_body += buf
            if len(resp_body) >= content_length:
                break

    else:
        for buf in iter(lambda: conn.recv(1024*16), b''):
            resp_body += buf

    return sh.encode() + resp_body
