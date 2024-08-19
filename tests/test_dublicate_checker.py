import unittest
import os

from src.dublicate_checker import DublicateChecker

class TestDanbooruParser(unittest.TestCase):
    db_file = 'test_dummy.db'
    def create_test_checker(self, formats: list = None) -> DublicateChecker:
        if formats:
            return DublicateChecker(allowed_formats=formats, db_file=self.db_file)
        else:
            return DublicateChecker(db_file=self.db_file)
    
    def clear_dummy_db(self) -> None:
        os.remove(self.db_file)

    def test_adding(self) -> None:
        ch = self.create_test_checker()
        url = 'https://cdn.donmai.us/sample/b2/ed/__elster_signalis_drawn_by_fune_nkjrs12__sample-b2ed9ea15fc0f0b784882fcca184210e.jpg'
        hash_str = ch.get_hash_from_url(url)
        ch.add_hash(hash_str, url)

        self.assertTrue(ch.hash_exists(hash_str))

        self.clear_dummy_db()

    def test_multiple_adding(self) -> None:
        ch = self.create_test_checker()
        urls = [
            'https://cdn.donmai.us/sample/b2/ed/__elster_signalis_drawn_by_fune_nkjrs12__sample-b2ed9ea15fc0f0b784882fcca184210e.jpg',
            'https://cdn.donmai.us/sample/b5/ba/__elster_ariane_yeong_and_falke_signalis_drawn_by_calitroppings__sample-b5ba850240d4c1d967e0e32b4ff194d8.jpg',
            'https://cdn.donmai.us/sample/14/17/__elster_and_ariane_yeong_signalis_drawn_by_legend_knit__sample-14173148c25e6177e4edbfa90c32d4fb.jpg',
            'https://cdn.donmai.us/sample/b1/39/__elster_and_ariane_yeong_signalis_and_1_more_drawn_by_funkiflame__sample-b13934a62ef003a7addbd603f8141c3f.jpg'
        ]
        hashes = []
        for url in urls:
            hash_str = ch.get_hash_from_url(url)
            ch.add_hash(hash_str, url)
            hashes.append(hash_str)

        for h in hashes:
            self.assertTrue(ch.hash_exists(h))

        self.clear_dummy_db()
