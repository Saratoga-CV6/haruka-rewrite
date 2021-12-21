from discord.ext import commands

import game
import utils
from core import bot
from game.core import PT


@bot.command(
    name="account",
    aliases=["acc"],
    description="View your RPG game account information",
)
@utils.testing()
@game.rpg_check()
@commands.cooldown(1, 3, commands.BucketType.user)
async def _account_cmd(ctx: commands.Context):
    player: PT = await game.BasePlayer.from_user(ctx.author)
    await ctx.send(embed=player.create_embed())
