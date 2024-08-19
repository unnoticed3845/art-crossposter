from typing import Tuple, Optional
from dataclasses import dataclass

md_special_char = ['_', ')', '(', '-', '.', '=', '!']

@dataclass(frozen=True)
class Post:
    media_urls: Tuple[str]
    author_name: Optional[str] = None
    source_link: Optional[str] = None
    tags: Optional[Tuple[str]] = None

    def form_caption(self) -> str:
        def escape_md(s: str) -> str:
            for ch in md_special_char:
                s = s.replace(ch, f'\{ch}')
            return s
        artist = f"Artist: {escape_md(self.author_name)}" if self.author_name else "Artist unknown"
        source = f"[Source]({self.source_link})" if self.source_link else "Source unknown"
        return f"{artist}\n" + \
               f"{source}"

    def __str__(self) -> str:
        return f"[{self.author_name}: {self.media_urls}]"
