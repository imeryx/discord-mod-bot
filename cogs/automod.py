import discord
from discord.ext import commands
from discord import app_commands
import database
from cogs.moderation import apply_auto_punishment 

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Dictionary dùng làm Bộ nhớ đệm (Cache). Cấu trúc: {guild_id: ["từ_1", "từ_2"]}
        self.word_cache = {}

    @commands.Cog.listener()
    async def on_ready(self):
        print("-> Cog [AutoMod] đã khởi động cùng hệ thống Caching và Auto-Punish!")

    # Hàm hỗ trợ tải dữ liệu từ DB lên Cache cho 1 server
    def load_cache(self, guild_id):
        words = database.get_badwords(guild_id)
        self.word_cache[guild_id] = words
        return words

    # ================= CÁC LỆNH QUẢN LÝ TỪ CẤM =================
    @app_commands.command(name="addword", description="Thêm một từ vào danh sách cấm của server")
    @app_commands.default_permissions(manage_guild=True)
    async def addword(self, interaction: discord.Interaction, word: str):
        word = word.lower()
        success = database.add_badword(interaction.guild.id, word)
        
        if success:
            # Cập nhật lại Cache ngay lập tức
            self.load_cache(interaction.guild.id)
            await interaction.response.send_message(f"✅ Đã thêm từ `{word}` vào danh sách cấm!", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Từ `{word}` đã có sẵn trong danh sách cấm rồi!", ephemeral=True)

    @app_commands.command(name="removeword", description="Xóa một từ khỏi danh sách cấm")
    @app_commands.default_permissions(manage_guild=True)
    async def removeword(self, interaction: discord.Interaction, word: str):
        success = database.remove_badword(interaction.guild.id, word.lower())
        
        if success:
            self.load_cache(interaction.guild.id)
            await interaction.response.send_message(f"🗑️ Đã xóa từ `{word}` khỏi danh sách cấm!", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Không tìm thấy từ `{word}` trong danh sách cấm.", ephemeral=True)

    @app_commands.command(name="listwords", description="Xem danh sách các từ bị cấm hiện tại")
    @app_commands.default_permissions(manage_guild=True)
    async def listwords(self, interaction: discord.Interaction):
        # Ưu tiên lấy từ Cache để phản hồi cực nhanh
        words = self.word_cache.get(interaction.guild.id) 
        
        # Nếu Cache trống, thử load từ DB
        if words is None:
            words = self.load_cache(interaction.guild.id)
            
        if not words:
            return await interaction.response.send_message("Server này hiện chưa có từ cấm nào.", ephemeral=True)
            
        # Nối các từ lại bằng dấu phẩy
        word_list = ", ".join([f"`{w}`" for w in words])
        await interaction.response.send_message(f"📜 **Danh sách từ cấm:**\n{word_list}", ephemeral=True)
        
    # ================= THIẾT LẬP NATIVE AUTOMOD ĐỂ NHẬN BADGE =================
    @app_commands.command(name="automod_setup", description="Tự động cài đặt lớp khiên AutoMod chính chủ của Discord")
    @app_commands.default_permissions(administrator=True)
    async def automod_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        
        try:
            # Quy tắc 1: Lọc ngôn từ độc hại (Sử dụng hệ thống bộ lọc có sẵn của Discord)
            await guild.create_automod_rule(
                name="🛡️ Elfaria - Lọc ngôn từ độc hại",
                event_type=discord.AutoModRuleEventType.message_send,
                trigger_type=discord.AutoModRuleTriggerType.keyword_preset,
                trigger_metadata=discord.AutoModTriggerMetadata(
                    presets=[1, 2, 3]  # 1: Từ tục tĩu, 2: Nội dung người lớn, 3: Xúc phạm/Slurs
                ),
                actions=[discord.AutoModRuleAction(type=discord.AutoModRuleActionType.block_message)],
                enabled=True
            )

            # Quy tắc 2: Tự động chặn tin nhắn bị nghi ngờ là Spam
            await guild.create_automod_rule(
                name="🛡️ Elfaria - Chống Spam",
                event_type=discord.AutoModRuleEventType.message_send,
                trigger_type=discord.AutoModRuleTriggerType.spam,
                actions=[discord.AutoModRuleAction(type=discord.AutoModRuleActionType.block_message)],
                enabled=True
            )

            # Quy tắc 3: Chặn các liên kết lừa đảo/Phishing
            await guild.create_automod_rule(
                name="🛡️ Elfaria - Chống Link Độc",
                event_type=discord.AutoModRuleEventType.message_send,
                trigger_type=discord.AutoModRuleTriggerType.harmful_link,
                actions=[discord.AutoModRuleAction(type=discord.AutoModRuleActionType.block_message)],
                enabled=True
            )
            
            await interaction.followup.send("✅ Đã thiết lập thành công 3 quy tắc lớp khiên thép AutoMod chính thức cho Server này!")
            
        except discord.Forbidden:
            await interaction.followup.send("❌ Bot không có đủ quyền `Quản lý Server` (Manage Server) để tạo bộ lọc.")
        except discord.HTTPException as e:
            if e.code == 50035:
                await interaction.followup.send("⚠️ Server này đã có sẵn một số quy tắc AutoMod rồi, hãy kiểm tra lại nhé!")
            else:
                await interaction.followup.send(f"❌ Có lỗi mạng xảy ra từ phía Discord: {e}")

    # ================= BỘ LỌC TIN NHẮN TỰ ĐỘNG =================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Bỏ qua tin nhắn của bot hoặc tin nhắn nhắn riêng (DM)
        if message.author.bot or not message.guild:
            return

        guild_id = message.guild.id
        
        # Lấy danh sách từ cấm từ Cache
        bad_words = self.word_cache.get(guild_id)
        
        # Nếu server này chưa có trong Cache, tiến hành load từ Database
        if bad_words is None:
            bad_words = self.load_cache(guild_id)

        # Nếu server không có cài đặt từ cấm nào, bỏ qua luôn
        if not bad_words:
            return

        content_lower = message.content.lower()

        # Kiểm tra vi phạm
        for word in bad_words:
            if word in content_lower:
                try:
                    # Xóa tin nhắn vi phạm
                    await message.delete()
                    
                    # Cảnh báo ra kênh chat
                    await message.channel.send(
                        f"⚠️ {message.author.mention}, tin nhắn của bạn đã bị xóa vì chứa từ ngữ vi phạm!", 
                        delete_after=5.0
                    )
                    
                    # Ghi vi phạm vào Database và hứng lấy tổng số cảnh báo hiện tại
                    warn_count = database.add_warning(
                        guild_id=guild_id,
                        user_id=message.author.id,
                        moderator_id=self.bot.user.id, 
                        reason=f"Auto-Mod: Sử dụng từ cấm ({word})"
                    )
                    
                    # Gọi hệ thống phạt tự động (Timeout/Kick/Ban) dựa trên số cảnh báo
                    await apply_auto_punishment(message, message.author, warn_count)
                    
                    # Dừng vòng lặp kiểm tra nếu đã phát hiện lỗi
                    break 
                
                except discord.Forbidden:
                    # Bỏ qua nếu bot bị thiếu quyền xóa tin nhắn ở một kênh nào đó
                    pass
                except Exception as e:
                    print(f"Lỗi Auto-Mod: {e}")

# Đảm bảo 2 dòng này nằm sát lề trái và chữ await chỉ lùi vào đúng 1 tab (4 dấu cách)
async def setup(bot):
    await bot.add_cog(AutoMod(bot))