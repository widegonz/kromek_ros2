import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from compare_acquisitions import compare
from run_park_reference import make_configured_copy

class TestComparison(unittest.TestCase):
    def sample(self, total, duration):
        return {'name':'test','channels': [total]+[0]*4095, 'count':total,
                'live_s':duration,'rate':total/duration,'intervals':10}
    def test_identical_rate_and_spectrum(self):
        report=compare(self.sample(200,2.0),self.sample(400,4.0))
        self.assertAlmostEqual(report['rate_difference_z'],0)
        self.assertEqual(report['grouped_spectral_total_variation'],0)
    def test_rate_shift(self):
        report=compare(self.sample(2000,10),self.sample(4000,40))
        self.assertFalse(report['rate_95pct_approx_compatible'])
    def test_reference_only_configuration_changes(self):
        original='MEASUREMENT_TIME_S = 60.0\nLIB_PATH = (\n "old"\n)\nOUTPUT_ROOT = Path(__file__).parent\nMAGIC = 12\n'
        result=make_configured_copy(original,Path('/tmp/vendor.so'),Path('/tmp/output'),90)
        self.assertIn('MAGIC = 12',result)
        self.assertIn('MEASUREMENT_TIME_S = 90.0',result)
        self.assertIn("LIB_PATH = '/tmp/vendor.so'",result)
if __name__=='__main__':unittest.main()
