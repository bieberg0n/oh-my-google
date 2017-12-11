#!/usr/bin/env python3
# coding=utf-8

from gevent import spawn
from gevent import ssl
# import time
import re
import json
from gevent.server import StreamServer
# from pprint import pprint
# import geventsocks
from utils import log
from http_utils import connect
# from http_utils import request
from http_utils import headers_by_conn
from http_utils import str_headers
from http_utils import response_by_conn
from cache import Cache


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


def modifier_headers(headers):
    headers = add_newwindow(headers)
    if headers['args'].get('Cookie'):
        headers['args']['Cookie'] = ''
    return headers


def request(s, google, headers):
    host = headers['args']['Host']
    headers['args']['Accept-Encoding'] = 'identity'
    sh = str_headers(headers)
    req_body = headers.get('body')
    _req_data = sh + req_body if req_body else sh
    req_data = _req_data.replace(host, google)
    # log('发送 data 给 google'), req_data)
    s.sendall(req_data.encode())

    resp = response_by_conn(s)
    # log('接收data')
    resp = resp.replace(google.encode(), '{}'.format(host).encode())
    return resp


def update_cache(headers, cache):
    # 发送headers到google
    s = connect(GOOGLE_HOST, PROXY_ADDR)
    r_raw = request(s, GOOGLE_HOST, headers)
    r = rm_redirect(r_raw)
    path = headers.get('path')
    user_agent = headers['args'].get('User-Agent')
    cache.write(path, user_agent, r)
    log('Update cache.')
    return r


def google(headers, cache, cli_addr):
    headers = modifier_headers(headers)
    path = headers['path']
    user_agent = headers['args'].get('User-Agent')
    data = cache.select(path, user_agent)
    # log('ua, data,', user_agent, data)

    if data:
        # log('命中缓存')
        resp = data['content']
        timeout = cache.timeout(path, user_agent)
        if timeout > TTL:
            spawn(update_cache, headers, cache)
        log(cli_addr,
            '[Length: {}]'.format(len(resp)),
            '[cache ttl: {}]'.format(TTL - timeout),
            path)
    else:
        resp = update_cache(headers, cache)
        log(cli_addr, '[Length: {}]'.format(len(resp)), path)

    return resp


def handle_func():
    cache = Cache()

    def handle(client, cli_addr):
        '''处理客户端请求'''
        # while True:
        # 获取客户端请求
        headers = headers_by_conn(client)
        if not headers or headers['method'] != 'GET':
            return
        else:
            r = google(headers, cache, cli_addr)
            client.sendall(r)
            # break
    return handle


def main(host, port, ssl_file=None):
    handle = handle_func()
    if ssl_file:
        certfile, keyfile = ssl_file
        StreamServer(
            (host, port),
            handle=handle,
            keyfile=keyfile,
            certfile=certfile,
            ssl_version=ssl.PROTOCOL_TLSv1_2
        ).serve_forever()
    else:
        StreamServer((host, port), handle=handle).serve_forever()


if __name__ == '__main__':
    GOOGLE_HOST = 'www.google.com'
    TTL = 3600

    p = re.compile(b'onmousedown="return rwt.+?"')
    pp = re.compile(b'onmousedown.+?return rwt\(.+?\).....')

    with open('ohmygoogle.json') as f:
        cfg = json.loads(f.read())
    log(cfg)
    if cfg['proxy']:
        # geventsocks.set_default_proxy(*PROXY_ADDR)
        PROXY_ADDR = ('127.0.0.1', 1080)
    if cfg['ssl']:
        ssl_file = (cfg['certfile'], cfg['keyfile'])
    else:
        ssl_file = None

    main(cfg['listen_ip'], cfg['listen_port'], ssl_file)
