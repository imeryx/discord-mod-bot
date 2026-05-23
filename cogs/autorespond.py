import discord
from discord.ext import commands
from discord import app_commands
import database

class AutoRespond(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("-> Cog [AutoRespond] Đã sẵn sàng tương tác!")

    # ================= CÁC LỆNH CẤU HÌNH =================
    @app_commands.command(name="add_response", description="Thêm một câu trả lời tự động cho server")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(
        trigger="Từ khóa hoặc câu kích hoạt (Ví dụ: xin chào)",
        response="Câu trả lời của bot (Ví dụ: Chào bạn, chúc một ngày tốt lành!)"
    )
    async def add_response(self, interaction: discord.Interaction, trigger: str, response: str):
        database.add_autoresponse(interaction.guild.id, trigger, response)
        await interaction.response.send_message(f"✅ Đã thêm AutoResponse!\nKhi ai đó gõ chính xác: `{trigger}`\nBot sẽ đáp lại: **{response}**", ephemeral=True)

    @app_commands.command(name="remove_response", description="Xóa một câu trả lời tự động")
    @app_commands.default_permissions(manage_guild=True)
    async def remove_response(self, interaction: discord.Interaction, trigger: str):
        success = database.remove_autoresponse(interaction.guild.id, trigger)
        if success:
            await interaction.response.send_message(f"🗑️ Đã xóa trả lời tự động cho từ khóa `{trigger}`!", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ Không tìm thấy từ khóa `{trigger}` trong hệ thống.", ephemeral=True)

    @app_commands.command(name="list_responses", description="Xem danh sách các câu trả lời tự động hiện có")
    @app_commands.default_permissions(manage_guild=True)
    async def list_responses(self, interaction: discord.Interaction):
        responses = database.get_autoresponses(interaction.guild.id)
        if not responses:
            return await interaction.response.send_message("Server này hiện chưa cài đặt AutoResponse nào.", ephemeral=True)
        
        msg = "📜 **Danh sách AutoRespond của Server:**\n"
        for trig, resp in responses:
            msg += f"• Nhắn `{trig}` ➡️ Đáp: `{resp}`\n"
        
        await interaction.response.send_message(msg, ephemeral=True)

    # ================= XỬ LÝ LẮNG NGHE TIN NHẮN =================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Bỏ qua tin nhắn do bot gửi hoặc tin nhắn DM
        if message.author.bot or not message.guild:
            return

        # Kéo danh sách câu trả lời của server từ Database
        responses = database.get_autoresponses(message.guild.id)
        if not responses:
            return

        content_lower = message.content.lower().strip()

        # Kiểm tra xem tin nhắn có trùng khớp với từ khóa nào không
        for trigger, response in responses:
            # Dùng toán tử == để yêu cầu người dùng gõ CHÍNH XÁC từ khóa thì bot mới rep
            # (Tránh việc bot spam nhảy vào giữa cuộc trò chuyện bình thường)
            if content_lower == trigger:
                try:
                    await message.channel.send(response)
                except Exception as e:
                    print(f"Lỗi gửi AutoRespond: {e}")
                
                # Bot chỉ rep 1 từ khóa đầu tiên tìm thấy rồi dừng vòng lặp
                break 

async def setup(bot):
    await bot.add_cog(AutoRespond(bot))