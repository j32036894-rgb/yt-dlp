import json
import unittest
from unittest.mock import patch

from test.helper import FakeYDL
from yt_dlp.extractor import gen_extractor_classes
from yt_dlp.extractor.camwhores import CamWhoresIE
from yt_dlp.utils import ExtractorError


class TestCamWhores(unittest.TestCase):
    URL = 'https://www.camwhores.tv/videos/123/example'
    MEDIA_URL = 'https://www.camwhores.tv/get_file/1/hash/0/123/123.mp4/?v-acctoken=abc%2Bdef'

    def setUp(self):
        self.ie = CamWhoresIE(FakeYDL())

    def extract(self, flashvars, html='', url=None):
        webpage = f'<script>var flashvars = {json.dumps(flashvars)};</script>{html}'
        with patch.object(self.ie, '_download_webpage', return_value=webpage) as download:
            info = self.ie._real_extract(url or self.URL)
        return info, download

    def test_registration_and_matching(self):
        self.assertIn(CamWhoresIE, gen_extractor_classes())
        for domain in ('camwhores.tv', 'www.camwhores.tv', 'camwhores.video', 'camwhores.us.com'):
            with self.subTest(domain=domain):
                self.assertTrue(CamWhoresIE.suitable(f'https://{domain}/videos/123/example/'))
        self.assertFalse(CamWhoresIE.suitable('https://camwhores.tv/search/example/'))
        self.assertFalse(CamWhoresIE.suitable('https://camwhores.tv.example.com/videos/123/example/'))

    def test_signed_url_and_metadata(self):
        info, download = self.extract({
            'video_title': 'Example video',
            'video_url': self.MEDIA_URL,
            'video_url_fhd': '1',
            'preview_url': '//cdn.camwhores.tv/preview.jpg',
            'video_categories': 'Category one, Category two',
            'video_tags': 'tag one, tag two, ',
        }, '''
            <meta property="og:description" content="Example &amp; description">
            <span>Duration: <em>16:47</em></span>
            <span>Views: <em>242 883</em></span>
        ''', url=f'{self.URL}?foo=bar')
        download.assert_called_once_with(f'{self.URL}/?foo=bar', '123')
        self.assertEqual(info['id'], '123')
        self.assertEqual(info['display_id'], 'example')
        self.assertEqual(info['title'], 'Example video')
        self.assertEqual(info['description'], 'Example & description')
        self.assertEqual(info['duration'], 1007)
        self.assertEqual(info['view_count'], 242883)
        self.assertEqual(info['thumbnail'], 'https://cdn.camwhores.tv/preview.jpg')
        self.assertEqual(info['categories'], ['Category one', 'Category two'])
        self.assertEqual(info['tags'], ['tag one', 'tag two'])
        self.assertEqual(info['age_limit'], 18)
        self.assertEqual(info['formats'][0]['url'], self.MEDIA_URL)
        self.assertEqual(info['formats'][0]['height'], 1080)
        self.assertEqual(info['http_headers']['Referer'], f'{self.URL}/?foo=bar')

    def test_alternate_formats_and_fallback_metadata(self):
        info, download = self.extract({
            'video_url': '/get_file/1/hash/0/123/123.mp4/',
            'video_url_hd': '1',
            'video_alt_url': '//cdn.camwhores.tv/123_480p.mp4',
            'video_alt_url_text': '480p',
            'video_alt_url2': 'https://cdn.camwhores.tv/123_1080p.mp4',
            'video_alt_url2_text': '1080p',
            'video_url1': 'https://example.com/advertisement.mp4',
            'video_alt_url3': '',
        }, '''
            <meta property="og:title" content="Fallback title">
            <meta property="og:image" content="https://cdn.camwhores.tv/preview.jpg">
        ''', url=f'{self.URL}/')
        download.assert_called_once_with(f'{self.URL}/', '123')
        self.assertEqual(info['title'], 'Fallback title')
        self.assertEqual(info['thumbnail'], 'https://cdn.camwhores.tv/preview.jpg')
        self.assertEqual([f['height'] for f in info['formats']], [720, 480, 1080])
        self.assertEqual(info['formats'][0]['url'], 'https://www.camwhores.tv/get_file/1/hash/0/123/123.mp4/')
        self.assertEqual(info['formats'][1]['url'], 'https://cdn.camwhores.tv/123_480p.mp4')

    def test_private_video(self):
        with patch.object(self.ie, '_download_webpage', return_value='<div>This video is a private video</div>'):
            with self.assertRaises(ExtractorError) as error:
                self.ie._real_extract(self.URL)
        self.assertTrue(error.exception.expected)
        self.assertIn('cookies', str(error.exception))

    def test_missing_player(self):
        with patch.object(self.ie, '_download_webpage', return_value='<title>404 / Page not found</title>'):
            with self.assertRaisesRegex(ExtractorError, 'Video is unavailable') as error:
                self.ie._real_extract(self.URL)
        self.assertTrue(error.exception.expected)


if __name__ == '__main__':
    unittest.main()
