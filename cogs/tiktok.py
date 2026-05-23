import discord
from discord.ext import commands
import aiohttp
import io
import re

class TikTokDownloader(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tiktok_pattern = re.compile(r'https?://(?:www\.)?(?:vm\.tiktok\.com|vt\.tiktok\.com|tiktok\.com)/[^?\s]+')

    @commands.Cog.listener()
    async def on_ready(self):
        print("-> Cog [TikTok] Đã sẵn sàng (Bản dùng API TikWM không bị chặn IP)!")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        match = self.tiktok_pattern.search(message.content)
        if match:
            tiktok_url = match.group(0)
            
            try: await message.add_reaction("⏳")
            except: pass

            # Sử dụng API TikWM chuyên dụng cho TikTok thay vì Cobalt
            tikwm_api = f"https://www.tikwm.com/api/?url={tiktok_url}"
            headers_dl = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(tikwm_api) as resp:
                        if resp.status == 200:
                            res_json = await resp.json()
                            
                            # API TikWM trả về code 0 là thành công
                            if res_json.get("code") == 0:
                                data = res_json.get("data", {})
                                
                                # ================= TRƯỜNG HỢP 1: BÀI ĐĂNG DẠNG ẢNH =================
                                if "images" in data and isinstance(data["images"], list):
                                    img_urls = data["images"]
                                    files = []
                                    
                                    # Tải tối đa 10 ảnh theo giới hạn của Discord
                                    for idx, img_url in enumerate(img_urls[:10]):
                                        async with session.get(img_url, headers=headers_dl) as img_resp:
                                            if img_resp.status == 200:
                                                img_bytes = await img_resp.read()
                                                files.append(discord.File(io.BytesIO(img_bytes), filename=f"tiktok_img_{idx}.jpg"))

                                    if files:
                                        try: await message.edit(suppress=True)
                                        except: pass
                                        extra_txt = f"\n*(Tải trực tiếp {len(files)}/{len(img_urls)} ảnh từ bài đăng)*"
                                        await message.reply(content=f"📸 **Album TikTok từ** {message.author.mention}:{extra_txt}", files=files)
                                        
                                # ================= TRƯỜNG HỢP 2: BÀI ĐĂNG DẠNG VIDEO =================
                                elif "play" in data:
                                    video_url = data["play"]
                                    
                                    # Kiểm tra dung lượng video trước khi tải
                                    async with session.head(video_url) as head_resp:
                                        file_size = int(head_resp.headers.get('Content-Length', 0))
                                    
                                    limit_bytes = message.guild.filesize_limit

                                    # Nếu video nhẹ hơn mức Discord cho phép
                                    if 0 < file_size <= limit_bytes:
                                        async with session.get(video_url, headers=headers_dl) as vid_resp:
                                            if vid_resp.status == 200:
                                                video_bytes = await vid_resp.read()
                                                file = discord.File(io.BytesIO(video_bytes), filename=f"tiktok_{message.author.name}.mp4")
                                                try: await message.edit(suppress=True)
                                                except: pass
                                                await message.reply(file=file)
                                    else:
                                        # Video quá nặng, dùng Kế hoạch B
                                        vx_url = tiktok_url.replace("tiktok.com", "tnktok.com")
                                        try: await message.edit(suppress=True)
                                        except: pass
                                        await message.reply(content=vx_url)
                            else:
                                # Nếu API lỗi không lấy được dữ liệu
                                vx_url = tiktok_url.replace("tiktok.com", "tnktok.com")
                                try: await message.edit(suppress=True)
                                except: pass
                                await message.reply(content=vx_url)
                        else:
                            vx_url = tiktok_url.replace("tiktok.com", "tnktok.com")
                            try: await message.edit(suppress=True)
                            except: pass
                            await message.reply(content=vx_url)

                    try:
                        await message.remove_reaction("⏳", self.bot.user)
                        await message.add_reaction("✅")
                    except: pass

                except Exception as e:
                    print(f"Lỗi API TikWM: {e}")
                    vx_url = tiktok_url.replace("tiktok.com", "tnktok.com")
                    try:
                        await message.edit(suppress=True)
                        await message.reply(content=vx_url)
                        await message.remove_reaction("⏳", self.bot.user)
                    except: pass

async def setup(bot):
    await bot.add_cog(TikTokDownloader(bot))