from gevent import spawn, queue, socket, ssl# monkey,
import requests
import re
import json
from gevent.server import StreamServer
import logging
from pprint import pprint
import geventsocks


GOOGLE_HOST = 'www.google.com'
# GOOGLE_HOST = 't66y.com'
MY_SITE = 'localhost'
PROXY_ADDR = ('127.0.0.1', 1080)


p = re.compile(b'onmousedown="return rwt.+?"')
pp = re.compile(b'onmousedown.+?return rwt\(.+?\).....')
chunk = re.compile(b'\r\n[0-9a-f]{1,4}\r\n')


def log(*args, **kwargs):
    print(*args)
    # [pprint(arg) for arg in args]


def transport(a, b, modifier, mark='req'):
    try:
        for buf in iter(lambda: a.recv(1024*16), b''):
            if buf.startswith(b'POST'):
                a.close()
                return
            else:
                buf = modifier(buf)
                b.sendall(buf)
    except OSError:
        log('connect close.', mark)
        b.sendall(b'')


def modifier_req(data):
    # data = data.replace('//{}/'.format(MY_SITE).encode(),
    #                     '//{}/'.format(GOOGLE_HOST).encode())
    data = data.replace(MY_SITE.encode(), GOOGLE_HOST.encode())\
               .replace(b'Connection: keep-alive', b'Connection: closed')
    data = re.sub(b'Accept-Encoding: .*\r\n', b'Accept-Encoding: identity\r\n', data)
    log(data)
    return data


def modifier_host(data):
    data = data.replace(GOOGLE_HOST.encode(), MY_SITE.encode())
    return data


def modifier_resp(data):
    # log(data)
    data = data.replace(GOOGLE_HOST.encode(), MY_SITE.encode())\
               .replace(b'Transfer-Encoding: chunked\r\n', b'')
               # .replace(b'0\r\n\r\n', b'')
    data = re.sub(b'\r\n\r\n[0-9a-f]{1,4}\r\n', b'\r\n\r\n', data)
    data = re.sub(chunk, b'', data)
    # log(data)
    return data


def serv_to_cli(serv, cli):
    data = b''
    for buf in iter(lambda: serv.recv(1024*16), b''):
        data += buf
        if b'\r\nContent-Length: ' in data[:1024]:
            cli.sendall(data)
            transport(serv, cli, modifier_host, mark='resp')
            return
        elif data.endswith(b'0\r\n\r\n'):
            break
    data = modifier_resp(data)
    log('response: ', data.decode('utf-8', errors='ignore')[:1024])
    cli.sendall(data)


def copy(cli, serv):
    g = spawn(transport, cli, serv, modifier_req)
    # transport(serv, cli, modifier_resp)
    serv_to_cli(serv, cli)
    g.kill()
    # serv.close()
    # cli.close()
    log('copy over.')


def handle(client, cli_addr):
    '''处理客户端请求'''
    log(cli_addr)

    _s = socket.socket()
    geventsocks.connect(_s, (GOOGLE_HOST, 443))
    s = ssl.wrap_socket(_s)

    copy(client, s)
    s.close()
    _s.close()
    client.close()
    log('close all.')


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
    if cfg['ssl']:
        ssl_file = (cfg['certfile'], cfg['keyfile'])
    else:
        ssl_file = None

    main(cfg['listen_ip'], cfg['listen_port'], ssl_file)
