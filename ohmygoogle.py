#!/usr/bin/env python3
# coding=utf-8

from gevent import spawn
from gevent import ssl
import re
import json
from gevent.server import StreamServer
from utils import (
    log,
    dbug,
)
from http_utils import (
    connect,
    headers_by_conn,
    str_headers,
    response_by_conn,
    make_headers,
)
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
    host = headers['args']['host']
    headers['args']['accept-encoding'] = 'identity'
    sh = str_headers(headers)
    req_body = headers.get('body')
    _req_data = sh + req_body if req_body else sh
    req_data = _req_data.replace(host, google)
    # log('发送 data 给 google', req_data)
    s.sendall(req_data.encode())

    # log('接收data')
    h, body = response_by_conn(s)
    body = body.replace('https://{}'.format(google).encode(), cfg['url'].encode())
    body = rm_redirect(body)
    h['args']['content-length'] = str(len(body))
    h_bytes = make_headers(h).encode()
    dbug('header length:', len(h_bytes))
    dbug('body length:', len(body))

    resp = h_bytes + body
    return resp


def update_cache(headers, cache):
    # 发送headers到google
    s = connect(GOOGLE_HOST, PROXY_ADDR)
    r = request(s, GOOGLE_HOST, headers)

    path = headers.get('path')
    user_agent = headers['args'].get('user-agent')
    cache.write(path, user_agent, r)
    log('Update cache.')
    return r


def is_spider_req(user_agent):
    spider_bot = ('bot', 'Bot', 'spider', 'Spider')
    return [i for i in spider_bot if i in user_agent] != []


def google(headers, cache, cli_addr):
    headers = modifier_headers(headers)
    path = headers['path']
    user_agent = headers['args'].get('user-agent', '')

    if is_spider_req(user_agent):
        return b'HTTP/1.1 403 Forbidden\r\n\r\n'

    else:
        data = cache.select(path, user_agent)
        if data:
            # log('命中缓存')
            resp = data['content']
            timeout = cache.timeout(path, user_agent)
            if timeout > TTL:
                spawn(update_cache, headers, cache)
            log('{} [Length: {}] [cache ttl: {}] {} ({})'.format(
                    cli_addr,
                    len(resp),
                    TTL - timeout,
                    path,
                    user_agent))
        else:
            resp = update_cache(headers, cache)
            log('{} [Length: {}] {} ({})'.format(cli_addr, len(resp),
                                                 path, user_agent))

        return resp


def handle_func():
    cache = Cache()

    def handle(client, cli_addr):
        '''处理客户端请求'''
        # 获取客户端请求
        headers = headers_by_conn(client)
        if not headers or headers['method'] != 'GET':
            r = b'HTTP/1.1 204 OK\r\n\r\n'
        else:
            r = google(headers, cache, cli_addr)
        client.sendall(r)
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
        PROXY_ADDR = ('127.0.0.1', 1080)
    else:
        PROXY_ADDR = None
    if cfg['ssl']:
        ssl_file = (cfg['certfile'], cfg['keyfile'])
    else:
        ssl_file = None

    main(cfg['listen_ip'], cfg['listen_port'], ssl_file)
