import discord
from discord.ext import commands
from discord import app_commands
import database
import os

class AutoRespond(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("-> Cog [AutoRespond] Đã sẵn sàng tương tác (Hỗ trợ Link Ảnh Tùy Chọn, Không Embed)!")

    # ================= CÁC LỆNH CẤU HÌNH =================
    @app_commands.command(name="add_response", description="Thêm một câu trả lời tự động cho server")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(
        trigger="Từ khóa hoặc câu kích hoạt (Ví dụ: meo meo)",
        response="[Tùy chọn] Câu trả lời bằng chữ của bot",
        image_url="[Tùy chọn] Link ảnh hoặc GIF hiển thị kèm (http...)"
    )
    async def add_response(self, interaction: discord.Interaction, trigger: str, response: str = None, image_url: str = None):
        if not response and not image_url:
            return await interaction.response.send_message("❌ Bạn phải nhập câu trả lời chữ (`response`) hoặc điền link ảnh (`image_url`)!", ephemeral=True)
        
        database.add_autoresponse(interaction.guild.id, trigger, response, image_url)
        
        msg = f"✅ Đã thêm AutoResponse!\n• Khi ai đó gõ: `{trigger}`"
        if response:
            msg += f"\n• Bot sẽ đáp: **{response}**"
        if image_url:
            msg += f"\n• Kèm theo link ảnh: [Nhấn vào để xem]({image_url})"
            
        await interaction.response.send_message(msg, ephemeral=True)

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
            return await interaction.response.send_message("⚠️ Server này hiện chưa cài đặt AutoResponse nào.", ephemeral=True)
        
        embed = discord.Embed(
            title="🤖 Danh Sách Trả Lời Tự Động",
            description="Dưới đây là các từ khóa và phản hồi mà bot đã ghi nhớ:\n" + "━"*30,
            color=discord.Color.blurple()
        )
        
        for idx, (trig, resp, img) in enumerate(responses, 1):
            if resp:
                display_resp = resp if len(resp) <= 60 else resp[:57] + "..."
            else:
                display_resp = "*(Will send image)*"
            
            # Gắn thêm icon nếu có ảnh
            img_status = " 📸 *(Có kèm ảnh)*" if img else ""
            
            embed.add_field(
                name=f"{idx}. Từ khóa: `{trig}`",
                value=f"↳ **Đáp lại:** {display_resp}{img_status}",
                inline=False 
            )
            
            if idx == 25:
                embed.set_footer(text=f"Và còn nhiều từ khóa khác... (Đang hiển thị 25 mục đầu tiên)")
                break
                
        if len(responses) <= 25:
            embed.set_footer(text=f"Tổng cộng: {len(responses)} câu trả lời tự động.")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ================= XỬ LÝ LẮNG NGHE TIN NHẮN =================
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
                    # Logic gửi mới: Không sử dụng Embed
                    file_attachment = None
                    message_content = response # Bắt đầu với văn bản phản hồi (có thể là None)
                    
                    # 1. Cơ chế tương thích ngược (Nếu trước đó có file lưu cục bộ)
                    if image_url and not image_url.startswith("http") and os.path.exists(image_url):
                        # Gửi hình ảnh cục bộ dưới dạng discord.File trực tiếp
                        file_attachment = discord.File(image_url)
                        # Nếu phản hồi chữ trống, Discord vẫn cho phép gửi chỉ File. 
                        # Nếu có File, Discord sẽ hiển thị phản hồi chữ phía trên.
                        
                    # 2. Xử lý link ảnh URL mới (Không Embed)
                    elif image_url and image_url.startswith("http"):
                        # Cộng link ảnh vào nội dung tin nhắn để Discord tự hiển thị ảnh
                        if message_content:
                            message_content += "\n" + image_url
                        else:
                            message_content = image_url

                    # Tiến hành gửi
                    await message.channel.send(content=message_content, file=file_attachment)
                            
                except Exception as e:
                    print(f"Lỗi gửi AutoRespond: {e}")
                
                break 

async def setup(bot):
    await bot.add_cog(AutoRespond(bot))