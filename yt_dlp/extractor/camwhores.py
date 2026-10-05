import re
import urllib.parse

from .common import InfoExtractor
from .generic import GenericIE
from ..utils import (
    ExtractorError,
    js_to_json,
    parse_duration,
    parse_resolution,
    str_to_int,
    url_or_none,
)


class CamWhoresIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?camwhores\.(?:tv|video|us\.com)/videos/(?P<id>\d+)/(?P<display_id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.camwhores.tv/videos/15102259/ambie-bambii-onlyfans-teen-step-sis-pov-sextape2',
        'info_dict': {
            'id': '15102259',
            'display_id': 'ambie-bambii-onlyfans-teen-step-sis-pov-sextape2',
            'ext': 'mp4',
            'title': 'Ambie Bambii OnlyFans Teen Step Sis POV Sextape',
            'thumbnail': r're:https?://[^/]+/contents/videos_screenshots/15102000/15102259/preview\.jpg',
            'description': str,
            'duration': 1007,
            'view_count': int,
            'categories': ['OnlyFans'],
            'tags': list,
            'age_limit': 18,
        },
    }, {
        'url': 'https://www.camwhores.us.com/videos/13511684/catanddickxxx-2023-12-29-22-03-17/',
        'only_matching': True,
    }, {
        'url': 'https://www.camwhores.video/videos/16747268/sex-boooy-girl-10-25-25/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id, display_id = self._match_valid_url(url).group('id', 'display_id')
        # The site returns 404 for video pages without a trailing slash.
        parsed_url = urllib.parse.urlparse(url)
        url = urllib.parse.urlunparse(parsed_url._replace(path=f'{parsed_url.path.rstrip("/")}/'))
        webpage = self._download_webpage(url, video_id)
        flashvars = self._search_json(
            r'\bvar\s+flashvars\s*=', webpage, 'player data', video_id,
            transform_source=js_to_json, default={})
        if not flashvars:
            if re.search(r'(?i)\b(?:private video|this video is (?:a )?private)\b', webpage):
                self.raise_login_required('This video is private', method='cookies')
            raise ExtractorError('Video is unavailable or player data is missing', expected=True)

        formats = []
        for key, video_url in flashvars.items():
            if not re.fullmatch(r'video_(?:url|alt_url\d*)', key) or not isinstance(video_url, str) or not video_url:
                continue
            video_url = url_or_none(urllib.parse.urljoin(
                url, GenericIE._kvs_get_real_url(video_url, flashvars.get('license_code', ''))))
            if not video_url:
                continue
            format_id = flashvars.get(f'{key}_text') or key
            resolution = parse_resolution(format_id) or parse_resolution(video_url)
            if not resolution:
                if flashvars.get(f'{key}_fhd') == '1':
                    resolution = {'height': 1080}
                elif flashvars.get(f'{key}_hd') == '1':
                    resolution = {'height': 720}
            formats.append({
                'url': video_url,
                'format_id': format_id,
                'ext': 'mp4',
                **resolution,
            })

        thumbnail = flashvars.get('preview_url') or self._og_search_thumbnail(webpage, default=None)
        view_count = self._html_search_regex(
            r'Views:\s*<em\b[^>]*>([^<]+)', webpage, 'view count', default='')
        return {
            'id': video_id,
            'display_id': display_id,
            'title': flashvars.get('video_title') or self._og_search_title(webpage),
            'description': self._og_search_description(webpage, default=None),
            'thumbnail': urllib.parse.urljoin(url, thumbnail) if thumbnail else None,
            'duration': parse_duration(self._html_search_regex(
                r'Duration:\s*<em\b[^>]*>([^<]+)', webpage, 'duration', default=None)),
            'view_count': str_to_int(re.sub(r'\s+', '', view_count)),
            'categories': [category.strip() for category in (flashvars.get('video_categories') or '').split(',') if category.strip()],
            'tags': [tag.strip() for tag in (flashvars.get('video_tags') or '').split(',') if tag.strip()],
            'age_limit': 18,
            'formats': formats,
            'http_headers': {'Referer': url},
        }
