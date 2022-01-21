from __future__ import annotations
import contextlib

import json
import os
import re
from typing import Any, Dict, List, Optional, Type, Union, TYPE_CHECKING

import aiohttp
import bs4
import discord
from discord.utils import escape_markdown as escape

import env


PIXIV_HEADERS = {"referer": "https://www.pixiv.net/"}
HOST = env.get_host()
ID_PATTERN = re.compile(r"(?<!\d)\d{4,8}(?!\d)")
URL_PATTERN = re.compile(r"https://www\.pixiv\.net/(en/)?artworks/\d{4,8}/?")


class StreamError(Exception):
    """Exception raised when collecting image data from Pixiv fails"""
    pass


class PixivUser:
    """Represents a Pixiv user"""

    __slots__ = ("id", "name", "image_url")
    if TYPE_CHECKING:
        id: int
        name: str
        image_url: str

    def __init__(self, id: int, name: str, image_url: str) -> None:
        self.id = id
        self.name = name
        self.image_url = image_url

    def __repr__(self) -> str:
        return f"<PixivUser name={self.name} id={self.id}>"


class PixivArtwork:
    """Represents an artwork from Pixiv ajax"""

    __slots__ = ("title", "id", "image_url", "width", "height", "nsfw", "description", "tags", "url", "thumbnail", "author")
    if TYPE_CHECKING:
        title: str
        id: int
        image_url: str
        width: int
        height: int
        nsfw: bool
        description: Optional[str]
        tags: Optional[List[str]]
        url: str
        thumbnail: str
        author: PixivUser

    def __init__(self, js: Dict[str, Any]) -> None:
        self.title = js["title"]
        self.id = js["id"]
        self.image_url = js["url"]
        self.width = js["width"]
        self.height = js["height"]

        self.nsfw = js.get("xRestrict", False)
        self.description = js.get("description")
        self.tags = js.get("tags")
        self.url = f"https://www.pixiv.net/en/artworks/{self.id}"
        self.thumbnail = f"https://embed.pixiv.net/decorate.php?illust_id={self.id}"

        author_id = js["userId"]
        author_name = js["userName"]
        author_avatar_url = js["profileImageUrl"]
        self.author = PixivUser(author_id, author_name, author_avatar_url)

    async def stream(self, *, session: aiohttp.ClientSession) -> None:
        if os.path.isfile(f"./server/image/{self.id}.png"):
            return

        with contextlib.suppress(aiohttp.ClientError):
            async with session.get(self.image_url, headers=PIXIV_HEADERS) as response:
                if response.ok:
                    with open(f"./server/image/{self.id}.png", "wb") as f:
                        f.write(await response.read())
                        return

        raise StreamError

    async def create_embed(self, *, session: aiohttp.ClientSession) -> discord.Embed:
        embed = discord.Embed(
            title=escape(self.title),
            description=escape(self.description) if self.description else discord.Embed.Empty,
            url=self.url,
        )

        try:
            await self.stream(session=session)
        except StreamError:
            embed.set_image(url=self.thumbnail)
        else:
            embed.set_image(url=f"{HOST}/image/{self.id}.png")

        embed.add_field(
            name="Tags",
            value=", ".join(escape(tag) for tag in self.tags) if self.tags else "*No tags given*",
            inline=False,
        )
        embed.add_field(
            name="Artwork ID",
            value=self.id,
        )
        embed.add_field(
            name="Author",
            value=f"[{escape(self.author.name)}](https://www.pixiv.net/en/users/{self.author.id})",
        )
        embed.add_field(
            name="Size",
            value=f"{self.width} x {self.height}",
        )
        embed.add_field(
            name="Artwork link",
            value=self.url,
            inline=False,
        )
        return embed

    def __repr__(self) -> str:
        return f"<PixivArtwork title={self.title} id={self.id} author={self.author}>"

    @classmethod
    async def search(cls: Type[PixivArtwork], query: str, *, session: aiohttp.ClientSession) -> List[PixivArtwork]:
        """This function is a coroutine

        Get 6 Pixiv images sorted by date that match the searching query.

        Parameters
        -----
        query: ``str``
            The searching query
        session: ``aiohttp.ClientSession``
            The session to perform the search

        Returns
        -----
        List[``PixivArtwork``]
            A list of search results, note that this may be empty
        """
        async with session.get(f"https://www.pixiv.net/ajax/search/artworks/{query}") as response:
            if response.ok:
                js = await response.json(encoding="utf-8")
                try:
                    artworks = js["body"]["illustManga"]["data"]
                except KeyError:
                    pass
                else:
                    return list(cls(artwork) for artwork in artworks[:6])

        return []

    @classmethod
    def parse_html(cls: Type[PixivArtwork], html: str) -> Optional[PixivArtwork]:
        """Parse the HTML string of the artwork site into a ``PixivArtwork`` object.

        Parameters
        -----
        html: ``str``
            The HTML string
        
        Returns
        -----
        Optional[``PixivArtwork``]
            The created ``PixivArtwork`` object
        """
        soup = bs4.BeautifulSoup(html, "html.parser")
        content = soup.find("meta", attrs={"name": "preload-data"}).get("content")
        if content:
            data = json.loads(content)
            id = int(list(data["illust"].keys())[0])
            illust = data["illust"][str(id)]
            user_id = int(illust.get("userId"))
            ret = {
                "title": illust.get("title"),
                "id": id,
                "xRestrict": illust.get("xRestrict"),
                "url": illust.get("urls", {}).get("regular", discord.Embed.Empty),
                "tags": list(tag["tag"] for tag in illust["tags"]["tags"]),
                "width": illust.get("width"),
                "height": illust.get("height"),
                "userId": user_id,
                "userName": illust.get("userName"),
                "profileImageUrl": data["user"][str(user_id)]["image"],
            }
            return cls(ret)


    @classmethod
    async def from_id(cls: Type[PixivArtwork], id: int, *, session: aiohttp.ClientSession) -> Optional[PixivArtwork]:
        """This function is a coroutine

        Gets a Pixiv artwork from an ID

        Parameters
        -----
        id: ``int``
            The artwork ID
        session: ``aiohttp.ClientSession``
            The session to perform the request

        Returns
        -----
        Optional[``PixivArtwork``]
            The artwork with the given ID, or ``None`` if not found
        """
        with contextlib.suppress(aiohttp.ClientError):
            async with session.get(f"https://pixiv.net/en/artworks/{id}") as response:
                if response.ok:
                    html = await response.text(encoding="utf-8")
                    return cls.parse_html(html)


async def parse(query: str, *, session: aiohttp.ClientSession) -> Union[PixivArtwork, List[PixivArtwork]]:
    """This function is a coroutine

    Parse ``query`` to predict the user's intention when processing a
    Pixiv-related request.

    Note that this coroutine never returns ``None``. When no result is
    found, an empty list is returned.

    Parameters
    -----
    query: ``str``
        The input string
    session: ``aiohttp.ClientSession``
        The session to perform the request

    Returns
    -----
    Union[``PixivArtwork``, List[``PixivArtwork``]]
        A certain artwork (when an ID or URL is detected), or multiple
        artworks as a list (in case of a searching string)
    """
    match = ID_PATTERN.fullmatch(query)
    if match:
        artwork = await PixivArtwork.from_id(match.group(), session=session)
        if artwork:
            return artwork

    if query.startswith("http"):
        with contextlib.suppress(aiohttp.ClientError):
            async with session.get(query) as response:
                if response.ok:
                    match = URL_PATTERN.fullmatch(str(response.url))
                    if match is not None:
                        # Valid URL, parse HTML to get the artwork
                        html = await response.text(encoding="utf-8")
                        return PixivArtwork.parse_html(html)

    return await PixivArtwork.search(query, session=session)
