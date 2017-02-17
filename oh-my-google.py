#!/usr/bin/env python3
# coding=utf-8

from gevent import monkey, spawn, queue
monkey.patch_socket()
monkey.patch_ssl()
# import queue
import requests
import threading
import re
import json
# import socks
# from flask import Flask, request
# from gevent.wsgi import WSGIServer
from gevent.server import StreamServer

# app = Flask(__name__)
s = requests.session()
# s.headers['User-Agent'] = 'Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36'
serv_q = queue.Queue()


p = re.compile('onmousedown="return rwt.+?"')
pp = re.compile('onmousedown.+?return rwt\(.+?\).....')
host_p = re.compile('https*://.+?/')


def get_headers_str(resp):
    headers_list = [key + ': ' + value for key, value in resp.headers.items()]
    # headers_str = '\r\n'.join(headers_list)
    headers_head = 'HTTP/1.1 ' + str(resp.status_code) + ' OK'
    headers_str = '\r\n'.join([headers_head] + headers_list)
    return headers_str


def get_google():
    while True:
        url, headers, cli_q = serv_q.get()
        print(url)
        # print(s.headers)
        # s.headers = headers
        # print(s.headers)
        try:
            resp = s.get('https://www.google.com.hk{}'.format(url), headers=headers, timeout=3)
            # resp_headers_str = resp_headers_str.replace('gzip', '')\
            #                                    .replace('chunked', '')\
            #                                    .encode()
        except requests.exceptions.ConnectionError:
            cli_q.put(b'')
            continue
        resp_body = resp.content
        print(resp.headers)
        resp_headers_str = get_headers_str(resp).replace('gzip', '')\
                                                .replace('chunked', '')\
                                                .encode()
        if b'onmouse' in resp_body:
            resp_body = resp_body.decode('utf-8', errors='ignore')
            resp_body = p.sub('',resp_body)
            resp_body = pp.sub('',resp_body).encode()
        cli_q.put(resp_headers_str + b'\r\n\r\n' + resp_body)


def get_headers_raw(conn):
    headers_raw = ''
    # for buf in iter(lambda: conn.recv(1), b''):
    while not headers_raw.endswith('\r\n\r\n'):
        buf = conn.recv(1)
        headers_raw += buf.decode('utf-8', errors='ignore')
    return headers_raw


def get_headers(conn):
    # url = host_p.sub('', request.url)
    # print(type(request.headers))
    headers_raw = get_headers_raw(conn)
    headers_dict = dict()
    headers_lines = headers_raw.split('\r\n')
    headers_head = headers_lines[0]
    headers_dict['method'], headers_dict['path'], _ = headers_head.split(' ')
    for line in headers_lines[1:]:
        if line:
            key, value = line.split(': ')
            headers_dict[key] = value
        else:
            pass
    # headers = {key: headers_raw[key] for key in request.headers.keys()}
    # get_headers(request.headers)
    # del headers['Host'], headers['Content-Length']
    # print(headers)
    return headers_dict


def handle(conn_cli, addr_cli):
    # print(addr_cli)
    headers_dict = get_headers(conn_cli)
    # print(headers_dict)
    if not headers_dict['method'] == 'GET':
        return
    else:
        host = headers_dict['Host']
        path = headers_dict['path']
        del headers_dict['Host']
        cli_q = queue.Queue()
        serv_q.put((path, headers_dict, cli_q))
        resp = cli_q.get()
        print(resp[:2000])
        conn_cli.sendall(resp)
    # print(conn_cli.recv(1024))


def main(host, port, ssl_file=None):
    # if debug:
    #     app.run(host=host, port=port, debug=debug,
    #             ssl_context=ssl_file, threaded=True)
    # else:
    if ssl_file:
        certfile, keyfile = ssl_file
        # WSGIServer((host, port), keyfile=keyfile, certfile=certfile).serve_forever()
    else:
        StreamServer((host, port), handle=handle).serve_forever()


if __name__ == '__main__':
    with open('oh-my-google.json') as f:
        cfg = json.loads(f.read())
    if cfg['proxy']:
        s.proxies = {'http': 'socks5://192.168.233.2:1080',
                     'https': 'socks5://192.168.233.2:1080'}
    if cfg['ssl']:
        # if cfg['keyfile']:
        ssl_file = (cfg['certfile'], cfg['keyfile'])
        # else:
        #     ssl_file = 'adhoc'
    else:
        ssl_file = None

    # threading.Thread(target=get_google).start()
    spawn(get_google)
    main(cfg['listen_ip'], cfg['listen_port'], ssl_file)
