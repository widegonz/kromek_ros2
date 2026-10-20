import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src' / 'kromek_driver'))
from kromek_driver.recovery import retry_delay, cpu_percentage


class TestRecovery(unittest.TestCase):
    def test_backoff(self):
        self.assertEqual([retry_delay(i) for i in range(1, 7)],
                         [2, 4, 8, 16, 30, 30])

    def test_invalid_params(self):
        with self.assertRaises(ValueError):
            retry_delay(0)
        with self.assertRaises(ValueError):
            cpu_percentage(1, 0)

    def test_cpu(self):
        self.assertEqual(cpu_percentage(3.14, 2.0), 157.0)


if __name__ == '__main__':
    unittest.main()
