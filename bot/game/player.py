from __future__ import annotations

import asyncio
import dataclasses
import datetime
import functools
import math
import random
from functools import cached_property
from typing import Any, Generic, List, Optional, Type, TypeVar, Union

import asyncpg
import discord

import utils
from .abc import Battleable, ClassObject
from .core import LT, WT


__all__ = (
    "BasePlayer",
    "BaseItem",
)


PT = TypeVar("PT", bound="BasePlayer")
IT = TypeVar("IT", bound="BaseItem")
EXP_SCALE: int = 4


@dataclasses.dataclass(init=True, repr=True, order=False, frozen=False)
class BasePlayer(Battleable, Generic[LT, WT]):
    """Base class for players from different worlds

    Each player is represented with an instance of a subclass of this class and
    they should be cached efficiently.

    Attributes
    -----
    name: :class:`str`
        The player's name, which is the same as Discord name
    id: :class:`int`
        The player's ID, which is the same as Discord ID
    description: :class:`str`
        The player's description
    world: :class:`BaseWorld`
        The world the player is currently in
    location: :class:`BaseLocation`
        The location the player is currently in
    level: :class:`int`
        The player's level
    xp: :class:`int`
        The player's experience point
    money: :class:`int`
        The player's money
    items: List[:class:`BaseItem`]
        The player's items
    hp: :class:`int`
        The player's current health point
    display: :class:`str`
        The emoji to display the player, this does not need
        to be a Unicode emoji
    """

    user: discord.User
    description: str
    world: Type[WT]
    location: Type[LT]
    level: int
    xp: int
    money: int
    items: List[IT]
    hp: int
    display: str

    @property
    def name(self) -> str:
        return self.user.name

    @property
    def id(self) -> int:
        return self.user.id

    @property
    def client_user(self) -> discord.ClientUser:
        return self.user._state.user

    @classmethod
    @property
    def type_id(self) -> int:
        raise NotImplementedError

    @cached_property
    def travel_lock(self) -> asyncio.Lock:
        return asyncio.Lock()

    def calc_distance(self, destination: Type[LT]) -> float:
        """Calculate the moving distance between the player and
        a location of the same world

        Parameters
        -----
        destination: Type[:class:`BaseLocation`]
            The location to travel to

        Returns
        -----
        :class:`float`
            The distance to travel
        """
        _dx: int = self.location.coordination.x - destination.coordination.x
        _dy: int = self.location.coordination.y - destination.coordination.y
        distance: float = math.sqrt(_dx ** 2 + _dy ** 2)
        return distance

    async def travel_to(
        self,
        channel: discord.TextChannel,
        destination: Type[LT],
    ) -> None:
        """This function is a coroutine

        Travel to the destination location.

        Parameters
        -----
        target: :class:`discord.TextChannel`
            The target Discord channel to send messages to
        destination: Type[:class:`BaseLocation`]
            The location to travel to
        """
        if self.travel_lock.locked():
            return await channel.send(f"You have already been on a journey, please get to the destination first!")

        async with self.travel_lock:
            distance: float = self.calc_distance(destination)
            _dest_time: datetime.datetime = discord.utils.utcnow() + datetime.timedelta(seconds=distance)
            await channel.send(f"Travelling to **{destination.name}**. You will arrive after {utils.format(distance)}")
            await discord.utils.sleep_until(_dest_time)
            self.location = destination

            for event in self.world.events:
                if event.location.id == self.location.id:
                    if random.random() < event.rate:
                        await event.run(channel, self)

    def gain_xp(self, exp: int) -> bool:
        """Increase the player's experience point and handle
        any calculation logics.

        Parameters
        -----
        exp: :class:`int`
            The amount of experience points to increase

        Returns
        -----
        :class:`bool`
            Returns ``True`` if the player leveled up, ``False``
            otherwise
        """
        self.xp += exp
        ret: bool = False

        while self.xp >= EXP_SCALE * self.level:
            self.xp -= EXP_SCALE * self.level
            self.level += 1
            ret = True

        return ret

    def isekai(self) -> Type[WT]:
        """Transfer this player to another world

        Returns
        -----
        :class:`BaseWorld`
            The new world
        """
        from .core import BaseWorld
        from .worlds import EarthWorld

        worlds: List[Type[WT]] = BaseWorld.__subclasses__()
        worlds.remove(EarthWorld)  # Imagine isekai back to earth
        world: Type[WT] = random.choice(worlds)
        self.world = world
        self.location = world.locations[0]
        return world

    def create_embed(self) -> discord.Embed:
        """Create an embed represents basic information about
        this player
        """
        embed: discord.Embed = discord.Embed(
            description=f"Lv.{self.level} (EXP {self.xp}/{EXP_SCALE * self.level})",
            color=0x2ECC71,
            timestamp=discord.utils.utcnow(),
        )

        embed.add_field(
            name="Class",
            value=f"{self.display} {self.__class__.__name__}",
            inline=False,
        )
        embed.add_field(
            name="HP",
            value=f"{self.hp}/{self.hp_max}",
        )
        embed.add_field(
            name="Physical ATK",
            value=self.physical_atk,
        )
        embed.add_field(
            name="Magical ATK",
            value=self.magical_atk,
        )
        embed.add_field(
            name="Physical RES",
            value="{:.2f}%".format(100 * self.physical_res),
        )
        embed.add_field(
            name="Magical RES",
            value="{:.2f}%".format(100 * self.magical_res),
        )
        embed.add_field(
            name="CRIT Attack",
            value="CRIT Rate {:.2f}%".format(100 * self.crit_rate) + "\nCRIT DMG {:.2f}%".format(100 * self.crit_dmg),
        )

        embed.set_thumbnail(url=self.user.avatar.url if self.user.avatar else discord.Embed.Empty)
        embed.set_author(
            name=f"{self.user} Information",
            icon_url=self.client_user.avatar.url,
        )

        return embed

    def map_world(self) -> discord.Embed:
        """Create an embed represents basic information about
        the player's world
        """
        embed: discord.Embed = discord.Embed(
            title=self.world.name,
            description=self.world.description,
            color=0x2ECC71,
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(
            name="World ID",
            value=self.world.id,
        )
        embed.add_field(
            name="Locations",
            value="\n".join(f"{location.name} ({location.coordination.x}, {location.coordination.y})" for location in self.world.locations),
        )
        embed.set_thumbnail(url=self.user.avatar.url if self.user.avatar else discord.Embed.Empty)
        embed.set_author(
            name="World Information",
            icon_url=self.client_user.avatar.url,
        )
        return embed

    # Logical operations

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return self.id == other.id
        return False

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    # Save and load operations

    async def update(self) -> None:
        """This function is a coroutine

        Save this player's data to the database.
        """
        conn: Union[asyncpg.Connection, asyncpg.Pool] = self.user._state.conn
        await conn.execute(
            f"UPDATE rpg \
            SET description = $1, world = $2, location = $3, \
                type = $4, level = $5, xp = $6, money = $7, \
                items = $8, hp = $9, display = $10 \
            WHERE id = '{self.id}';",
            self.description,
            self.world.id,
            self.location.id,
            self.type_id,
            self.level,
            self.xp,
            self.money,
            [item.id for item in self.items],
            self.hp,
            self.display,
        )

    @classmethod
    async def from_user(cls: Type[PT], user: discord.User) -> Optional[PT]:
        """This function is a coroutine

        Get a player object from a Discord user

        Parameters
        -----
        user: :class:`discord.User`
            The Discord user

        Returns
        -----
        Optional[:class:`BasePlayer`]
            The retrieved player, or ``None`` if not found
        """
        from .core import BaseWorld

        conn: Union[asyncpg.Connection, asyncpg.Pool] = user._state.conn
        row: asyncpg.Record = await conn.fetchrow(f"SELECT * FROM rpg WHERE id = '{user.id}';")
        if not row:
            return

        world: Type[WT] = BaseWorld.from_id(row["world"])
        location: Type[LT] = world.get_location(row["location"])
        ptype: Type[PT] = world.get_player(row["type"])

        return ptype(
            user=user,
            description=row["description"],
            world=world,
            location=location,
            level=row["level"],
            xp=row["xp"],
            money=row["money"],
            items=[BaseItem.from_id(item_id) for item_id in row["items"]],
            hp=row["hp"],
            display=row["display"],
        )

    @classmethod
    async def make_new(cls: Type[PT], user: discord.User) -> Optional[PT]:
        """This function is a coroutine

        Create a new player from a Discord user

        Parameters
        -----
        user: :class:`discord.User`
            The Discord user

        Returns
        -----
        :class:`BasePlayer`
            The newly created player

        Exceptions
        -----
        :class:`ValueError`
            The player has already existed
        """
        conn: Union[asyncpg.Connection, asyncpg.Pool] = user._state.conn
        if await conn.fetchrow(f"SELECT * FROM rpg WHERE id = '{user.id}';"):
            raise ValueError("A player with the same ID exists")

        await conn.execute(
            f"INSERT INTO rpg \
            VALUES ('{user.id}', $1, $2, $3, $4, $5, $6, $7, $8, $9, $10);",
            "A new player",  # description
            0,  # world
            1,  # location
            0,  # type
            1,  # level
            0,  # exp
            50,  # money
            [],  # items
            100,  # hp
            "🧍",  # display
        )
        return await cls.from_user(user)


class BaseItem(ClassObject, Generic[PT]):
    """Base class for player items.

    All items must subclass this class. Please note that
    item objects are represented by the classes themselves,
    not by their instances.

    Attributes
    -----
    name: :class:`str`
        The item's name
    description: :class:`str`
        The item's description
    id: :class:`int`
        The item's id
    level: :class:`int`
        The item's level
    """
    __slots__ = (
        "level",
    )
    name: str
    description: str
    id: int

    def effect(self, user: PT, target: Optional[Battleable]) -> Any:
        """Perform calculation for the effect when a user consumes this item.

        Subclasses must implement this.

        Parameters
        -----
        user: :class:`BasePlayer`
            The player who consumed this item
        Optional[:class:`Battleable`]
            The effect target, if this item aims at another entity
        """
        raise NotImplementedError

    @classmethod
    @functools.cache
    def from_id(cls: Type[BaseItem], id: int) -> Optional[Type[IT]]:
        """Construct an item from an identification string

        Parameters
        -----
        id: :class:`int`
            The item ID

        Returns
        -----
        Optional[Type[:class:`BaseItem`]]
            The item with the given ID, or ``None`` if not found
        """
        for itype in cls.__subclasses__():
            if itype.id == id:
                return itype
