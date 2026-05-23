import discord
from discord.ext import commands
from aiohttp import web
import json
import os

CONFIG_PATH = "config.json"

class Dashboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application()
        self.app.add_routes([
            web.get('/', self.home_page),
            web.post('/api/toggle-module', self.toggle_module)
        ])

    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {"bot_prefix": "!", "modules": {}}

    def save_config(self, data):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    async def home_page(self, request):
        config = self.load_config()
        modules = config.get("modules", {"ai_chat": True, "image_tools": True})

        module_details = {
            "ai_chat": {
                "name": "Trợ lý AI (Gemini)", 
                "desc": "Cho phép bot trả lời tin nhắn tự động bằng AI khi được tag."
            },
            "image_tools": {
                "name": "Công cụ Tách Nền", 
                "desc": "Kích hoạt lệnh !tachnen sử dụng API của remove.bg."
            }
        }

        modules_html = ""
        for key, info in module_details.items():
            is_checked = "checked" if modules.get(key, True) else ""
            modules_html += f"""
            <div class="card">
                <div class="card-header">
                    <h3>{info['name']}</h3>
                    <label class="switch">
                        <input type="checkbox" onchange="toggleModule('{key}', this.checked)" {is_checked}>
                        <span class="slider round"></span>
                    </label>
                </div>
                <p class="desc">{info['desc']}</p>
            </div>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html lang="vi">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Elfaria Dashboard</title>
            <style>
                :root {{ --bg-main: #1e1e24; --bg-sidebar: #17171a; --bg-card: #2b2d31; --accent: #5865F2; --text: #dcddde; }}
                body {{ margin: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: var(--bg-main); color: var(--text); display: flex; height: 100vh; }}
                .sidebar {{ width: 250px; background: var(--bg-sidebar); padding: 20px 0; border-right: 1px solid #222; }}
                .sidebar h2 {{ text-align: center; color: white; border-bottom: 1px solid #333; padding-bottom: 20px; margin-top: 0; }}
                .menu-item {{ padding: 15px 25px; cursor: pointer; transition: 0.2s; font-weight: 500; }}
                .menu-item:hover, .menu-item.active {{ background: #2a2d33; border-left: 4px solid var(--accent); color: white; }}
                .main-content {{ flex: 1; padding: 40px; overflow-y: auto; }}
                h1 {{ margin-top: 0; color: white; }}
                .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; margin-top: 30px; }}
                .card {{ background: var(--bg-card); padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
                .card h3 {{ margin: 0; color: white; }}
                .desc {{ color: #a3a6aa; font-size: 14px; margin-bottom: 0; }}
                .switch {{ position: relative; display: inline-block; width: 44px; height: 24px; }}
                .switch input {{ opacity: 0; width: 0; height: 0; }}
                .slider {{ position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #72767d; transition: .4s; border-radius: 34px; }}
                .slider:before {{ position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; transition: .4s; border-radius: 50%; }}
                input:checked + .slider {{ background-color: #43b581; }}
                input:checked + .slider:before {{ transform: translateX(20px); }}
            </style>
        </head>
        <body>
            <div class="sidebar">
                <h2>🤖 Elfaria Bot</h2>
                <div class="menu-item active">🧩 Quản lý Tính năng</div>
            </div>
            <div class="main-content">
                <h1>Tính năng (Modules)</h1>
                <p>Bật hoặc tắt các công cụ cốt lõi của bot theo thời gian thực.</p>
                <div class="grid">
                    {modules_html}
                </div>
            </div>
            <script>
                async function toggleModule(moduleName, isEnabled) {{
                    try {{
                        await fetch('/api/toggle-module', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ module: moduleName, state: isEnabled }})
                        }});
                    }} catch (e) {{
                        alert("Lỗi kết nối đến VPS!");
                    }}
                }}
            </script>
        </body>
        </html>
        """
        return web.Response(text=html_content, content_type='text/html')

    async def toggle_module(self, request):
        data = await request.json()
        module_name = data.get("module")
        state = data.get("state")

        config = self.load_config()
        if "modules" not in config:
            config["modules"] = {}
            
        config["modules"][module_name] = state
        self.save_config(config)
        return web.json_response({"status": "success"})

    async def start_web_server(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, '0.0.0.0', 8080)
        await site.start()

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.loop.create_task(self.start_web_server())

async def setup(bot):
    await bot.add_cog(Dashboard(bot))