import traceback

import slash
from _types import Interaction
from core import bot


@bot.event
async def on_slash_command_error(interaction: Interaction, error: Exception):
    if isinstance(error, slash.NoPrivateMessage):
        await interaction.response.send_message("This command can only be invoked in a server channel.")

    elif isinstance(error, slash.CommandInvokeError):
        await on_slash_command_error(interaction, error.original)

    else:
        content = None
        if interaction.message:
            content = interaction.message.content
        bot.log(f"'{content}' in {interaction.channel_id}/{interaction.guild_id} from {interaction.user}:")
        bot.log("".join(traceback.format_exception(error.__class__, error, error.__traceback__)))
        await bot.report("An error has just occured and was handled by `on_slash_command_error`", send_state=False)
