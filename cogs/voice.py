import discord
from discord.ext import commands
from discord import app_commands

class VoiceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="join", description="Make the bot join your current Voice channel to AFK")
    async def join(self, i: discord.Interaction):
        # 1. Check if the user is currently in a voice channel
        if not i.user.voice or not i.user.voice.channel:
            return await i.response.send_message("❌ You must join a Voice channel first!", ephemeral=True)

        voice_channel = i.user.voice.channel

        # 2. Check if the bot is already in a voice channel within this server
        if i.guild.voice_client:
            if i.guild.voice_client.channel == voice_channel:
                return await i.response.send_message("🤖 I'm already sitting in this channel!", ephemeral=True)
            else:
                # If the bot is in another channel, move it to the user's channel
                await i.guild.voice_client.move_to(voice_channel)
                return await i.response.send_message(f"🏃 Moved to **{voice_channel.name}**")

        # 3. Connect to the new voice channel
        try:
            await voice_channel.connect()
            
            # Automatically Deafen to save bandwidth and indicate the bot is AFK
            await i.guild.change_voice_state(channel=voice_channel, self_mute=False, self_deaf=True)
            
            await i.response.send_message(f"✅ Successfully joined **{voice_channel.name}**!")
        except discord.ClientException:
            await i.response.send_message("❌ Cannot connect. I might be missing the `Connect` permission in this channel.", ephemeral=True)
        except Exception as e:
            await i.response.send_message(f"❌ An error occurred: `{e}`", ephemeral=True)

    @app_commands.command(name="leave", description="Request the bot to leave the Voice channel")
    async def leave(self, i: discord.Interaction):
        # Check if the bot is actually connected to a voice channel
        if i.guild.voice_client:
            await i.guild.voice_client.disconnect()
            await i.response.send_message("👋 Disconnected from the Voice channel. See ya!")
        else:
            await i.response.send_message("❌ I'm not hanging out in any Voice channel right now!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(VoiceCog(bot))