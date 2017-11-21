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
    # print(*args)
    [pprint(arg) for arg in args]


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
    headers = dict(
        args={}
    )
    headers_lines = str_headers.split('\r\n')
    headers_head = headers_lines[0]
    headers['method'], headers['path'], _ = headers_head.split(' ')
    for line in headers_lines[1:]:
        if line:
            key, value = line.split(': ')
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
            headers['body'] = conn.recv(int(headers['args']['Content-Length']))
    return headers


def str_headers(headers):
    # custom_key = ['method', 'path']
    first_line = '{} {} HTTP/1.1\r\n'.format(headers['method'],
                                             headers['path'])
    other_line = ''.join(['{}: {}\r\n'.format(k, w)
                          for k, w in headers['args'].items()])
    return first_line + other_line + '\r\n'


def response_by_conn(conn):
    sh = b''
    # while len(sh) <= 4 or sh[-4:] != ['\r', '\n', '\r', '\n']:
    #     char = conn.recv(1).decode()
    #     sh.append(char)
    # log(''.join(sh))

    # while (not sh.endswith(b'0\r\n\r\n')) and buf:
    for buf in iter(lambda: conn.recv(1024*16), b''):
        # length = int(conn.recv(4).decode())
        # log(buf)
        # sh.append(buf)
        sh += buf
        if sh.endswith(b'\r\n\r\n'):
            break

    # return b''.join(sh)
    return sh


def request(s, headers):
    headers['args']['Accept-Encoding'] = ''
    headers['args']['Host'] = GOOGLE_HOST
    sh = str_headers(headers)
    req_body = headers.get('body')
    req_data = sh + req_body if req_body else sh
    log('发送data给google', req_data)
    s.sendall(req_data.encode())
    resp = response_by_conn(s)
    log('接收data')
    # if b'onmouse' in resp:
    #     resp = p.sub(b'', resp)
    #     resp = pp.sub(b'',resp)
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
    proxy_addr = ('127.0.0.1', 1080)

    log(cli_addr)

    _s = socket.socket()
    geventsocks.connect(_s, (GOOGLE_HOST, 443))
    s = ssl.wrap_socket(_s)

    while True:
        # 获取客户端请求
        headers = headers_by_conn(client)
        if not headers:
            return
        else:
            log(headers)
            host, _ = headers['args']['Host'], headers['path']
            # 发送headers到google
            r = request(s, headers)
            r.replace(GOOGLE_HOST.encode(), host.encode())
            log(r[:1024])
            client.sendall(r)
            s.close()
            client.close()
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
    log('Config:', cfg)
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
