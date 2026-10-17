import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError

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
        app.vss.call = lambda *args, **kwargs: {'results': [
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

    def test_search_job_is_reused_and_result_cache_can_be_refreshed(self):
        app.SEARCH_JOBS.clear()
        app.SEARCH_CACHE.clear()
        entered, release = threading.Event(), threading.Event()
        def upstream(query):
            entered.set()
            self.assertTrue(release.wait(3))
            return {'query': query, 'clips': []}
        with patch.object(app, 'search', side_effect=upstream) as call:
            first = app.start_search('test query')
            self.assertTrue(entered.wait(3))
            self.assertEqual(app.start_search('test query')['id'], first['id'])
            release.set()
            deadline = time.monotonic() + 3
            while app.SEARCH_JOBS[first['id']]['status'] == 'running' and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertEqual(app.SEARCH_JOBS[first['id']]['status'], 'done')
            self.assertTrue(app.start_search('test query')['result']['cached'])
            self.assertEqual(call.call_count, 1)
            second = app.start_search('test query', refresh=True)
            self.assertNotEqual(second['id'], first['id'])
            deadline = time.monotonic() + 3
            while app.SEARCH_JOBS[second['id']]['status'] == 'running' and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertEqual(app.SEARCH_JOBS[second['id']]['status'], 'done')
            self.assertEqual(call.call_count, 2)

    def test_failed_search_releases_capacity_and_does_not_cache_error(self):
        app.SEARCH_SLOTS.acquire()
        app.SEARCH_JOBS['failure'] = {'status': 'running'}
        with patch.object(app, 'search', side_effect=TimeoutError('sensitive upstream URL')):
            app.search_worker('failure', 'failure query')
        self.assertEqual(app.SEARCH_JOBS['failure']['status'], 'error')
        self.assertNotIn('sensitive', app.SEARCH_JOBS['failure']['error'])
        self.assertNotIn('failure query', app.SEARCH_CACHE)
        self.assertTrue(app.SEARCH_SLOTS.acquire(blocking=False))
        app.SEARCH_SLOTS.release()
        app.SEARCH_JOBS.pop('failure')

    def test_source_list_download_preserves_order_and_authoritative_times(self):
        clips = [app.normalize({'source': f's3://test/export-{i}.mp4',
            'segment_start_sec': start, 'segment_end_sec': start + 5})
            for i, start in enumerate([25, 10])]
        server = app.ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = 'http://127.0.0.1:' + str(server.server_port)
        try:
            body = {'clip_ids': [c['id'] for c in clips],
                'labels': {clips[0]['id']: 'Opening'}, 'brief': 'An urban story',
                'source_in_sec': 999}
            req = Request(base + '/api/source-list', data=json.dumps(body).encode(),
                headers={'Content-Type': 'application/json'})
            with urlopen(req) as response:
                data = json.load(response)
            with urlopen(base + '/api/' + data['download_path']) as response:
                self.assertIn('attachment', response.headers['Content-Disposition'])
                manifest = json.load(response)
            self.assertEqual(manifest['brief'], 'An urban story')
            self.assertEqual([s['source_in_sec'] for s in manifest['shots']], [25, 10])
            self.assertEqual([s['cut_out_sec'] for s in manifest['shots']], [5, 10])
            self.assertEqual(manifest['shots'][0]['request'], 'Opening')
            self.assertTrue((app.DATA / 'source-lists' / (data['id'] + '.json')).exists())
            bad = Request(base + '/api/source-list', data=b'{"clip_ids":["unknown"]}',
                headers={'Content-Type': 'application/json'})
            with self.assertRaises(HTTPError) as error:
                urlopen(bad)
            self.assertEqual(error.exception.code, 400)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_restored_catalog_and_finished_job_survive_reload(self):
        clip = app.normalize({'source': 's3://test/restore.mp4', 'segment_start_sec': 5, 'segment_end_sec': 10})
        app.JOBS['finished'] = {'status': 'done', 'duration_sec': 5}
        app.JOBS['interrupted'] = {'status': 'rendering'}
        app.save_jobs()
        app.CATALOG.clear()
        app.JOBS.clear()
        app.load_saved_state()
        self.assertEqual(app.CATALOG[clip['id']]['in'], 5)
        self.assertEqual(app.JOBS['finished']['status'], 'done')
        self.assertEqual(app.JOBS['interrupted']['status'], 'error')

    def test_advice_uses_server_caption_and_rejects_unknown_sources(self):
        clip = app.normalize({'source': 's3://test/advice.mp4', 'reasoning_content': 'A real cyclist.'})
        payload = {'brief': 'City story', 'requests': [{'id': 'bike', 'label': 'Cyclist', 'query': 'cycling'}],
            'candidates': [{'id': clip['id'], 'request_id': 'bike', 'reason': 'Client invented a marathon.'}]}
        with patch.object(app, 'suggest_edit', return_value={'review_required': True}) as call:
            result = app.editorial_advice(payload)
            self.assertEqual(call.call_args.args[2][0]['reason'], 'A real cyclist.')
            self.assertTrue(result['review_required'])
            self.assertEqual(result['candidate_count'], 1)
        payload['candidates'][0]['id'] = 'unknown'
        with self.assertRaises(ValueError):
            app.editorial_advice(payload)

    def test_advice_failure_does_not_mutate_cut_or_hold_inference_lock(self):
        payload = {'requests': [{'id': 'bike'}], 'candidates': []}
        before = dict(app.CATALOG)
        with patch.object(app, 'suggest_edit', side_effect=app.AdvisorError('Unavailable')):
            with self.assertRaises(app.AdvisorError):
                app.editorial_advice(payload)
        self.assertEqual(app.CATALOG, before)
        self.assertTrue(app.ADVICE_LOCK.acquire(blocking=False))
        app.ADVICE_LOCK.release()


if __name__ == '__main__':
    unittest.main()
