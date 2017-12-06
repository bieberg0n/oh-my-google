#!/usr/bin/env python3
# coding=utf-8

from gevent import socket, ssl  # spawn, queue,   # monkey,
import time
import re
import json
from gevent.server import StreamServer
# import logging
from pprint import pprint
import geventsocks

GOOGLE_HOST = 'www.google.com'
PROXY_ADDR = ('127.0.0.1', 1080)


p = re.compile(b'onmousedown="return rwt.+?"')
pp = re.compile(b'onmousedown.+?return rwt\(.+?\).....')


def log(*args, **kwargs):
    if len(args) == 1:
        pprint(args[0])
    else:
        print(time.strftime('%Y-%m-%d %H:%M:%S'), *args)


def connect_google():
    _s = socket.socket()
    geventsocks.connect(_s, (GOOGLE_HOST, 443))
    s = ssl.wrap_socket(_s)
    return s


def headers_raw(conn):
    headers_raw = ''
    for buf in iter(lambda: conn.recv(1024), b''):
        headers_raw += buf.decode('utf-8')  # , errors='ignore')
        # if headers_raw.endswith('\r\n\r\n'):
        if '\r\n\r\n' in headers_raw:
            break
    # headers_raw = re.sub('\r\n\r\n.+', '\r\n\r\n', headers_raw)
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
            # log(line)
            key, value = line.split(': ')[:2]
            headers['args'][key] = value
        else:
            pass
    return headers


def headers_by_conn(conn):
    '''在conn中获取headers并转成dict'''
    str_headers = headers_raw(conn)
    if not str_headers:
        return
    else:
        headers = headers_by_str(str_headers)
        if headers['method'] == 'POST':
            content_len = int(headers['args']['Content-Length'])
            current_len = len(str_headers.split('\r\n\r\n')[1])
            need_recv_len = content_len - current_len
            headers['body'] = conn.recv(need_recv_len).decode()
    return headers


def str_headers(headers):
    '''header 转成 string 格式'''
    first_line = '{} {} HTTP/1.1\r\n'.format(headers['method'],
                                             headers['path'])
    other_line = ''.join(['{}: {}\r\n'.format(k, w)
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
    # log('resp headers: ', h['args'])

    # 获取body
    transfer_encoding = h['args'].get('Transfer-Encoding')
    resp_body = b''
    if transfer_encoding == 'chunked':
        resp_body = response_by_chunked(conn)
        sh = sh.replace('chunked', '')
        # sh = sh.replace('Transfer-Encoding: chunked',
        #                 'Content-Length: {}\r\nAccept-Encoding: identity'\
        # .format(len(resp_body)))
        # sh = sh.replace('gzip', 'identity')
    else:
        content_length = int(h['args'].get('Content-Length'))
        for buf in iter(lambda: conn.recv(1024*16), b''):
            resp_body += buf
            if len(resp_body) >= content_length:
                break

    # return b''.join(sh)
    return sh.encode() + resp_body


def request(s, headers):
    host = headers['args']['Host']
    headers['args']['Accept-Encoding'] = 'identity'
    sh = str_headers(headers)
    req_body = headers.get('body')
    _req_data = sh + req_body if req_body else sh
    req_data = _req_data.replace(host, GOOGLE_HOST)
    # log('发送 data 给 google'), req_data)
    s.sendall(req_data.encode())

    resp = response_by_conn(s)
    # log('接收data')
    resp = resp.replace(GOOGLE_HOST.encode(), '{}'.format(host).encode())
    return resp


def add_newwindow(headers):
    path = headers['path']
    if path.startswith('/search') and 'newwindow' not in path:
        new_path = path.replace('?', '?newwindow=1&')
        headers['path'] = new_path
    return headers


def rm_redirect(r):
    r = p.sub(b'', r)
    r = pp.sub(b'', r)
    return r


def path_timeout(cache, path):
    query_time = cache[path]['querytime']
    now = int(time.time())
    return now - query_time


def in_cache(cache, path):
    ttl = 3600
    if path in cache:
        return path_timeout(cache, path) <= ttl
    else:
        return False


def write_cache(cache, path, content):
    now = int(time.time())
    cache[path] = dict(
        content=content,
        querytime=now,
    )


def modifier_headers(headers):
    headers = add_newwindow(headers)
    if headers['args'].get('Cookie'):
        headers['args']['Cookie'] = ''
    return headers


def handle_func():
    cache = {}

    def handle(client, cli_addr):
        '''处理客户端请求'''
        # log(cli_addr)

        while True:
            # 获取客户端请求
            headers = headers_by_conn(client)
            if not headers or headers['method'] != 'GET':
                return
            else:
                headers = modifier_headers(headers)
                # log(headers)

                path = headers['path']
                if in_cache(cache, path):
                    r = cache[path]['content']
                    ttl = 3600 - path_timeout(cache, path)
                    # log('命中缓存')
                    log(cli_addr,
                        '[Length: {}]'.format(len(r)),
                        '[cache ttl: {}]'.format(ttl),
                        path)
                else:
                    # 发送headers到google
                    s = connect_google()
                    r_raw = request(s, headers)
                    r = rm_redirect(r_raw)
                    write_cache(cache, path, r)
                    log(cli_addr, '[Length: {}]'.format(len(r)), path)

                # log('r大小', len(r), r[:1024])
                client.sendall(r)
                break
    return handle


def main(host, port, ssl_file=None):
    handle = handle_func()
    if ssl_file:
        certfile, keyfile = ssl_file
        StreamServer((host, port), handle=handle,
                     keyfile=keyfile, certfile=certfile).serve_forever()
    else:
        StreamServer((host, port), handle=handle).serve_forever()


if __name__ == '__main__':
    with open('oh-my-google.json') as f:
        cfg = json.loads(f.read())
    log(cfg)
    if cfg['proxy']:
        geventsocks.set_default_proxy(*PROXY_ADDR)
        # s.proxies = {'http': 'socks5://127.0.0.1:1080',
        #              'https': 'socks5://127.0.0.1:1080'}
    if cfg['ssl']:
        ssl_file = (cfg['certfile'], cfg['keyfile'])
    else:
        ssl_file = None

    # spawn(get_google)
    main(cfg['listen_ip'], cfg['listen_port'], ssl_file)
