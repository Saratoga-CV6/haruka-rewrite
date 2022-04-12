from typing import List, Literal

import discord
from discord import app_commands

from _types import Interaction
from core import bot
from lib import image


async def create_image_slash_command() -> None:
    await bot.image.wait_until_ready()

    sfw_keys = sorted(bot.image.sfw.keys())
    nsfw_keys = sorted(bot.image.nsfw.keys())

    class _ImageSlashCommand(app_commands.Group):
        @app_commands.command(name="sfw", description="Get a random SFW image")
        @app_commands.describe(category="The image category")
        async def _sfw_slash(self, interaction: Interaction, category: str):
            await self._process_request(interaction, "sfw", category)

        @app_commands.command(name="nsfw", description="Get a random NSFW image")
        @app_commands.describe(category="The image category")
        async def _nsfw_slash(self, interaction: Interaction, category: str):
            try:
                if not interaction.channel.is_nsfw():
                    return await interaction.response.send_message("🔞 This command can only be invoked in a NSFW channel.")
            except AttributeError:
                return await interaction.response.send_message("Cannot process the command in this channel!")

            await self._process_request(interaction, "nsfw", category)

        async def _process_request(self, interaction: Interaction, mode: Literal["sfw", "nsfw"], category: str) -> None:
            await interaction.response.defer()

            try:
                image_url = await bot.image.get(category, mode=mode)
            except image.CategoryNotFound:
                return await interaction.followup.send(f"No category named `{category}` was found.")

            if image_url is None:
                return await interaction.followup.send("Cannot fetch any images from this category right now...")

            embed = discord.Embed()
            embed.set_image(url=image_url)
            embed.set_author(
                name="This is your image!",
                icon_url=bot.user.avatar.url,
            )
            await interaction.followup.send(embed=embed)

    @_ImageSlashCommand._sfw_slash.autocomplete("category")
    async def _sfw_autocomplete(interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
        await interaction.response.defer()
        result = [app_commands.Choice(name=sfw_key, value=sfw_key) for sfw_key in sfw_keys if current in sfw_key]
        return result[:25]

    @_ImageSlashCommand._nsfw_slash.autocomplete("category")
    async def _nsfw_autocomplete(interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
        await interaction.response.defer()
        result = [app_commands.Choice(name=nsfw_key, value=nsfw_key) for nsfw_key in nsfw_keys if current in nsfw_key]
        return result[:25]

    bot.tree.add_command(_ImageSlashCommand(name="image", description="Get a random anime image"))


bot._create_image_slash_command = create_image_slash_command()
