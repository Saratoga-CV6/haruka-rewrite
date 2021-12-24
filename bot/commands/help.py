import asyncio
import sys
from typing import Dict, List, Mapping, Optional

import discord
from discord.ext import commands

import utils
import emoji_ui
from core import bot, prefix


class CustomHelpCommand(commands.MinimalHelpCommand):
    def __init__(self):
        command_attrs: Dict[str, str] = {
            "name": "help",
            "description": "Get all available commands or for a specific command.",
            "usage": "help\nhelp <command>",
            "cooldown": commands.CooldownMapping(
                commands.Cooldown(1, 3),
                commands.BucketType.user,
            ),
        }
        super().__init__(command_attrs=command_attrs)

    @staticmethod
    def template(page: int, pref: str) -> discord.Embed:
        em: discord.Embed = discord.Embed(
            title=f"{bot.user} command list",
            description=f"You can also invoke command with <@!{bot.user.id}> as a prefix.\nTo get help on a command, type `{pref}help <command>`.",
            color=0x2ECC71,
        )
        em.set_thumbnail(url=bot.user.avatar.url)
        em.set_footer(text=f"Current prefix: {pref} | Page {page}/4")
        return em

    async def send_bot_help(self, mapping: Mapping[Optional[commands.Cog], List[commands.Command]]):
        # Initialize
        pref: str = await prefix(bot, self.context.message)
        help_em: List[discord.Embed] = []

        # Page 1
        em: discord.Embed = self.template(1, pref)
        em.add_field(
            name="💬 General",
            value="```\nabout, avatar, emoji, help, info, invite, prefix, remind, say, source, svinfo\n```",
            inline=False,
        )
        em.add_field(
            name="✨ Fun",
            value="```\n8ball, card, fact, hangman, ping, quote, rickroll, roll\n```",
            inline=False
        )
        em.add_field(
            name="🔍 Searching",
            value="```\nanime, manga, nhentai, pixiv, sauce, urban, youtube\n```",
        )
        help_em.append(em)

        # Page 2
        em: discord.Embed = self.template(2, pref)
        em.add_field(
            name="🖼️ Images",
            value="```\nnsfw, sfw\n```",
            inline=False,
        )
        em.add_field(
            name="🎶 Music",
            value="```\nadd, dashboard, myplaylist, pause, play, playlist, publish, queue, remove, repeat, resume, shuffle, skip, stop, stopafter, unpublish, vping\n```",
            inline=False,
        )
        em.add_field(
            name="🛡️ Moderation",
            value="```\nban, kick, mute, unmute\n```",
            inline=False,
        )
        help_em.append(em)

        # Page 3
        em: discord.Embed = self.template(3, pref)
        em.add_field(
            name="🖼️ SFW images",
            value=f"Remember to add the prefix `{pref}`! E.g. `{pref}*waifu`\n" + self._sfw_description,
            inline=False,
        )
        help_em.append(em)

        # Page 4
        em: discord.Embed = self.template(4, pref)
        em.add_field(
            name="🔞 NSFW images",
            value=f"Remember to add the prefix `{pref}`! E.g. `{pref}**waifu`\n" + self._nsfw_description,
            inline=False,
        )
        help_em.append(em)

        display: emoji_ui.Pagination = emoji_ui.Pagination(help_em)
        await display.send(self.context)

    async def send_command_help(self, command: commands.Command):
        # Fetch server's prefix
        pref: str = await prefix(bot, self.context.message)

        if command.aliases and command.qualified_name not in command.aliases:
            command.aliases.insert(0, command.qualified_name)
        elif not command.aliases:
            command.aliases = [command.qualified_name]

        command.usage = command.usage if command.usage else command.qualified_name
        usage: str = command.usage.replace("\n", f"\n{pref}")

        description: str = command.description.format(pref)

        cooldown: commands.CooldownMapping = command._buckets
        cooldown_notify: str = "**Cooldown**\nNo cooldown"

        _cd_time: float = cooldown._cooldown.per
        if cooldown._cooldown:
            cooldown_notify = f"**Cooldown**\n{utils.format(_cd_time)} per {cooldown._type.name}"

        if command.name == "sfw":
            description += ", ".join(f"`{key}`" for key in self.sfw_keys)

        elif command.name == "nsfw":
            description += ", ".join(f"`{key}`" for key in self.nsfw_keys)

        em: discord.Embed = discord.Embed(
            title=command.qualified_name,
            description=f"```\n{pref}{usage}\n```\n**Description**\n{description}\n**Aliases**\n" + ", ".join(f"`{alias}`" for alias in command.aliases) + "\n" + cooldown_notify,
            color=0x2ECC71,
        )
        em.set_author(name=f"{self.context.author.name}, this is an instruction for {command.qualified_name}!", icon_url=self.context.author.avatar.url if self.context.author.avatar else discord.Embed.Empty)
        await self.context.send(embed=em)

    async def prepare_help_command(self, ctx: commands.Context, command: Optional[str] = None) -> None:
        self.sfw_keys: List[str] = list(ctx.bot.image.sfw.keys())
        self.sfw_keys.sort()
        self._sfw_description: str = "```\n" + ", ".join(f"*{s.replace(' ', '_')}" for s in self.sfw_keys) + "\n```"

        self.nsfw_keys: List[str] = list(ctx.bot.image.nsfw.keys())
        self.nsfw_keys.sort()
        self._nsfw_description: str = "```\n" + ", ".join(f"**{s.replace(' ', '_')}" for s in self.nsfw_keys) + "\n```"

    async def command_not_found(self, string: str) -> str:
        if len(string) > 20:
            return "There is no such long command."

        args: List[str]
        if sys.platform == "win32":
            args = ["py"]
        else:
            args = ["python"]
        args.append("./bot/levenshtein.py")
        args.append(string)
        args.extend(bot.all_commands.keys())

        process: asyncio.subprocess.Process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await process.communicate()
        word: str = stdout.decode("utf-8").replace("\n", "").replace("\r", "")
        return f"No command called `{string}` was found. Did you mean `{word}`?"


bot.help_command = CustomHelpCommand()
