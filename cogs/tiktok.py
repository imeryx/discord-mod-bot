import discord
from discord.ext import commands
import aiohttp
import io
import re

class TikTokDownloader(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tiktok_pattern = re.compile(r'https?://(?:www\.)?(?:vm\.tiktok\.com|vt\.tiktok\.com|tiktok\.com/.*)')

    @commands.Cog.listener()
    async def on_ready(self):
        print("-> Cog [TikTok] Đã sẵn sàng (Bản gửi thẳng Video MP4)!")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Bỏ qua tin nhắn của bot
        if message.author.bot or not message.guild:
            return

        match = self.tiktok_pattern.search(message.content)
        if match:
            tiktok_url = match.group(0)
            
            try: await message.add_reaction("⏳")
            except: pass

            api_url = f"https://www.tikwm.com/api/?url={tiktok_url}"
            
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(api_url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            
                            if data.get("code") == 0:
                                item_data = data["data"]
                                title = item_data.get("title", "Không có tiêu đề")
                                author = item_data.get("author", {}).get("nickname", "Unknown")
                                
                                # ================= XỬ LÝ ẢNH (SLIDESHOW) =================
                                if "images" in item_data and isinstance(item_data["images"], list):
                                    image_urls = item_data["images"]
                                    files = []
                                    
                                    for idx, img_url in enumerate(image_urls[:10]):
                                        async with session.get(img_url) as img_resp:
                                            if img_resp.status == 200:
                                                img_bytes = await img_resp.read()
                                                files.append(discord.File(io.BytesIO(img_bytes), filename=f"tiktok_img_{idx}.jpg"))
                                                
                                    if files:
                                        msg_content = f"📸 **{author}**: {title}"
                                        if len(image_urls) > 10:
                                            msg_content += f"\n*(Chỉ hiển thị 10/{len(image_urls)} ảnh)*"
                                            
                                        try: await message.edit(suppress=True)
                                        except: pass
                                        await message.reply(content=msg_content, files=files)
                                
                                # ================= XỬ LÝ GỬI THẲNG VIDEO =================
                                else:
                                    video_url = item_data.get("play")

                                    if video_url:
                                        # Tiến hành tải thẳng video về RAM của VPS mà không cần hỏi han dung lượng
                                        async with session.get(video_url) as vid_resp:
                                            if vid_resp.status == 200:
                                                video_bytes = await vid_resp.read()
                                                
                                                # Đóng gói video thành file chuẩn của Discord (.mp4)
                                                file = discord.File(io.BytesIO(video_bytes), filename=f"tiktok_{message.author.name}.mp4")
                                                
                                                try:
                                                    # Ẩn cái link xấu xí người dùng vừa gửi đi
                                                    try: await message.edit(suppress=True)
                                                    except: pass
                                                    
                                                    # Ép Discord nhận file Video trực tiếp vào chat
                                                    await message.reply(content=f"🎥 **{author}**: {title}", file=file)
                                                    
                                                except discord.errors.HTTPException as e:
                                                    # Nếu video thực sự quá béo (Vượt ngưỡng 25MB) và Discord từ chối
                                                    if e.code == 40005:
                                                        await message.reply(f"⚠️ Video của **{author}** quá nặng (vượt ngưỡng 25MB) nên máy chủ Discord không cho phép bot tải lên.")
                                                    else:
                                                        print(f"Lỗi gửi video: {e}")

                                # Đổi trạng thái sang dấu tick xanh
                                try:
                                    await message.remove_reaction("⏳", self.bot.user)
                                    await message.add_reaction("✅")
                                except: pass
                            else:
                                await message.reply("❌ Không thể tải video này.")
                                try: await message.remove_reaction("⏳", self.bot.user)
                                except: pass
                except Exception as e:
                    print(f"Lỗi hệ thống TikTok: {e}")
                    try: await message.remove_reaction("⏳", self.bot.user)
                    except: pass

async def setup(bot):
    await bot.add_cog(TikTokDownloader(bot))