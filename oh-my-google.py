#!/usr/bin/env python3
# coding=utf-8

from gevent import monkey, spawn, queue  #, socket
monkey.patch_socket()
monkey.patch_ssl()
import gevent.queue as queue
import requests
import re
import json
from gevent.server import StreamServer
import logging

s = requests.session()
serv_q = queue.Queue()
logging.basicConfig(level=logging.DEBUG)


p = re.compile('onmousedown="return rwt.+?"')
pp = re.compile('onmousedown.+?return rwt\(.+?\).....')
host_p = re.compile('https*://.+?/')


def get_headers_str(resp):
    headers_list = [key + ': ' + value for key, value in resp.headers.items()]
    headers_head = 'HTTP/1.1 ' + str(resp.status_code) + ' OK'
    headers_str = '\r\n'.join([headers_head] + headers_list)
    return headers_str


def get_google():
    while True:
        url, headers, cli_q = serv_q.get()
        logging.debug(url)
        try:
            logging.debug('requests start')
            status_code = 503
            resp = None
            while status_code == 503:
                resp = s.get('https://www.google.com.hk{}'.format(url), headers=headers, timeout=3)
                logging.debug(resp.status_code)
                status_code = resp.status_code
        # except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, socket.timeout):
        except:
            cli_q.put(b'')
            continue
        resp_body = resp.content
        # print(resp.headers)
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
    for buf in iter(lambda: conn.recv(512), b''):
        logging.debug(buf)
        headers_raw += buf.decode('utf-8', errors='ignore')
        if '\r\n\r\n' in headers_raw:
            break
    headers_raw = re.sub('\r\n\r\n.+', '\r\n\r\n', headers_raw)
    return headers_raw


def get_headers(conn):
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
    return headers_dict


def handle(conn_cli, addr_cli):
    logging.debug(addr_cli)
    headers_dict = get_headers(conn_cli)
    if not headers_dict['method'] == 'GET':
        return
    else:
        host = headers_dict['Host']
        path = headers_dict['path']
        del headers_dict['Host']
        cli_q = queue.Queue()
        serv_q.put((path, headers_dict, cli_q))
        resp = cli_q.get()
        resp = resp.replace(b'www.google.com.hk', host.encode())
        conn_cli.sendall(resp)


def main(host, port, ssl_file=None):
    if ssl_file:
        certfile, keyfile = ssl_file
        StreamServer((host, port), handle=handle, keyfile=keyfile, certfile=certfile).serve_forever()
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
