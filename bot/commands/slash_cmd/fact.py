from typing import Any, Dict

import discord

import leech
from core import bot


json: Dict[str, Any] = {
    "name": "fact",
    "type": 1,
    "description": "Send you a random fact.",
}


@bot.slash(json)
async def _fact_slash(interaction: discord.Interaction):
    await interaction.response.send_message(leech.get_fact())