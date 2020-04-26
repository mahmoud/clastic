import shelve
import time


def _is_expired(entry):
    expired_time = time.time() > entry["expires"] > 0
    expired_clicks = entry["count"] >= entry["max_count"] > 0
    return expired_time or expired_clicks



class LinkDB:
    def __init__(self, db_path):
        self.db_path = db_path

    def add_link(self, target_url, alias=None, *, expiry_time=0, max_count=0):
        entry = {
            "target": target_url,
            "alias": alias,
            "expires": time.time() + expiry_time if expiry_time > 0 else 0,
            "max_count": max_count,
            "count": 0,
        }
        with shelve.open(self.db_path) as db:
            db[alias] = entry
        return entry

    def get_links(self):
        with shelve.open(self.db_path) as db:
            entries = [link for link in db.values() if not _is_expired(link)]
        return entries

    def use_link(self, alias):
        with shelve.open(self.db_path, writeback=True) as db:
            entry = db.get(alias)
            if entry is not None:
                entry["count"] += 1
                db.sync()
        return entry
