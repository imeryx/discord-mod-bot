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
        print("-> Cog [TikTok] Đã sẵn sàng (Bản vượt Tường lửa Ảnh)!")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        match = self.tiktok_pattern.search(message.content)
        if match:
            tiktok_url = match.group(0)
            
            try: await message.add_reaction("⏳")
            except: pass

            cobalt_api = "https://api.cobalt.tools/"
            headers_api = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            payload = {
                "url": tiktok_url,
                "vQuality": "720",
                "filenamePattern": "basic"
            }
            
            # Vũ khí mới: Giả danh trình duyệt thật để không bị TikTok chặn tải
            headers_dl = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(cobalt_api, json=payload, headers=headers_api) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            status = data.get("status")

                            # ================= XỬ LÝ DẠNG ẢNH =================
                            if status == "picker":
                                picker_items = data.get("picker", [])
                                files = []
                                
                                img_urls = [item["url"] for item in picker_items if "url" in item]
                                
                                for idx, img_url in enumerate(img_urls[:10]):
                                    async with session.get(img_url, headers=headers_dl) as img_resp:
                                        if img_resp.status == 200:
                                            img_bytes = await img_resp.read()
                                            files.append(discord.File(io.BytesIO(img_bytes), filename=f"tiktok_img_{idx}.jpg"))
                                        else:
                                            print(f"Lỗi tải ảnh {idx}: Bị chặn với mã {img_resp.status}")

                                if files:
                                    try: await message.edit(suppress=True)
                                    except: pass
                                    
                                    # Báo cáo kết quả trực tiếp ra chat
                                    extra_txt = f"\n*(Hệ thống tìm thấy {len(img_urls)} ảnh, tải thành công {len(files)} ảnh)*"
                                    await message.reply(content=f"📸 **Album ảnh TikTok từ** {message.author.mention}:{extra_txt}", files=files)

                            # ================= XỬ LÝ DẠNG VIDEO =================
                            elif status == "stream":
                                video_url = data.get("url")
                                if video_url:
                                    async with session.head(video_url) as head_resp:
                                        file_size = int(head_resp.headers.get('Content-Length', 0))
                                    
                                    limit_bytes = message.guild.filesize_limit

                                    if 0 < file_size <= limit_bytes:
                                        async with session.get(video_url, headers=headers_dl) as vid_resp:
                                            if vid_resp.status == 200:
                                                video_bytes = await vid_resp.read()
                                                file = discord.File(io.BytesIO(video_bytes), filename=f"tiktok_{message.author.name}.mp4")
                                                
                                                try: await message.edit(suppress=True)
                                                except: pass
                                                await message.reply(file=file)
                                    else:
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
                        else:
                            vx_url = tiktok_url.replace("tiktok.com", "tnktok.com")
                            try: await message.edit(suppress=True)
                            except: pass
                            await message.reply(content=vx_url)
                            try: await message.remove_reaction("⏳", self.bot.user)
                            except: pass

                except Exception as e:
                    print(f"Lỗi hệ thống đồng bộ TikTok: {e}")
                    vx_url = tiktok_url.replace("tiktok.com", "tnktok.com")
                    try:
                        await message.edit(suppress=True)
                        await message.reply(content=vx_url)
                        await message.remove_reaction("⏳", self.bot.user)
                    except: pass

async def setup(bot):
    await bot.add_cog(TikTokDownloader(bot))