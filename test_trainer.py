import sys
import time
import unittest

from trainer import ArenaLab


@unittest.skipUnless(sys.platform == "win32", "requires Windows")
class TrainerIntegrationTest(unittest.TestCase):
    def test_scan_freeze_and_disable(self):
        with ArenaLab() as lab:
            self.assertEqual(lab.find_health()[0], 3)
            self.assertIn("HP  87", lab.exchange("status"))
            self.assertIn("HP  52", lab.exchange("fire"))
            lab.start_freeze()
            lab.exchange("hit")
            deadline = time.monotonic() + 2
            status = lab.exchange("status")
            while "HP 100" not in status and time.monotonic() < deadline:
                time.sleep(0.03)
                status = lab.exchange("status")
            self.assertIn("HP 100", status)
            lab.stop_freeze()
            self.assertIn("HP  87", lab.exchange("hit"))
            self.assertIn("HP  87", lab.exchange("status"))


if __name__ == "__main__":
    unittest.main()
