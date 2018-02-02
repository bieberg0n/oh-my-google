import time
from pprint import pprint


def log(*args, **kwargs):
    # if len(args) == 1:
    #     pprint(args[0])
    # else:
    print(time.strftime('%Y-%m-%d %H:%M:%S'), *args)
