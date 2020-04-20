import shelve


class LinkDB:
    def __init__(self, db_path):
        self.db_path = db_path

    def get_links(self):
        with shelve.open(self.db_path) as db:
            entries = list(db.values())
        return entries

    def get_link(self, alias):
        with shelve.open(self.db_path) as db:
            entry = db.get(alias)
        return entry

    def add_link(self, *, target_url, alias, expiry_time, max_count):
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
