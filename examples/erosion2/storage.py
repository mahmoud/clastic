import operator
import shelve
import string
import time


_CHARS = sorted(string.ascii_lowercase + string.digits)
_N_CHARS = len(_CHARS)


def _encode_id(num):
    alias = ""
    while num:
        alias = _CHARS[num % _N_CHARS] + alias
        num //= len(_CHARS)
    return alias if alias else _CHARS[0]


def _is_expired(entry):
    expired_time = time.time() > entry["expires"] > 0
    expired_clicks = entry["count"] >= entry["max_count"] > 0
    return expired_time or expired_clicks


class LinkDB:
    def __init__(self, db_path):
        self.db_path = db_path

    def add_link(self, target_url, alias=None, *, expiry_time=0, max_count=0):
        with shelve.open(self.db_path) as db:
            next_id = db.get("__last__", {}).get("link_id", 41660) + 1
            if not alias:
                alias = _encode_id(next_id)
            if alias in db:
                raise ValueError("alias already in use %r" % alias)
            now = time.time()
            entry = {
                "link_id": next_id,
                "target": target_url,
                "alias": alias,
                "expires": now + expiry_time if expiry_time > 0 else 0,
                "max_count": max_count,
                "count": 0,
            }
            db[alias] = entry
            db["__last__"] = {**entry, "expires": now}
        return entry

    def get_links(self):
        with shelve.open(self.db_path) as db:
            entries = [link for link in db.values() if not _is_expired(link)]
        return sorted(entries, key=operator.itemgetter("link_id"), reverse=True)

    def use_link(self, alias):
        with shelve.open(self.db_path, writeback=True) as db:
            entry = db.get(alias)
            if entry is not None:
                entry["count"] += 1
                db.sync()
        return entry
