import discord
from discord.ext import commands
import aiohttp
import io
import re

class TikTokDownloader(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Bộ lọc Regex để nhận diện mọi loại link TikTok (link ngắn, link dài, web, app)
        self.tiktok_pattern = re.compile(r'https?://(?:www\.)?(?:vm\.tiktok\.com|vt\.tiktok\.com|tiktok\.com/.*)')

    @commands.Cog.listener()
    async def on_ready(self):
        print("-> Cog [TikTok] Đã sẵn sàng bắt link video!")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Bỏ qua tin nhắn của bot để tránh tạo vòng lặp vô tận
        if message.author.bot or not message.guild:
            return

        # Quét xem trong tin nhắn có chứa link TikTok không
        match = self.tiktok_pattern.search(message.content)
        if match:
            tiktok_url = match.group(0)
            
            # Thả cảm xúc ⏳ để báo cho người dùng biết bot đang xử lý
            try:
                await message.add_reaction("⏳")
            except:
                pass

            # Sử dụng API của TikWM để lấy link video gốc (Không chứa Logo)
            api_url = f"https://www.tikwm.com/api/?url={tiktok_url}"
            
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(api_url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            
                            # Code = 0 nghĩa là API xử lý thành công
                            if data.get("code") == 0:
                                video_url = data["data"]["play"]
                                title = data["data"].get("title", "Không có tiêu đề")
                                author = data["data"].get("author", {}).get("nickname", "Unknown")
                                
                                # Tiến hành tải video về bộ nhớ đệm (RAM)
                                async with session.get(video_url) as vid_resp:
                                    if vid_resp.status == 200:
                                        video_bytes = await vid_resp.read()
                                        
                                        # Khóa an toàn: Discord giới hạn file tải lên tối đa 25MB cho bản miễn phí
                                        if len(video_bytes) > 25 * 1024 * 1024:
                                            await message.reply("⚠️ Video này quá lớn (vượt mức 25MB), bot không thể tải lên Discord được.")
                                            await message.remove_reaction("⏳", self.bot.user)
                                            return
                                        
                                        # Đóng gói video thành file của Discord
                                        file = discord.File(io.BytesIO(video_bytes), filename=f"tiktok_{message.author.name}.mp4")
                                        
                                        # (Tùy chọn) Ẩn cái khung link gốc xấu xí của Discord đi
                                        try:
                                            await message.edit(suppress=True)
                                        except:
                                            pass

                                        # Trả lời lại tin nhắn gốc kèm video
                                        await message.reply(content=f"🎥 **{author}**: {title}", file=file)
                                        
                                        # Thay đổi cảm xúc thành ✅
                                        try:
                                            await message.remove_reaction("⏳", self.bot.user)
                                            await message.add_reaction("✅")
                                        except:
                                            pass
                            else:
                                await message.reply("❌ Không thể tải video này (Có thể video đang bị riêng tư hoặc bị xóa).")
                                await message.remove_reaction("⏳", self.bot.user)
                except Exception as e:
                    print(f"Lỗi hệ thống tải TikTok: {e}")
                    try:
                        await message.remove_reaction("⏳", self.bot.user)
                    except:
                        pass

async def setup(bot):
    await bot.add_cog(TikTokDownloader(bot))