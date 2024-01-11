from PIL import Image
from typing import List
from pathlib import Path
from secrets import token_hex
import imagehash
import sqlite3
import requests
import os

from src.request_utils import strip_args_from_url

class DublicateChecker:
    __data_dir = Path(__file__).parent.joinpath("data")

    def __init__(self, allowed_formats: List[str] = [".jpg", ".jpeg", ".png", ".bmp"]) -> None:
        self.con = sqlite3.connect("image_hashes.db")
        self.allowed_formats = tuple(allowed_formats)

        if not self.__data_dir.is_dir():
            self.__data_dir.mkdir()
        """ for f in self.__data_dir.iterdir():
            f.unlink() """

    def check(self, photo_url: str) -> bool:
        photo_hash = self.get_hash_from_url(photo_url)

    def get_hash(self, photo_path: Path):
        return imagehash.average_hash(Image.open(photo_path), hash_size=8)
        return imagehash.crop_resistant_hash(
            Image.open(photo_path),
            segment_threshold=128,
            min_segment_size=100,
            segmentation_image_size=300
        )

    def get_hash_from_url(self, photo_url: Path):
        file_name = self._download_photo(photo_url)
        file_hash = self.get_hash(file_name)
        #file_name.unlink(missing_ok=True)
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
        
        img_data = requests.get(photo_url).content
        file_name = self.__data_dir.joinpath(f"{token_hex()}{img_format}")
        with open(file_name, 'wb') as handler:
            handler.write(img_data)

        #os.system(f"convert -resize 256X256 {file_name} {file_name}")
        #self._strip_colors(file_name)

        return file_name

    def _strip_colors(self, photo_path: Path) -> Path:
        img = Image.open(photo_path)
        pixels = img.load()
        def round_bin(num: int, n: int = 6) -> int:
            bit = num & (1<<n)
            mask = (1<<n) - 1
            if(bit):
                return num | mask
            else:
                return num & ~mask
        for i in range(img.size[0]):
            for j in range(img.size[1]):
                if len(pixels[i, j]) == 4:
                    r, g, b, a = pixels[i, j]
                else:
                    r, g, b = pixels[i, j]
                r = round_bin(r)
                g = round_bin(g)
                b = round_bin(b)
                if len(pixels[i, j]) == 4:
                    pixels[i, j] = r, g, b, a
                else: 
                    pixels[i, j] = r, g, b
        #img.save(photo_path.parent.joinpath("stripped_" + str(photo_path.name)))
        img.save(photo_path)