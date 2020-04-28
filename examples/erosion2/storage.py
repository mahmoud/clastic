import os
import shelve
import string
import time


_CHARS = sorted(string.ascii_lowercase + string.digits)
_N_CHARS = len(_CHARS)


def _encode_id(num):
    alias = ""
    n = abs(num)
    while n > 0:
        alias = _CHARS[n % _N_CHARS] + alias
        n //= len(_CHARS)
    return alias if alias else _CHARS[0]


class LinkDB:
    def __init__(self, db_path):
        self.db_path = db_path
        if not os.path.exists(self.db_path):
            with shelve.open(self.db_path, writeback=True) as db:
                db["last_id"] = 41660
                db["entries"] = {}

    def add_link(self, target_url, alias=None, expiry_time=0, max_count=0):
        with shelve.open(self.db_path, writeback=True) as db:
            next_id = db["last_id"] + 1
            if not alias:
                alias = _encode_id(next_id)
            if alias in db["entries"]:
                raise ValueError("alias already in use %r" % alias)
            now = time.time()
            entry = {
                "target": target_url,
                "alias": alias,
                "expires": now + expiry_time if expiry_time > 0 else 0,
                "max_count": max_count,
                "count": 0,
            }
            db["entries"][alias] = entry
            db["last_id"] = next_id
        return entry

    def get_links(self):
        with shelve.open(self.db_path, writeback=True) as db:
            entries = []
            for alias, entry in db["entries"].items():
                if entry is None:
                    continue
                if time.time() > entry["expires"] > 0:
                    db["entries"][alias] = None
                    continue
                entries.append(entry)
        return entries

    def use_link(self, alias):
        with shelve.open(self.db_path, writeback=True) as db:
            entry = db["entries"].get(alias)
            if entry is not None:
                entry["count"] += 1
                if entry["count"] >= entry["max_count"] > 0:
                    db["entries"][alias] = None
        return entry
