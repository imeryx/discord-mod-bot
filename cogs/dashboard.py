import discord
from discord.ext import commands
from aiohttp import web
import asyncio

class Dashboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Khởi tạo máy chủ web
        self.app = web.Application()
        self.runner = None
        
        # Định tuyến các trang web (Routes) - Dễ dàng mở rộng thêm trang sau này
        self.app.add_routes([
            web.get('/', self.home_page),
            web.get('/api/stats', self.api_stats)
        ])

    async def home_page(self, request):
        """Trang chủ của Dashboard (Giao diện HTML)"""
        
        # TỰ ĐỘNG ĐỌC LỆNH: Bất cứ khi nào bạn thêm lệnh mới vào bot, web sẽ tự cập nhật!
        commands_list = [f"<li><b>!{cmd.name}</b>: {cmd.help or 'Không có mô tả'}</li>" for cmd in self.bot.commands]
        commands_html = "".join(commands_list)

        # Bạn có thể tách đoạn HTML này ra một file index.html riêng sau này cho dễ viết CSS/JS
        html_content = f"""
        <!DOCTYPE html>
        <html lang="vi">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Elfaria Bot Dashboard</title>
            <style>
                body {{ font-family: Arial, sans-serif; background: #2c2f33; color: white; padding: 20px; }}
                .container {{ max-width: 800px; margin: auto; background: #23272a; padding: 20px; border-radius: 10px; }}
                h1 {{ color: #5865F2; }}
                ul {{ line-height: 1.8; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎛️ Bảng điều khiển Elfaria Bot</h1>
                <p>Bot đang phục vụ ở <b>{len(self.bot.guilds)}</b> máy chủ với độ trễ (ping) là <b>{round(self.bot.latency * 1000)}ms</b>.</p>
                
                <h2>Danh sách lệnh hiện có (Tự động cập nhật)</h2>
                <ul>
                    {commands_html}
                </ul>
            </div>
        </body>
        </html>
        """
        return web.Response(text=html_content, content_type='text/html')

    async def api_stats(self, request):
        """API trả về dữ liệu JSON (dành cho frontend JavaScript gọi)"""
        return web.json_response({
            "servers": len(self.bot.guilds),
            "ping": round(self.bot.latency * 1000),
            "commands_count": len(self.bot.commands)
        })

    async def start_web_server(self):
        """Hàm chạy ngầm máy chủ web"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        # Chạy ở cổng 8080
        site = web.TCPSite(self.runner, '0.0.0.0', 8080)
        await site.start()
        print("🌐 Web Dashboard đang chạy tại port 8080")

    @commands.Cog.listener()
    async def on_ready(self):
        # Khi bot khởi động xong, kích hoạt máy chủ web chạy song song
        self.bot.loop.create_task(self.start_web_server())

async def setup(bot):
    await bot.add_cog(Dashboard(bot))