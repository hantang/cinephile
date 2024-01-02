import unittest
import pendulum

from cinephile.utils import datetimes


class TestDatetime(unittest.TestCase):
    def test_now(self):
        dt1 = datetimes.utcnow()
        dt2 = datetimes.now()
        dt3 = datetimes.bjnow()

        self.assertEqual(0, dt2.diff(dt1).in_hours())
        self.assertEqual(0, dt3.diff(dt1).in_hours())

    def test_time2str(self):
        result = {
            0: "2023-07-26 12:23:44",
            1: "2023-07-26T12:23:44+0800",
            2: "2023-07-26",
            3: "20230726",
        }
        dt = pendulum.parse(result[1])
        for i in range(4):
            self.assertEqual(datetimes.time2str(dt, i), result[i])

    def test_time2zh(self):
        date = "2023-07-26T12:23:44+0800"
        dt = pendulum.parse(date)
        result = "二〇二三年七月二十六日（星期三）12:23:44 +0800"
        self.assertEqual(datetimes.time2zh(dt), result)


if __name__ == "__main__":
    unittest.main()
