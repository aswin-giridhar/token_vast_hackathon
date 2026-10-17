import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

workspace = tempfile.TemporaryDirectory()
os.environ['DATA_DIR'] = workspace.name
spec = importlib.util.spec_from_file_location('clipscout', Path(__file__).with_name('main.py'))
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class EvidenceTests(unittest.TestCase):
    def test_source_times_remain_parent_relative(self):
        clip = app.normalize({'source': 's3://test/segment.mp4',
            'original_video': 's3://test/parent.mp4', 'segment_start_sec': 25,
            'segment_end_sec': 30, 'duration': 5, 'upload_timestamp': '2026-10-08T12:00:00'})
        self.assertEqual((clip['in'], clip['out'], clip['duration']), (25, 30, 5))
        self.assertIsNone(clip['capture_time'])
        self.assertEqual(clip['original_video'], 's3://test/parent.mp4')

    def test_invalid_media_reference_is_not_registered(self):
        self.assertIsNone(app.normalize({'source': 'http://169.254.169.254/'}))
        self.assertIsNone(app.normalize({'source':'s3://test/reverse.mp4',
            'segment_start_sec':10, 'segment_end_sec':5}))

    def test_search_uses_ranked_segment_not_group_preview(self):
        original = app.vss.call
        app.vss.call = lambda *args: {'results': [
            {'source': 's3://test/segment2.mp4', 'original_video':'s3://test/parent.mp4',
             'segment_start_sec':5, 'segment_end_sec':10, 'similarity_score':.57}],
            'chunk_results': [{'preview_source':'s3://test/segment3.mp4',
              'best_match_start_sec':10, 'best_match_end_sec':15}]}
        try:
            clip = app.search('cyclist')['clips'][0]
            self.assertEqual(clip['source'], 's3://test/segment2.mp4')
            self.assertEqual((clip['in'], clip['out']), (5, 10))
        finally:
            app.vss.call = original


if __name__ == '__main__':
    unittest.main()
