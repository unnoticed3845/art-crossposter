import unittest
import json
import os

from src.parse import DanbooruParser, BlacklistedTag, BaseParser

class TestDanbooruParser(unittest.TestCase):
    _dummy_config = 'dummy_config.json'

    @classmethod
    def create_dummy_config(cls, data: dict):
        with open(BaseParser._config_dir.joinpath(cls._dummy_config), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    @classmethod
    def vipe_dummy_config(cls):
        os.remove(BaseParser._config_dir.joinpath(cls._dummy_config))

    def test_scrape_one_page(self) -> None:
        target_tag = 'signalis'
        self.create_dummy_config({
            'max_pages': 1,
            'tags': [target_tag],
            'blacklisted_tags': []
        })
        dp = DanbooruParser(config_file=self._dummy_config)
        # saving real data so it is not overwritten while testing
        real_data = dp.file_data.copy()
        dp.file_data = dp._default_data.copy()
        # scraping
        posts = list(dp.scrape_posts())
        # restoring real data
        dp.file_data = real_data
        dp.save_data()
        self.vipe_dummy_config()

        self.assertGreater(len(posts), 0)
        for post in posts:
            self.assertGreater(len(post.media_urls), 0)
            self.assertIn(target_tag, post.tags)

    def test_scrape_one_page_max_three_posts(self) -> None:
        target_tag = '1girl'
        self.create_dummy_config({
            'max_pages': 1,
            'tags': [target_tag],
            'blacklisted_tags': []
        })
        dp = DanbooruParser(config_file=self._dummy_config)
        # saving real data so it is not overwritten while testing
        real_data = dp.file_data.copy()
        dp.file_data = dp._default_data.copy()
        # scraping
        posts = list(dp.scrape_posts(max_posts_total=3))
        # restoring real data
        dp.file_data = real_data
        dp.save_data()
        self.vipe_dummy_config()

        self.assertEqual(len(posts), 3)
        for post in posts:
            self.assertGreater(len(post.media_urls), 0)
            self.assertIn(target_tag, post.tags, msg='')

    def test_scrape_blacklisted(self) -> None:
        target_tag = 'signalis'
        self.create_dummy_config({
            'max_pages': 1,
            'tags': [target_tag],
            'blacklisted_tags': [target_tag]
        })
        dp = DanbooruParser(config_file=self._dummy_config)
        # saving real data so it is not overwritten while testing
        real_data = dp.file_data.copy()
        dp.file_data = dp._default_data.copy()
        # scraping
        posts = list(dp.scrape_posts())
        # restoring real data
        dp.file_data = real_data
        dp.save_data()
        self.vipe_dummy_config()

        self.assertEqual(len(posts), 0)

    def test_scrape_blacklisted_exceptions(self) -> None:
        target_tag = 'signalis'
        exception = 'elster_(signalis)'
        self.create_dummy_config({
            'max_pages': 1,
            'tags': [f'{target_tag} {exception}'],
            'blacklisted_tags': [[target_tag, [exception]]]
        })
        dp = DanbooruParser(config_file=self._dummy_config)
        # saving real data so it is not overwritten while testing
        real_data = dp.file_data.copy()
        dp.file_data = dp._default_data.copy()
        # scraping
        posts = list(dp.scrape_posts(max_posts_total=5))
        # restoring real data
        dp.file_data = real_data
        dp.save_data()
        self.vipe_dummy_config()

        self.assertEqual(len(posts), 5)