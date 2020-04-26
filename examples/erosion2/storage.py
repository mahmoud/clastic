import shelve


class LinkDB:
    def __init__(self, db_path):
        self.db_path = db_path

    def add_link(self, alias=None, *, target_url, expiry_time, max_count):
        entry = {
            "target": target_url,
            "alias": alias,
            "expiry_time": expiry_time,
            "max_count": max_count,
            "count": 0,
        }
        with shelve.open(self.db_path) as db:
            db[alias] = entry
        return entry

    def get_links(self):
        with shelve.open(self.db_path) as db:
            entries = [link for link in db.values() if link is not None]
        return entries

    def use_link(self, alias):
        with shelve.open(self.db_path, writeback=True) as db:
            entry = db.get(alias)
            if entry is not None:
                entry["count"] += 1
                if entry["count"] >= entry["max_count"]:
                    db[alias] = None
                db.sync()
        return entry
