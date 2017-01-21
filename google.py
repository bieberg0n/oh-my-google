import queue
import requests
import threading
import re
import json
# import socks
from flask import Flask, request

app = Flask(__name__)
s = requests.session()
# s.headers['User-Agent'] = 'Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36'
serv_q = queue.Queue()


p = re.compile('onmousedown="return rwt.+?"')
pp = re.compile('onmousedown.+?return rwt\(.+?\).....')
host_p = re.compile('http://.+?/')


def get_google():
    while True:
        url, headers, cli_q = serv_q.get()
        print(url)
        # print(s.headers)
        # s.headers = headers
        # print(s.headers)
        resp = s.get('https://www.google.com.hk/{}'.format(url), headers=headers).content
        if b'onmouse' in resp:
            resp = resp.decode()
            resp = p.sub('',resp)
            resp = pp.sub('',resp).encode()
        cli_q.put(resp)


def get_headers(request):
    url = host_p.sub('', request.url)
    # print(type(request.headers))
    headers = {key: request.headers[key] for key in request.headers.keys()}
    # get_headers(request.headers)
    del headers['Host'], headers['Content-Length']
    # print(headers)
    return url, headers


@app.route('/<path:path>', methods=['GET'])
def google_q(path):
    # return get_google()
    # return get_google(path)
    # print(dir(request))
    url, headers = get_headers(request)
    cli_q = queue.Queue()
    serv_q.put((url, headers, cli_q))
    return cli_q.get()


@app.route('/', methods=['GET'])
def google():
    url, headers = get_headers(request)
    cli_q = queue.Queue()
    serv_q.put((url, headers, cli_q))
    return cli_q.get()


def main(host, port, debug=False):
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    with open('oh-my-google.json') as f:
        cfg = json.loads(f.read())
    threading.Thread(target=get_google).start()
    if cfg['proxy']:
        s.proxies = {'http': 'socks5://192.168.1.1:1080',
                     'https': 'socks5://192.168.1.1:1080'}
    main(cfg['listen_ip'], cfg['listen_port'], cfg['debug'])
