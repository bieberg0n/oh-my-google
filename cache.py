import time


class Cache():
    def __init__(self):
        self.cache = {}

    def select(self, path, user_agent):
        path = self.cache.get(path)
        if path:
            return path.get(user_agent)
        else:
            return None

    def write(self, path, user_agent, content):
        now = int(time.time())
        ua = dict(
            content=content,
            time=now,
        )
        if self.cache.get(path):
            self.cache[path][user_agent] = ua
        else:
            self.cache[path] = {
                user_agent: ua
            }

    def timeout(self, path, user_agent):
        t = self.cache[path][user_agent]['time']
        now = int(time.time())
        return now - t
