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
        print("-> Cog [AutoRespond] Đã sẵn sàng tương tác (Giao diện Mimu-style hoàn hảo)!")

    # ================= CÁC LỆNH CẤU HÌNH =================
    @app_commands.command(name="add_response", description="Thêm một câu trả lời tự động cho server")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(
        trigger="Từ khóa hoặc câu kích hoạt (Ví dụ: meo meo)",
        response="[Tùy chọn] Câu trả lời bằng chữ của bot",
        image_url="[Tùy chọn] Link ảnh hoặc GIF hiển thị kèm (http...)"
    )
    async def add_response(self, interaction: discord.Interaction, trigger: str, response: str = None, image_url: str = None):
        # Kiểm tra logic: Không thể để trống cả trường chữ lẫn trường ảnh
        if not response and not image_url:
            return await interaction.response.send_message("❌ Bạn phải nhập câu trả lời chữ (`response`) hoặc điền link ảnh (`image_url`)!", ephemeral=True)
        
        # Lưu vào database
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
            # Xử lý chuỗi hiển thị nếu phản hồi chữ trống (chỉ có ảnh)
            if resp:
                display_resp = resp if len(resp) <= 60 else resp[:57] + "..."
            else:
                display_resp = "*(Chỉ gửi ảnh)*"
            
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
                    kwargs = {}
                    message_content = response if response else ""
                    
                    if image_url:
                        # 1. Nếu là Link mạng -> Áp dụng mẹo Ký tự tàng hình giống Mimu bot
                        if image_url.startswith("http"):
                            # Ký tự \u200B giúp ẩn hoàn toàn text của đường dẫn link URL
                            invisible_link = f"[\u200B]({image_url})"
                            if message_content:
                                kwargs['content'] = f"{message_content}\n{invisible_link}"
                            else:
                                kwargs['content'] = invisible_link
                        
                        # 2. Tương thích ngược: Nếu hệ thống cũ lưu file ảnh cục bộ trên ổ cứng VPS
                        elif os.path.exists(image_url):
                            filename = os.path.basename(image_url)
                            kwargs['file'] = discord.File(image_url, filename=filename)
                            # File cục bộ buộc phải dùng Embed tiệp màu để ẩn chữ tên file đính kèm
                            embed = discord.Embed(color=0x2B2D31)
                            embed.set_image(url=f"attachment://{filename}")
                            kwargs['embed'] = embed
                            if message_content:
                                kwargs['content'] = message_content
                                
                    elif message_content:
                        kwargs['content'] = message_content

                    # Tiến hành gửi gói tin dữ liệu linh hoạt
                    if kwargs:
                        await message.channel.send(**kwargs)
                            
                except Exception as e:
                    print(f"Lỗi gửi AutoRespond: {e}")
                
                break 
                
async def setup(bot):
    await bot.add_cog(AutoRespond(bot))