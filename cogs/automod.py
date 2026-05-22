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