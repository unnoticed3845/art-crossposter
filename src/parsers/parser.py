from typing import Generator, Dict, Any
from . import Post

class ArtworkParser:
    def scrape_posts(
        self,
        max_pages: int = 3
    ) -> Generator[Post, None, None]:
        raise NotImplementedError()
