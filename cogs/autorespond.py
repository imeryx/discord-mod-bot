import discord
from discord.ext import commands
from discord import app_commands
import database
import os
import aiohttp
import io
import re

class AutoRespond(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Regex pattern to identify Discord message link structures
        self.discord_msg_pattern = re.compile(r"https?://(?:ptb\.|canary\.)?discord\.com/channels/(\d+)/(\d+)/(\d+)")

    @commands.Cog.listener()
    async def on_ready(self):
        print("-> Cog [AutoRespond] V2 Ready (Integrated Discord CDN anti-expiration!)")

    # ================= CONFIGURATION COMMANDS =================
    @app_commands.command(name="add_response", description="Add an auto-response for the server")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(
        trigger="Trigger word or phrase (e.g., hello)",
        response="[Optional] Bot's text response",
        image_url="[Optional] Discord message link containing the image OR a regular image link"
    )
    async def add_response(self, interaction: discord.Interaction, trigger: str, response: str = None, image_url: str = None):
        if not response and not image_url:
            return await interaction.response.send_message("❌ You must provide a text response (`response`) or an image link (`image_url`)!", ephemeral=True)
        
        database.add_autoresponse(interaction.guild.id, trigger, response, image_url)
        
        msg = f"✅ AutoResponse added!\n• When someone types: `{trigger}`"
        if response:
            msg += f"\n• Bot will reply: **{response}**"
        if image_url:
            msg += f"\n• Saved image source: [Click to view]({image_url})"
            
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(name="remove_response", description="Remove an auto-response")
    @app_commands.default_permissions(manage_guild=True)
    async def remove_response(self, interaction: discord.Interaction, trigger: str):
        success = database.remove_autoresponse(interaction.guild.id, trigger)
        if success:
            await interaction.response.send_message(f"🗑️ Deleted auto-response for trigger `{trigger}`!", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ Could not find trigger `{trigger}` in the system.", ephemeral=True)

    @app_commands.command(name="list_responses", description="View the list of current auto-responses")
    @app_commands.default_permissions(manage_guild=True)
    async def list_responses(self, interaction: discord.Interaction):
        responses = database.get_autoresponses(interaction.guild.id)
        if not responses:
            return await interaction.response.send_message("⚠️ This server doesn't have any AutoResponses setup yet.", ephemeral=True)
        
        embed = discord.Embed(
            title="🤖 Auto-Response List",
            description="Below are the triggers and responses the bot has memorized:\n" + "━"*30,
            color=discord.Color.blurple()
        )
        
        for idx, (trig, resp, img) in enumerate(responses, 1):
            if resp:
                display_resp = resp if len(resp) <= 60 else resp[:57] + "..."
            else:
                display_resp = "*(Image only)*"
            
            # Display different icons depending on whether it's a normal link or a message link
            if img and "discord.com/channels" in img:
                img_status = " 🔗 *(Has image coordinates)*"
            elif img:
                img_status = " 📸 *(Has attached image)*"
            else:
                img_status = ""
            
            embed.add_field(
                name=f"{idx}. Trigger: `{trig}`",
                value=f"↳ **Reply:** {display_resp}{img_status}",
                inline=False 
            )
            
            if idx == 25:
                embed.set_footer(text=f"And many more triggers... (Showing first 25 items)")
                break
                
        if len(responses) <= 25:
            embed.set_footer(text=f"Total: {len(responses)} auto-responses.")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ================= MESSAGE LISTENER =================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        responses = database.get_autoresponses(message.guild.id)
        if not responses:
            return

        content_lower = message.content.lower().strip()

        for trigger, response, image_url in responses:
            if content_lower == trigger:
                try:
                    kwargs = {}
                    if response:
                        kwargs['content'] = response
                    
                    target_download_url = image_url

                    if image_url:
                        # 1. CHECK: Is this a Discord message link or a regular image link?
                        match = self.discord_msg_pattern.match(image_url)
                        if match:
                            _, channel_id, message_id = match.groups()
                            try:
                                # Fetch the original channel and message to bypass the 24h CDN limit
                                source_channel = self.bot.get_channel(int(channel_id))
                                if not source_channel:
                                    source_channel = await self.bot.fetch_channel(int(channel_id))
                                    
                                source_message = await source_channel.fetch_message(int(message_id))
                                
                                if source_message.attachments:
                                    # Generate a fresh CDN link
                                    target_download_url = source_message.attachments[0].url
                                else:
                                    target_download_url = None
                                    print("⚠️ Source message does not contain any image files!")
                            except discord.NotFound:
                                target_download_url = None
                                print("❌ The source message containing the AutoRespond image was deleted.")
                            except Exception as e:
                                target_download_url = None
                                print(f"❌ Could not fetch message coordinates: {e}")

                        # 2. DOWNLOAD IMAGE: Use the newly obtained link (or external link) to load into RAM
                        if target_download_url:
                            if target_download_url.startswith("http"):
                                async with aiohttp.ClientSession() as session:
                                    async with session.get(target_download_url) as resp:
                                        if resp.status == 200:
                                            content_type = resp.headers.get('Content-Type', '')
                                            if 'image' in content_type or 'video' in content_type:
                                                img_bytes = await resp.read()
                                                ext = content_type.split('/')[-1] 
                                                # Attach to payload as a normal file, no embed borders!
                                                kwargs['file'] = discord.File(io.BytesIO(img_bytes), filename=f"image.{ext}")
                                            else:
                                                # Fallback if the returned file format is unknown
                                                kwargs['content'] = f"{kwargs.get('content', '')}\n{target_download_url}".strip()
                            
                            elif os.path.exists(target_download_url):
                                filename = os.path.basename(target_download_url)
                                kwargs['file'] = discord.File(target_download_url, filename=filename)

                    # Send all data to the channel smoothly
                    if kwargs:
                        await message.channel.send(**kwargs)
                            
                except Exception as e:
                    print(f"Error sending AutoRespond: {e}")
                
                break 

async def setup(bot):
    await bot.add_cog(AutoRespond(bot))