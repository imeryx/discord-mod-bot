import discord
from discord.ext import commands
from discord import app_commands
from deep_translator import GoogleTranslator

class TranslatorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # 1. INITIALIZE CONTEXT MENU
        self.ctx_menu = app_commands.ContextMenu(
            name='Translate to Vietnamese',
            callback=self.translate_context_menu,
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        # Clean up the menu when unloading the cog to prevent duplicates
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    @commands.Cog.listener()
    async def on_ready(self):
        print("-> Cog [Translator] loaded successfully!")

    # ========================================================
    # FEATURE 1: RIGHT-CLICK CONTEXT MENU TRANSLATION
    # ========================================================
    async def translate_context_menu(self, i: discord.Interaction, message: discord.Message):
        # Ephemeral response so only the user who clicked can see the translation
        await i.response.defer(ephemeral=True)
        
        if not message.content:
            return await i.followup.send("⚠️ No text found in this message to translate!")

        try:
            # Auto-detect source language and translate to Vietnamese ('vi')
            translated = GoogleTranslator(source='auto', target='vi').translate(message.content)
            
            embed = discord.Embed(title="🌐 Translation Result", color=0x007BFF)
            embed.add_field(name="Original Message", value=message.content[:1024], inline=False)
            embed.add_field(name="Translated (VI)", value=translated[:1024], inline=False)
            embed.set_footer(text=f"Translated for {i.user.name} | Powered by Google Translate")
            
            await i.followup.send(embed=embed)
        except Exception as e:
            await i.followup.send(f"❌ An error occurred during translation: {e}")

    # ========================================================
    # FEATURE 2: NORMAL SLASH COMMAND
    # ========================================================
    @app_commands.command(name="translate", description="Translate text to any language")
    @app_commands.describe(
        text="The text you want to translate", 
        target_lang="Target language code (e.g., vi, en, ja, ko) - Default is Vietnamese"
    )
    async def translate_slash(self, i: discord.Interaction, text: str, target_lang: str = 'vi'):
        await i.response.defer()
        try:
            # Translate to the specified language (defaults to Vietnamese)
            translated = GoogleTranslator(source='auto', target=target_lang).translate(text)
            
            embed = discord.Embed(title="🌐 Global Translator", color=0x007BFF)
            embed.add_field(name="Original", value=text[:1024], inline=False)
            embed.add_field(name=f"Translated ({target_lang.upper()})", value=translated[:1024], inline=False)
            
            await i.followup.send(embed=embed)
        except Exception as e:
            await i.followup.send(f"❌ Translation error. Please check the language code or text length.\nDetails: {e}")

    # ========================================================
    # FEATURE 3: PREFIX COMMAND FOR REPLIED MESSAGES
    # ========================================================
    @commands.command(name="translate")
    async def translate_reply(self, ctx, target_lang: str = 'vi'):
        # Check if the command message is replying to another message
        if ctx.message.reference and ctx.message.reference.message_id:
            try:
                # Fetch the original message that is being replied to
                replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                text_to_translate = replied_message.content

                if not text_to_translate:
                    return await ctx.reply("⚠️ No text found in the replied message to translate!")

                # Translate the text (defaults to Vietnamese)
                translated = GoogleTranslator(source='auto', target=target_lang).translate(text_to_translate)

                embed = discord.Embed(title="🌐 Reply Translation Result", color=0x007BFF)
                embed.add_field(name="Original Message", value=text_to_translate[:1024], inline=False)
                embed.add_field(name=f"Translated ({target_lang.upper()})", value=translated[:1024], inline=False)
                embed.set_footer(text=f"Requested by {ctx.author.name} | Powered by Google Translate")

                # Reply directly to the user's command message
                await ctx.reply(embed=embed)
                
            except Exception as e:
                await ctx.reply(f"❌ Failed to fetch or translate the message: {e}")
        else:
            # Guide the user if they use the prefix command without replying to anyone
            await ctx.reply("💡 To translate a specific message, please **reply** to it and type this command (e.g., `!translate`).")

# ========================================================
# ENTRY POINT (CRUCIAL FOR LOADING THE COG)
# ========================================================
async def setup(bot):
    await bot.add_cog(TranslatorCog(bot))