from typing import Optional, List
from urllib import parse

from bs4 import BeautifulSoup

from core import bot


async def search(query: str, *, max_results: Optional[int] = None) -> List[str]:
    """This function is a coroutine

    Search zerochan.net for a list of image URLs.

    Parameters
    -----
    query: ``str``
        The searching query
    max_results: Optional[``int``]
        The maximum number of results to return

    Returns
    List[``str``]
        A list of image URLs
    """
    url: str = "https://www.zerochan.net/" + parse.quote(query, encoding="utf-8")
    ret: List[str] = []
    page: int = 0

    while page := page + 1:
        ext: List[str] = []
        async with bot.session.get(url, params={"p": page}) as response:
            if response.ok:
                html: str = await response.text(encoding="utf-8")
                soup: BeautifulSoup = BeautifulSoup(html, "html.parser")
                for img in soup.find_all("img"):
                    image_url: Optional[str] = img.get("src")  # This should be "type: str" (who would create an <img> tag without "src" anyway?)
                    if image_url.endswith(".jpg"):
                        ext.append(image_url)

        if ext:
            ret.extend(ext)
            if max_results is not None and len(ret) >= max_results:
                return ret[:max_results]
        else:
            break

    return ret
