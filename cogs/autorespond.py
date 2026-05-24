import discord
from discord.ext import commands
from discord import app_commands
import database
import os
import aiohttp
import io

class AutoRespond(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("-> Cog [AutoRespond] Đã sẵn sàng (Upload ảnh trực tiếp từ RAM, không viền!)")

    # ================= CÁC LỆNH CẤU HÌNH =================
    @app_commands.command(name="add_response", description="Thêm một câu trả lời tự động cho server")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(
        trigger="Từ khóa hoặc câu kích hoạt (Ví dụ: meo meo)",
        response="[Tùy chọn] Câu trả lời bằng chữ của bot",
        image_url="[Tùy chọn] Link ảnh trực tiếp hoặc GIF (http...)"
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
                    if response:
                        kwargs['content'] = response
                    
                    if image_url:
                        if image_url.startswith("http"):
                            # Tuyệt chiêu: Tải ảnh từ URL vào RAM và gửi như 1 file đính kèm thật
                            async with aiohttp.ClientSession() as session:
                                async with session.get(image_url) as resp:
                                    if resp.status == 200:
                                        # Kiem tra xem link co phai la file anh thuc su khong
                                        content_type = resp.headers.get('Content-Type', '')
                                        if 'image' in content_type or 'video' in content_type:
                                            img_bytes = await resp.read()
                                            ext = content_type.split('/')[-1] # lay duoi png, gif, jpeg
                                            # Gắn vào payload như 1 file bình thường
                                            kwargs['file'] = discord.File(io.BytesIO(img_bytes), filename=f"image.{ext}")
                                        else:
                                            # Neu link khong phai anh (vd: link tenor.com/xxx), tra ve text de Discord tu render
                                            kwargs['content'] = f"{kwargs.get('content', '')}\n{image_url}".strip()
                        
                        elif os.path.exists(image_url):
                            # Tương thích với các file cũ đang nằm ở thư mục saved_images trên VPS
                            filename = os.path.basename(image_url)
                            kwargs['file'] = discord.File(image_url, filename=filename)

                    # Gửi tin nhắn ra chat
                    if kwargs:
                        await message.channel.send(**kwargs)
                            
                except Exception as e:
                    print(f"Lỗi gửi AutoRespond: {e}")
                
                break 

async def setup(bot):
    await bot.add_cog(AutoRespond(bot))