#!/usr/bin/env python3
# coding=utf-8

from gevent import spawn, queue, socket, ssl# monkey,
import requests
import re
import json
from gevent.server import StreamServer
import logging
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
        print(*args)


def get_headers_raw(conn):
    headers_raw = ''
    for buf in iter(lambda: conn.recv(1), b''):
        headers_raw += buf.decode('utf-8', errors='ignore')
        # if '\r\n\r\n' in headers_raw:
        if headers_raw.endswith('\r\n\r\n'):
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
            log(line)
            key, value = line.split(': ')[:2]
            headers['args'][key] = value
        else:
            pass
    return headers


def headers_by_conn(conn):
    '''在conn中获取headers并转成dict'''
    str_headers = get_headers_raw(conn)
    if not str_headers:
        return
    else:
        headers = headers_by_str(str_headers)
        if headers['method'] == 'POST':
            headers['body'] = conn.recv(int(headers['args']['Content-Length'])).decode()
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
    log('resp headers: ', h['args'])

    # 获取body
    transfer_encoding = h['args'].get('Transfer-Encoding')
    resp_body = b''
    if transfer_encoding == 'chunked':
        resp_body = response_by_chunked(conn)
        sh = sh.replace('chunked', '')
        # sh = sh.replace('Transfer-Encoding: chunked',
        #                 'Content-Length: {}\r\nAccept-Encoding: identity'.format(len(resp_body)))
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
    log('发送 data 给 google', req_data)
    s.sendall(req_data.encode())

    resp = response_by_conn(s)
    log('接收data')
    # if b'onmouse' in resp:
    #     resp = p.sub(b'', resp)
    #     resp = pp.sub(b'',resp)
    resp = resp.replace(GOOGLE_HOST.encode(), '{}'.format(host).encode())
    return resp


# def sendall(client, data):
#     size1, size2 = 0, 1024
#     while True:
#         if size2 > len(data):
#             client.sendall(data[size1:])
#             break
#         else:
#             client.sendall(data[size1:size2])
#         size1, size2 = size2, size2 + 1024


def handle(client, cli_addr):
    '''处理客户端请求'''
    log(cli_addr)

    _s = socket.socket()
    geventsocks.connect(_s, (GOOGLE_HOST, 443))
    s = ssl.wrap_socket(_s)

    while True:
        # 获取客户端请求
        headers = headers_by_conn(client)
        if not headers or headers['method'] != 'GET':
            return
        else:
            log(headers)
            # host, _ = headers['args']['Host'], headers['path']
            # 发送headers到google
            r = request(s, headers)
            r = p.sub(b'', r)
            r = pp.sub(b'', r)
            log('r大小', len(r), r[:1024])
            client.sendall(r)
            # s.close()
            # client.close()
            break


def main(host, port, ssl_file=None):
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
