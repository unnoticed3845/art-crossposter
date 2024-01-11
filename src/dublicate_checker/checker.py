from secrets import token_hex
from pathlib import Path
from typing import List
from PIL import Image
import imagehash
import logging
import sqlite3

from src.request_utils import strip_args_from_url, download_photo

logger = logging.getLogger("DublicateChecker")

class DublicateChecker:
    __tmp_dir = Path(__file__).parent.joinpath("tmp")
    __init_script = Path(__file__).parent.joinpath("init.sql")
    __db_file = Path(__file__).parent.joinpath("image_hashes.db")

    def __init__(self, allowed_formats: List[str] = [".jpg", ".jpeg", ".png", ".bmp"]) -> None:
        self.con = sqlite3.connect(self.__db_file)
        self._init_db()
        self.allowed_formats = tuple(allowed_formats)

        if not self.__tmp_dir.is_dir():
            self.__tmp_dir.mkdir()
        for f in self.__tmp_dir.iterdir():
            f.unlink()

    def hash_exists(self, hash_str: str) -> bool:
        cur = self.con.cursor()
        cur.execute("""
            SELECT 1 FROM img_hashes WHERE img_hash = ?
        """, (hash_str, ))
        result = cur.fetchall()
        logger.debug(f"Hash {hash_str} returned {result}")
        if len(result) != 0:
            cur.execute("""
                UPDATE img_hashes
                SET matches = matches + 1
                WHERE img_hash = ?
            """, (hash_str, ))
            self.con.commit()
        return len(result) != 0

    def photo_exists(self, photo_url: str) -> bool:
        photo_hash = self.get_hash_from_url(photo_url)
        return self.hash_exists(photo_hash)

    def add_hash(self, hash_str: str, source_url: str = None) -> None:
        cur = self.con.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO img_hashes(img_hash, source_link)
            VALUES(?,?)
        """, (hash_str, source_url))
        self.con.commit()

    def add_hash_from_url(self, photo_url: str):
        hash_str = self.get_hash_from_url(photo_url)
        return self.add_hash(hash_str, photo_url)

    def get_hash(self, photo_path: Path) -> str:
        return str(imagehash.average_hash(Image.open(photo_path), hash_size=8))

    def get_hash_from_url(self, photo_url: str) -> str:
        file_name = self._download_photo(photo_url)
        file_hash = self.get_hash(file_name)
        file_name.unlink(missing_ok=True)
        return file_hash

    def _download_photo(self, photo_url: str) -> Path:
        stripped_url = strip_args_from_url(photo_url)
        img_format = None
        for format in self.allowed_formats:
            if stripped_url.endswith(format):
                img_format = format
                break
        if img_format is None:
            raise ValueError(f"photo_url must have allowed type. photo_url: {photo_url}")
        file_name = self.__tmp_dir.joinpath(f"{token_hex()}{img_format}")
        download_photo(photo_url, file_name)
        return file_name

    def _init_db(self) -> None:
        with open(self.__init_script, 'r', encoding='utf-8') as f:
            raw_sql = f.read()
        cur = self.con.cursor()
        cur.executescript(raw_sql)
        