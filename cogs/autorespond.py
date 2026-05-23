import discord
from discord.ext import commands
from discord import app_commands
import database

class AutoRespond(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("-> Cog [AutoRespond] Đã sẵn sàng tương tác (Hỗ trợ Ảnh/GIF & Giao diện mới)!")

    # ================= CÁC LỆNH CẤU HÌNH =================
    @app_commands.command(name="add_response", description="Thêm một câu trả lời tự động cho server")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(
        trigger="Từ khóa hoặc câu kích hoạt (Ví dụ: meo meo)",
        response="Câu trả lời của bot (Ví dụ: Gọi tôi có việc gì?)",
        image_url="[Không bắt buộc] Link ảnh hoặc GIF hiển thị kèm (http...)"
    )
    async def add_response(self, interaction: discord.Interaction, trigger: str, response: str, image_url: str = None):
        # Lưu vào database
        database.add_autoresponse(interaction.guild.id, trigger, response, image_url)
        
        msg = f"✅ Đã thêm AutoResponse!\n• Khi ai đó gõ: `{trigger}`\n• Bot sẽ đáp: **{response}**"
        if image_url:
            msg += f"\n• Kèm theo ảnh/GIF: [Nhấn vào để xem]({image_url})"
            
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
        
        # Thiết kế khung Embed chuyên nghiệp
        embed = discord.Embed(
            title="🤖 Danh Sách Trả Lời Tự Động",
            description="Dưới đây là các từ khóa và phản hồi mà bot đã ghi nhớ:\n" + "━"*30,
            color=discord.Color.blurple()
        )
        
        for idx, (trig, resp, img) in enumerate(responses, 1):
            # Cắt bớt câu trả lời nếu nó quá dài để tránh làm vỡ khung hiển thị
            display_resp = resp if len(resp) <= 60 else resp[:57] + "..."
            
            # Gắn thêm icon nếu có ảnh
            img_status = " 📸 *(Có đính kèm ảnh)*" if img else ""
            
            # Thêm từng mục vào Embed dưới dạng Field
            embed.add_field(
                name=f"{idx}. Từ khóa: `{trig}`",
                value=f"↳ **Đáp lại:** {display_resp}{img_status}",
                inline=False # Buộc mỗi từ khóa phải nằm trên một hàng riêng biệt
            )
            
            # Khóa an toàn: Discord giới hạn tối đa 25 fields cho 1 Embed
            if idx == 25:
                embed.set_footer(text=f"Và còn nhiều từ khóa khác... (Đang hiển thị 25 mục đầu tiên)")
                break
                
        # Nếu ít hơn 25 mục thì đếm tổng số lượng
        if len(responses) <= 25:
            embed.set_footer(text=f"Tổng cộng: {len(responses)} câu trả lời tự động.")

        await interaction.response.send_message(embed=embed, ephemeral=True)

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

        # Chuyển tin nhắn của người dùng về chữ thường và xóa khoảng trắng thừa 2 đầu
        content_lower = message.content.lower().strip()

        # Kiểm tra xem tin nhắn có trùng khớp với từ khóa nào không
        for trigger, response, image_url in responses:
            if content_lower == trigger:
                try:
                    # Nếu có link ảnh, tạo khung Embed đẹp mắt
                    if image_url:
                        embed = discord.Embed(color=discord.Color.random())
                        embed.set_image(url=image_url)
                        await message.channel.send(content=response, embed=embed)
                    # Nếu không có ảnh, chỉ gửi chữ bình thường
                    else:
                        await message.channel.send(content=response)
                except Exception as e:
                    print(f"Lỗi gửi AutoRespond: {e}")
                
                # Bot chỉ rep 1 từ khóa đầu tiên tìm thấy rồi dừng vòng lặp
                break 

async def setup(bot):
    await bot.add_cog(AutoRespond(bot))