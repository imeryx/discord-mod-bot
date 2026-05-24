import discord
from discord.ext import commands
from discord import app_commands
import database
import os
import uuid

# Tạo thư mục cục bộ để lưu ảnh vĩnh viễn trên VPS nếu chưa có
if not os.path.exists("./saved_images"):
    os.makedirs("./saved_images")

class AutoRespond(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("-> Cog [AutoRespond] Đã sẵn sàng tương tác (Hỗ trợ Tải file & Giao diện mới)!")

    # ================= CÁC LỆNH CẤU HÌNH =================
    @app_commands.command(name="add_response", description="Thêm một câu trả lời tự động cho server")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(
        trigger="Từ khóa hoặc câu kích hoạt (Ví dụ: meo meo)",
        response="[Tùy chọn] Câu trả lời bằng chữ của bot",
        image="[Tùy chọn] Tải lên trực tiếp một file ảnh hoặc GIF"
    )
    # Đặt response và image thành None mặc định để biến chúng thành Tùy chọn (Optional)
    async def add_response(self, interaction: discord.Interaction, trigger: str, response: str = None, image: discord.Attachment = None):
        # Kiểm tra logic: Không thể để trống cả 2
        if not response and not image:
            return await interaction.response.send_message("❌ Bạn phải nhập câu trả lời chữ (`response`) hoặc tải lên một file (`image`)!", ephemeral=True)
        
        image_path = None
        if image:
            # Kiểm tra định dạng file an toàn
            if not image.content_type or not image.content_type.startswith('image/'):
                return await interaction.response.send_message("❌ File tải lên phải là định dạng ảnh hoặc GIF!", ephemeral=True)
            
            # Tạo tên file ngẫu nhiên để tránh trùng lặp khi nhiều server cùng tải ảnh
            ext = image.filename.split('.')[-1]
            filename = f"{uuid.uuid4().hex}.{ext}"
            image_path = f"./saved_images/{filename}"
            
            # Lưu file trực tiếp xuống ổ cứng VPS
            await image.save(image_path)

        # Lưu vào database (Lưu đường dẫn ổ cứng thay vì URL mạng)
        database.add_autoresponse(interaction.guild.id, trigger, response, image_path)
        
        msg = f"✅ Đã thêm AutoResponse!\n• Khi ai đó gõ: `{trigger}`"
        if response:
            msg += f"\n• Bot sẽ đáp: **{response}**"
        if image:
            msg += f"\n• Kèm theo ảnh tải lên: `{image.filename}`"
            
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(name="remove_response", description="Xóa một câu trả lời tự động")
    @app_commands.default_permissions(manage_guild=True)
    async def remove_response(self, interaction: discord.Interaction, trigger: str):
        # Tìm xem từ khóa này có chứa file ảnh cục bộ không
        responses = database.get_autoresponses(interaction.guild.id)
        target_image_path = None
        for t, r, img in responses:
            if t == trigger.lower():
                target_image_path = img
                break

        success = database.remove_autoresponse(interaction.guild.id, trigger)
        if success:
            # Thu dọn rác: Xóa file ảnh trên VPS để giải phóng dung lượng
            if target_image_path and os.path.exists(target_image_path):
                try:
                    os.remove(target_image_path)
                except Exception as e:
                    print(f"Lỗi khi xóa ảnh cục bộ: {e}")
                    
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
            # Xử lý hiển thị nếu response là None (chỉ gửi ảnh)
            if resp:
                display_resp = resp if len(resp) <= 60 else resp[:57] + "..."
            else:
                display_resp = "*(Chỉ gửi ảnh)*"
            
            img_status = " 📸 *(Có file đính kèm)*" if img else ""
            
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

        for trigger, response, image_path in responses:
            if content_lower == trigger:
                try:
                    file_attachment = None
                    embed = None
                    
                    # 1. Nếu có lưu ảnh cục bộ trên VPS
                    if image_path and os.path.exists(image_path):
                        filename = os.path.basename(image_path)
                        # Mở file từ VPS và nhúng vào Embed
                        file_attachment = discord.File(image_path, filename=filename)
                        embed = discord.Embed(color=discord.Color.random())
                        embed.set_image(url=f"attachment://{filename}")
                        
                    # 2. Cơ chế tương thích ngược (nếu database cũ vẫn còn lưu link URL http)
                    elif image_path and image_path.startswith("http"):
                        embed = discord.Embed(color=discord.Color.random())
                        embed.set_image(url=image_path)

                    # Tiến hành gửi
                    if embed:
                        await message.channel.send(content=response if response else None, file=file_attachment, embed=embed)
                    else:
                        if response:
                            await message.channel.send(content=response)
                            
                except Exception as e:
                    print(f"Lỗi gửi AutoRespond: {e}")
                
                break 

async def setup(bot):
    await bot.add_cog(AutoRespond(bot))