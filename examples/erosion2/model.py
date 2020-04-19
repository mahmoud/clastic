import shelve


class LinkDB:
    def __init__(self, db_path):
        self.db_path = db_path

    def get_links(self):
        with shelve.open(self.db_path) as db:
            return db.values()
