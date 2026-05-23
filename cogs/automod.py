import discord
from discord.ext import commands
from discord import app_commands
import database
from cogs.moderation import apply_auto_punishment 
import aiohttp
import os

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

    # ================= CÁC LỆNH QUẢN LÝ TỪ CẤM (BOT-SIDE) =================
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


    # ================= THIẾT LẬP NATIVE AUTOMOD ĐỂ NHẬN BADGE (SERVER-SIDE) =================
    @app_commands.command(name="automod_setup", description="Tự động cài đặt 5 lớp khiên AutoMod chính chủ của Discord")
    @app_commands.default_permissions(administrator=True)
    async def automod_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        
        # Cấu hình JSON nguyên thủy gửi thẳng cho API Discord (Tránh lỗi phiên bản thư viện)
        rules = [
            # Quy tắc hệ thống 1: Ngôn từ độc hại
            {
                "name": "🛡️ Elfaria - Lọc ngôn từ độc hại",
                "event_type": 1,
                "trigger_type": 4, 
                "trigger_metadata": {"presets": [1, 2, 3]}, # 1: Tục tĩu, 2: 18+, 3: Xúc phạm
                "actions": [{"type": 1}], 
                "enabled": True
            },
            # Quy tắc hệ thống 2: Chống Spam tin nhắn
            {
                "name": "🛡️ Elfaria - Chống Spam",
                "event_type": 1,
                "trigger_type": 3,
                "actions": [{"type": 1}],
                "enabled": True
            },
            # Quy tắc hệ thống 3: Chống Spam Tag thành viên
            {
                "name": "🛡️ Elfaria - Chống Spam Tag",
                "event_type": 1,
                "trigger_type": 5, 
                "trigger_metadata": {"mention_total_limit": 5}, # Giới hạn tối đa 5 tag/tin nhắn
                "actions": [{"type": 1}],
                "enabled": True
            },
            # Quy tắc tùy chỉnh 4: Chặn link lừa đảo / Scam quà tặng free
            {
                "name": "🛡️ Elfaria - Chặn lừa đảo (Scam/Phishing)",
                "event_type": 1,
                "trigger_type": 1, # 1: Custom Keyword Filter
                "trigger_metadata": {
                    "keyword_filter": ["*nhận quân huy miễn phí*", "*free polychromes*", "*nhận nitro*", "*hack garena*", "*tặng thẻ game*"]
                },
                "actions": [{"type": 1}],
                "enabled": True
            },
            # Quy tắc tùy chỉnh 5: Chặn tin nhắn quảng cáo buôn bán trái phép / Tool hack
            {
                "name": "🛡️ Elfaria - Chặn quảng cáo rác/Tool Hack",
                "event_type": 1,
                "trigger_type": 1,
                "trigger_metadata": {
                    "keyword_filter": ["*bán tool*", "*hack token*", "*kéo rank*", "*mua data*", "*bán mã nguồn*"]
                },
                "actions": [{"type": 1}],
                "enabled": True
            }
        ]
        
        try:
            token = os.getenv('DISCORD_TOKEN')
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bot {token}",
                    "Content-Type": "application/json",
                    "X-Audit-Log-Reason": "Elfaria AutoMod Full Setup"
                }
                url = f"https://discord.com/api/v10/guilds/{guild.id}/auto-moderation/rules"
                
                success_count = 0
                for rule in rules:
                    async with session.post(url, json=rule, headers=headers) as resp:
                        if resp.status in (200, 201):
                            success_count += 1
                
                if success_count > 0:
                    await interaction.followup.send(f"✅ Đã thiết lập thành công {success_count}/5 quy tắc lớp khiên thép AutoMod chính thức cho Server này!")
                else:
                    await interaction.followup.send("⚠️ Không thể tạo thêm quy tắc. Vui lòng kiểm tra xem server đã cài sẵn các quy tắc này chưa, hoặc bot có thiếu quyền `Quản lý Server` không nhé.")
                    
        except Exception as e:
            await interaction.followup.send(f"❌ Có lỗi xảy ra khi thiết lập hệ thống: {e}")


    # ================= BỘ LỌC TIN NHẮN TỰ ĐỘNG (BOT-SIDE) =================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Bỏ qua tin nhắn của bot hoặc tin nhắn cá nhân DM
        if message.author.bot or not message.guild:
            return

        guild_id = message.guild.id
        
        # Lấy danh sách từ cấm từ Cache
        bad_words = self.word_cache.get(guild_id)
        
        # Nếu server chưa có dữ liệu trong Cache, tải từ DB lên
        if bad_words is None:
            bad_words = self.load_cache(guild_id)

        # Nếu không có từ cấm nào được thiết lập, bỏ qua
        if not bad_words:
            return

        content_lower = message.content.lower()

        # Kiểm tra trùng khớp từ cấm
        for word in bad_words:
            if word in content_lower:
                try:
                    # Xóa tin nhắn vi phạm
                    await message.delete()
                    
                    # Cảnh báo nhanh ra kênh chat
                    await message.channel.send(
                        f"⚠️ {message.author.mention}, tin nhắn của bạn đã bị xóa vì chứa từ ngữ vi phạm!", 
                        delete_after=5.0
                    )
                    
                    # Ghi nhận vi phạm vào Database và lấy tổng số cảnh báo hiện có
                    warn_count = database.add_warning(
                        guild_id=guild_id,
                        user_id=message.author.id,
                        moderator_id=self.bot.user.id, 
                        reason=f"Auto-Mod: Sử dụng từ cấm ({word})"
                    )
                    
                    # Thực thi hình phạt tự động dựa trên số lần vi phạm
                    await apply_auto_punishment(message, message.author, warn_count)
                    break 
                
                except discord.Forbidden:
                    pass
                except Exception as e:
                    print(f"Lỗi hệ thống Auto-Mod: {e}")

async def setup(bot):
    await bot.add_cog(AutoMod(bot))