import tempfile
import unittest
from pathlib import Path

import storage


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test.db"
        storage.init_db(self.db_path)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_create_user_unique_email(self):
        user = storage.create_user("a@example.com", "secret", self.db_path)
        self.assertIsNotNone(user)
        duplicate = storage.create_user("a@example.com", "secret2", self.db_path)
        self.assertIsNone(duplicate)

    def test_authenticate_user(self):
        storage.create_user("b@example.com", "secret", self.db_path)
        ok = storage.authenticate_user("b@example.com", "secret", self.db_path)
        bad = storage.authenticate_user("b@example.com", "wrong", self.db_path)
        self.assertIsNotNone(ok)
        self.assertIsNone(bad)

    def test_event_logging_is_scoped(self):
        user_a = storage.create_user("a2@example.com", "secret", self.db_path)
        user_b = storage.create_user("b2@example.com", "secret", self.db_path)
        storage.log_event(user_a["id"], "search", {"mood": "cozy"}, self.db_path)
        storage.log_event(user_b["id"], "search", {"mood": "thrill"}, self.db_path)
        storage.log_event(user_a["id"], "feedback", {"tmdb_id": 1}, self.db_path)

        history_a = storage.get_user_history(user_a["id"], db_path=self.db_path)
        history_b = storage.get_user_history(user_b["id"], db_path=self.db_path)

        self.assertEqual(len(history_a), 2)
        self.assertEqual(len(history_b), 1)
        self.assertEqual(history_b[0]["payload"]["mood"], "thrill")


if __name__ == "__main__":
    unittest.main()
