import unittest

from src.parsers import DanbooruParser, BlacklistedTag

class TestDanbooruParser(unittest.TestCase):
    def test_scrape_one_page(self) -> None:
        target_tag = 'signalis'
        dp = DanbooruParser(tags=[target_tag])
        # saving real data so it is not overwritten while testing
        real_data = dp.file_data.copy()
        dp.file_data = dp._default_data.copy()
        posts = list(dp.scrape_posts(max_pages=1))
        # restoring real data
        dp.file_data = real_data
        dp._write_file_data()

        self.assertGreater(len(posts), 0)
        for post in posts:
            self.assertGreater(len(post.media_urls), 0)
            self.assertIn(target_tag, post.tags)

    def test_scrape_one_page_max_three_posts(self) -> None:
        target_tag = '1girl'
        dp = DanbooruParser(tags=[target_tag])
        # saving real data so it is not overwritten while testing
        real_data = dp.file_data.copy()
        dp.file_data = dp._default_data.copy()
        posts = list(dp.scrape_posts(max_pages=1, max_posts_total=3))
        # restoring real data
        dp.file_data = real_data
        dp._write_file_data()

        self.assertEqual(len(posts), 3)
        for post in posts:
            self.assertGreater(len(post.media_urls), 0)
            self.assertIn(target_tag, post.tags, msg='')

    def test_scrape_blacklisted(self) -> None:
        target_tag = 'signalis'
        dp = DanbooruParser(tags=[target_tag], 
                            blacklist_tags=[BlacklistedTag(target_tag)])
        # saving real data so it is not overwritten while testing
        real_data = dp.file_data.copy()
        dp.file_data = dp._default_data.copy()
        posts = list(dp.scrape_posts(max_pages=1))
        # restoring real data
        dp.file_data = real_data
        dp._write_file_data()

        self.assertEqual(len(posts), 0)

    def test_scrape_blacklisted_exceptions(self) -> None:
        target_tag = 'signalis elster_(signalis)'
        dp = DanbooruParser(
            tags=[target_tag], 
            blacklist_tags=[BlacklistedTag('signalis', ['elster_(signalis)'])])
        # saving real data so it is not overwritten while testing
        real_data = dp.file_data.copy()
        dp.file_data = dp._default_data.copy()
        posts = list(dp.scrape_posts(max_pages=1,max_posts_total=5))
        # restoring real data
        dp.file_data = real_data
        dp._write_file_data()

        self.assertEqual(len(posts), 5)