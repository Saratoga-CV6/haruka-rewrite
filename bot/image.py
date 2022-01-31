from __future__ import annotations

import asyncio
import random
import re
from typing import (
    ClassVar,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    TypeVar,
    TYPE_CHECKING,
)

import aiohttp

if TYPE_CHECKING:
    import haruka


IT = TypeVar("IT", bound="ImageSource")


class CategoryNotFound(Exception):
    def __init__(self, category: str) -> None:
        self.category = category


class ImageSource:
    """Represents an image source.

    This class is responsible for registering the categories that
    an image source can provide, as well as getting the image URL
    when there is a request.

    Attributes
    -----
    session: ``aiohttp.ClientSession``
        The aiohttp session used to interact with the image source.
    client: ``ImageClient``
        The client that manages this image source.
    """

    __slots__ = ("session", "client")
    if TYPE_CHECKING:
        session: aiohttp.ClientSession
        client: ImageClient

    def __init__(self, session: aiohttp.ClientSession, client: ImageClient) -> None:
        self.session = session
        self.client = client

    async def _get_all_endpoints(self) -> Tuple[List[str], List[str]]:
        """This function is a coroutine

        Get all endpoints that this image source can provide.

        Subclasses must implement this.

        Returns
        -----
        Tuple[List[``str``], List[``str``]]
            A 2-tuple containing the sfw and nsfw categories that the
            image source can provide. These categories will be passed
            to ``get`` to get the image URL.
        """
        raise NotImplementedError

    async def get(self, category: str, *, mode: Literal["sfw", "nsfw"]) -> Optional[str]:
        """This function is a coroutine

        Get the URL of the requested category and mode.

        Subclasses must implement this.

        Parameters
        -----
        category: ``str``
            The requested category that the image source can provide,
            should be registered with ``_get_all_endpoints`` first.
        mode: Literal["sfw", "nsfw"]
            Whether the image should be sfw or nsfw.

        Returns
        -----
        Optional[``str``]
            The image URL
        """
        raise NotImplementedError

    @property
    def bot(self) -> haruka.Haruka:
        return self.client.bot


class WaifuPics(ImageSource):

    __slots__ = (
        "session",
        "client",
    )
    endpoints_url: ClassVar[str] = "https://api.waifu.pics/endpoints"

    async def _get_all_endpoints(self) -> Tuple[List[str], List[str]]:
        data = {
            "sfw": [],
            "nsfw": [],
        }
        async with self.session.get(self.endpoints_url) as response:
            if response.status == 200:
                data = await response.json(encoding="utf-8")

        return data["sfw"], data["nsfw"]

    async def get(self, category: str, *, mode: Literal["sfw", "nsfw"]) -> Optional[str]:
        url = f"https://api.waifu.pics/{mode}/{category}"
        async with self.session.get(url) as response:
            if response.status == 200:
                json = await response.json(encoding="utf-8")
                return json["url"]

        return


class WaifuIm(ImageSource):

    __slots__ = (
        "session",
        "client",
    )
    endpoints_url: ClassVar[str] = "https://api.waifu.im/endpoints"

    async def _get_all_endpoints(self) -> Tuple[List[str], List[str]]:
        data = {"sfw": [], "nsfw": []}

        async with self.session.get(self.endpoints_url) as response:
            if response.status == 200:
                data = await response.json(encoding="utf-8")

        return data["sfw"], data["nsfw"]

    async def get(self, category: str, *, mode: Literal["sfw", "nsfw"]) -> Optional[str]:
        url = f"https://api.waifu.im/{mode}/{category}"
        async with self.session.get(url) as response:
            if response.status == 200:
                json = await response.json(encoding="utf-8")
                return json["images"][0]["url"]

        return


class NekosLife(ImageSource):

    __slots__ = (
        "session",
        "client",
    )
    endpoints_url: ClassVar[str] = "https://nekos.life/api/v2/endpoints"
    sfw_converter: ClassVar[Dict[str, str]] = {
        "neko gif": "ngif",
        "kitsune": "fox_girl",
    }
    nsfw_converter: ClassVar[Dict[str, str]] = {
        "ero neko": "eron",
        "neko gif": "nsfw_neko_gif",
        "lewd kitsune": "lewdk",
        "ero kitsune": "erok",
        "lewd holo": "hololewd",
        "ero holo": "holoero",
        "ero feet": "erofeet",
        "ero yuri": "eroyuri",
        "cum": "cum_jpg",
        "pussy": "pussy_jpg",
        "cum gif": "cum",
        "solo gif": "solog",
        "pussy wank gif": "pwankg",
        "pussy gif": "pussy",
        "random": "Random_hentai_gif",
        "feet gif": "feetg",
        "pussy lick gif": "kuni",
    }

    async def _get_all_endpoints(self) -> Tuple[List[str], List[str]]:
        data = {
            "sfw": ["neko", "neko gif", "kitsune", "holo", "pat", "poke", "hug", "cuddle", "kiss", "feed", "tickle", "smug", "baka", "slap"],
            "nsfw": ["lewd", "ero neko", "neko gif", "lewd kitsune", "ero kitsune", "lewd holo", "ero holo", "ero", "feet", "ero feet", "gasm", "solo", "tits", "yuri", "ero yuri", "hentai", "cum", "blowjob", "femdom", "trap", "pussy", "futanari", "cum gif", "solo gif", "spank", "les", "bj", "pussy wank gif", "pussy gif", "random", "feet gif", "pussy lick gif", "classic", "boobs", "anal"],
        }

        async with self.session.get(self.endpoints_url) as response:
            if response.ok:
                js = await response.json(encoding="utf-8")
                for endpoint in js:
                    if "/api/v2/img/" in endpoint:
                        categories = [category.group(1) for category in re.finditer(r"'(\w+)'", endpoint)]

                        value: str
                        for name in data["sfw"]:
                            value = self.sfw_converter.get(name, name)
                            if value not in categories:
                                self.bot.log(f"Warning in NekosLife: no SFW endpoint called '{value}' (corresponding name '{name}')")

                        for name in data["nsfw"]:
                            value = self.nsfw_converter.get(name, name)
                            if value not in categories:
                                self.bot.log(f"Warning in NekosLife: no NSFW endpoint called '{value}' (corresponding name '{name}')")

                        return data["sfw"], data["nsfw"]

            return [], []

    async def get(self, category: str, *, mode: Literal["sfw", "nsfw"]) -> Optional[str]:
        if mode == "sfw":
            category = self.sfw_converter.get(category, category)
        else:
            category = self.nsfw_converter.get(category, category)

        url = f"https://nekos.life/api/v2/img/{category}"
        async with self.session.get(url) as response:
            if response.status == 200:
                json = await response.json(encoding="utf-8")
                return json["url"]

        return


class Asuna(ImageSource):

    __slots__ = (
        "session",
        "client",
    )
    endpoints_url: ClassVar[str] = "https://asuna.ga/api"
    converter: ClassVar[Dict[str, str]] = {
        "fox": "wholesome_foxes",
    }

    async def _get_all_endpoints(self) -> Tuple[List[str], List[str]]:
        data = {
            "sfw": ["hug", "kiss", "neko", "pat", "slap", "fox"],
            "nsfw": [],
        }

        async with self.session.get(self.endpoints_url) as response:
            if response.ok:
                json = await response.json(encoding="utf-8")
                endpoints = json["allEndpoints"]

                for name in data["sfw"]:
                    value = self.converter.get(name, name)
                    if value not in endpoints:
                        self.bot.log(f"Warning in Asuna: no SFW endpoint called '{value}' (corresponding name '{name}')")

                return data["sfw"], data["nsfw"]

            return [], []

    async def get(self, category: str, *, mode: Literal["sfw", "nsfw"]) -> Optional[str]:
        category = self.converter.get(category, category)
        async with self.session.get(f"https://asuna.ga/api/{category}") as response:
            if response.ok:
                json = await response.json(encoding="utf-8")
                return json["url"]

        return


class ImageClient(Generic[IT]):
    """Represents a client that is used to interact with all
    ImageSource objects.

    Attributes
    -----
    bot: ``haruka.Haruka``
        The bot associated with this image client.
    session: ``aiohttp.ClientSession``
        The ``aiohttp.ClientSession`` used to interact with
        the ``ImageSource`` that this client contains.
    sfw: Dict[``str``, List[``ImageSource``]]
        A mapping of SFW categories with all ``ImageSource``
        that can listen to it.
    nsfw: Dict[``str``, List[``ImageSource``]]
        A mapping of NSFW categories with all ``ImageSource``
        that can listen to it.
    sources: List[Type[``ImageSource``]]
        All the ``ImageSource`` that this client contains.
    """
    __slots__ = (
        "_ready",
        "bot",
        "sfw",
        "nsfw",
        "session",
        "sources",
    )
    if TYPE_CHECKING:
        _ready: asyncio.Event
        bot: haruka.Haruka
        session: aiohttp.ClientSession
        sources: List[Type[IT]]
        sfw: Dict[str, List[IT]]
        nsfw: Dict[str, List[IT]]

    def __init__(self, bot: haruka.Haruka, *sources) -> None:
        self._ready = asyncio.Event()
        self.bot = bot
        self.session = bot.session
        self.sources = sources
        asyncio.create_task(self._load())

    async def _load(self) -> None:
        """This function is a coroutine

        Register all image categories that this client can listen to.
        This method is scheduled right when this class is initialized.
        """
        self.sfw = {}
        self.nsfw = {}

        await asyncio.gather(*[self._register(source(self.session, self)) for source in self.sources])
        self.bot.log(f"Loaded {len(self.sources)} ImageSource objects.")
        self._ready.set()

    async def _register(self, source: IT) -> None:
        """This function is a coroutine

        Register all endpoints that a ``ImageSource`` can listen
        to and add them to the client listener.

        Parameters
        -----
        source: ``ImageSource``
            The ``ImageSource`` to analyze.
        """
        if not isinstance(source, ImageSource):
            raise TypeError(f"source must be ImageSource, not {source.__class__.__name__}")

        sfw, nsfw = await source._get_all_endpoints()

        for endpoint in sfw:
            if endpoint not in self.sfw:
                self.sfw[endpoint] = [source]
            else:
                self.sfw[endpoint].append(source)

        for endpoint in nsfw:
            if endpoint not in self.nsfw:
                self.nsfw[endpoint] = [source]
            else:
                self.nsfw[endpoint].append(source)

        self.bot.log(f"Loaded {len(sfw)} SFW endpoints and {len(nsfw)} NSFW endpoints from {source.__class__.__name__}")

    async def wait_until_ready(self) -> None:
        """This function is a coroutine
        
        Asynchronously block until all image categories have
        been loaded.
        """
        await self._ready.wait()

    async def get(self, category: str, *, mode: Literal["sfw", "nsfw"] = "sfw") -> Optional[str]:
        """This function is a coroutine

        Get a URL from the requested category. If the requested
        category was not registered, this method will raise
        ``CategoryNotFound``.

        Note that although the category was registered, the
        fetching operation may still fall somehow and ``None``
        is returned instead.

        Parameters
        -----
        category: ``str``
            The image category to fetch URL.

        mode: Literal["sfw", "nsfw"]
            Whether the category belongs to the SFW or NSFW
            collections.

        Returns
        -----
        Optional[``str``]
            The image URL.

        Exceptions
        -----
        ``CategoryNotFound``
            The category does not exist in the requested mode
            (SFW or NSFW).
        """
        if category not in self.sfw and mode == "sfw":
            raise CategoryNotFound(category)

        if category not in self.nsfw and mode == "nsfw":
            raise CategoryNotFound(category)

        if mode == "sfw":
            random.shuffle(self.sfw[category])

            for source in self.sfw[category]:
                image_url = await source.get(category, mode="sfw")
                if image_url:
                    return image_url

        elif mode == "nsfw":
            random.shuffle(self.nsfw[category])

            for source in self.nsfw[category]:
                image_url = await source.get(category, mode="nsfw")
                if image_url:
                    return image_url
