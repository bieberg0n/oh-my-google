import sys
import time
from pprint import pprint


def log(*args):
    print(time.strftime('%Y-%m-%d %H:%M:%S'), *args)


def dbug(*args):
    if len(sys.argv) > 1:
        if len(args) == 1:
            pprint(args[0])
        else:
            print(*args)
