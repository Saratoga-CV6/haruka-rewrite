from __future__ import annotations

import enum
from typing import Tuple, TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from .core import BaseCreature
    from .player import PT


__all__ = (
    "battle",
)


class BattleStatus(enum.Enum):
    WIN: int = 0
    LOSS: int = 1
    DRAW: int = 2


def battle(player: PT, enemy: BaseCreature) -> discord.Embed:
    turn: int = 0
    status: BattleStatus
    entities: Tuple[PT, BaseCreature] = (player, enemy)

    while player.hp > 0 and enemy.hp > 0:
        turn += 1
        for index, entity in enumerate(entities):
            target = entities[1 - index]
            entity.attack(target)

            if player.hp <= 0 or enemy.hp <= 0:  # The damage may be reflected somehow
                if player.hp > 0:
                    status = BattleStatus.WIN
                elif enemy.hp > 0:
                    status = BattleStatus.LOSS
                else:
                    status = BattleStatus.DRAW
                break

    embed: discord.Embed = discord.Embed()
    embed.set_author(name=f"⚔️ {player.name} challenged {enemy.name}")
    embed.add_field(
        name=f"{player.display} {player.name}",
        value=f"HP {player.hp}/{player.hp_max}",
        inline=True,
    )
    embed.add_field(
        name=f"{enemy.name} {enemy.display}",
        value=f"HP {enemy.hp}/{enemy.hp_max}",
        inline=True,
    )

    if status == BattleStatus.WIN:
        embed.color = 0x2ECC71
        embed.set_footer(text=f"{player.name} won!")
    elif status == BattleStatus.LOSS:
        embed.color = 0xED4245
        embed.set_footer(text=f"{enemy.name} won!")
    else:
        embed.color = 0x95a5a6
        embed.set_footer(text="Draw!")

    return embed
