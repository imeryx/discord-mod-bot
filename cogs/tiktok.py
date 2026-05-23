import discord
from discord.ext import commands
import aiohttp
import io
import re

class TikTokDownloader(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Regex thông minh nhận diện mọi loại cấu trúc đường dẫn TikTok
        self.tiktok_pattern = re.compile(r'https?://(?:www\.)?(?:vm\.tiktok\.com|vt\.tiktok\.com|tiktok\.com/[^?\s]+)')

    @commands.Cog.listener()
    async def on_ready(self):
        print("-> Cog [TikTok] Động cơ Hybrid Cobalt & VxTikTok đã kích hoạt hoàn hảo!")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Bỏ qua tin nhắn của các tài khoản bot hoặc tin nhắn DM cá nhân
        if message.author.bot or not message.guild:
            return

        match = self.tiktok_pattern.search(message.content)
        if match:
            tiktok_url = match.group(0)
            
            try: await message.add_reaction("⏳")
            except: pass

            # Sử dụng API của hệ thống Cobalt Server công cộng để bóc tách media
            cobalt_api = "https://api.cobalt.tools/"
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            payload = {
                "url": tiktok_url,
                "vQuality": "720", # Chất lượng tối ưu nhất cho thiết bị di động và Discord
                "filenamePattern": "basic"
            }

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(cobalt_api, json=payload, headers=headers) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            status = data.get("status")

                            # ================= TRƯỜNG HỢP 1: BÀI ĐĂNG DẠNG ẢNH (SLIDESHOW) =================
                            if status == "picker":
                                picker_items = data.get("picker", [])
                                files = []
                                
                                # Lọc lấy các đường dẫn định dạng ảnh
                                img_urls = [item["url"] for item in picker_items if item.get("type") == "photo"]
                                
                                # Tiến hành tải hàng loạt (Tối đa 10 ảnh do giới hạn nghiêm ngặt của Discord)
                                for idx, img_url in enumerate(img_urls[:10]):
                                    async with session.get(img_url) as img_resp:
                                        if img_resp.status == 200:
                                            img_bytes = await img_resp.read()
                                            files.append(discord.File(io.BytesIO(img_bytes), filename=f"tiktok_img_{idx}.jpg"))

                                if files:
                                    try: await message.edit(suppress=True) # Ẩn cái Embed link gốc của người dùng
                                    except: pass
                                    
                                    extra_txt = f"\n*(Chỉ hiển thị 10/{len(img_urls)} ảnh do giới hạn nhóm file)*" if len(img_urls) > 10 else ""
                                    await message.reply(content=f"📸 **Album ảnh TikTok từ** {message.author.mention}:{extra_txt}", files=files)

                            # ================= TRƯỜNG HỢP 2: BÀI ĐĂNG DẠNG VIDEO =================
                            elif status == "stream":
                                video_url = data.get("url")
                                if video_url:
                                    # Đọc nhanh Header của file để check dung lượng thực tế (Content-Length)
                                    async with session.head(video_url) as head_resp:
                                        file_size = int(head_resp.headers.get('Content-Length', 0))
                                    
                                    limit_bytes = message.guild.filesize_limit

                                    # Nếu video nhẹ (< 25MB): Tải về RAM và đẩy trực tiếp thành file đính kèm
                                    if 0 < file_size <= limit_bytes:
                                        async with session.get(video_url) as vid_resp:
                                            if vid_resp.status == 200:
                                                video_bytes = await vid_resp.read()
                                                file = discord.File(io.BytesIO(video_bytes), filename=f"tiktok_{message.author.name}.mp4")
                                                
                                                try: await message.edit(suppress=True)
                                                except: pass
                                                await message.reply(file=file)
                                    else:
                                        # Nếu video quá nặng (> 25MB): Chuyển đổi link sang vxtiktok để ép Discord tự render Trình phát trực tiếp
                                        vx_url = tiktok_url.replace("tiktok.com", "vxtiktok.com")
                                        try: await message.edit(suppress=True)
                                        except: pass
                                        await message.reply(content=vx_url)
                            else:
                                # Dự phòng khẩn cấp nếu Cobalt trả về cấu trúc lạ
                                vx_url = tiktok_url.replace("tiktok.com", "vxtiktok.com")
                                try: await message.edit(suppress=True)
                                except: pass
                                await message.reply(content=vx_url)

                            # Đổi trạng thái từ chờ đợi sang hoàn thành thành công
                            try:
                                await message.remove_reaction("⏳", self.bot.user)
                                await message.add_reaction("✅")
                            except: pass
                        else:
                            # Nếu API Cobalt bị nghẽn (Status code != 200), lập tức dùng VTikTok làm cứu cánh
                            vx_url = tiktok_url.replace("tiktok.com", "vxtiktok.com")
                            try: await message.edit(suppress=True)
                            except: pass
                            await message.reply(content=vx_url)
                            try: await message.remove_reaction("⏳", self.bot.user)
                            except: pass

                except Exception as e:
                    print(f"Lỗi hệ thống đồng bộ TikTok: {e}")
                    # Lớp phòng vệ cuối cùng khi toàn bộ hệ thống gặp sự cố mạng
                    vx_url = tiktok_url.replace("tiktok.com", "vxtiktok.com")
                    try:
                        await message.edit(suppress=True)
                        await message.reply(content=vx_url)
                        await message.remove_reaction("⏳", self.bot.user)
                    except: pass

async def setup(bot):
    await bot.add_cog(TikTokDownloader(bot))