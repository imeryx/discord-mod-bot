import discord
from discord.ext import commands
from aiohttp import web
import aiohttp
import json
import os
import uuid
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = "config.json"
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI")

class Dashboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application()
        self.sessions = {}
        self.app.add_routes([
            web.get('/', self.home_page),
            web.get('/login', self.login),
            web.get('/callback', self.callback),
            web.get('/server/{guild_id}', self.server_panel),
            web.post('/api/toggle-module', self.toggle_module)
        ])

    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: pass
        return {}

    def save_config(self, data):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    async def login(self, request):
        url = f"https://discord.com/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={urllib.parse.quote(REDIRECT_URI)}&response_type=code&scope=identify%20guilds"
        return web.HTTPFound(url)

    async def callback(self, request):
        code = request.query.get('code')
        if not code: return web.HTTPForbidden(text="Thiếu mã xác thực!")

        async with aiohttp.ClientSession() as session:
            token_resp = await session.post(
                "https://discord.com/api/oauth2/token",
                data={
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": REDIRECT_URI
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            token_data = await token_resp.json()
            access_token = token_data.get("access_token")

            if not access_token: return web.HTTPForbidden(text="Lỗi xác thực OAuth2!")

            user_resp = await session.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {access_token}"})
            user_data = await user_resp.json()
            
            guilds_resp = await session.get("https://discord.com/api/users/@me/guilds", headers={"Authorization": f"Bearer {access_token}"})
            guilds_data = await guilds_resp.json()

        manageable_guilds = []
        bot_guild_ids = [str(g.id) for g in self.bot.guilds]

        for g in guilds_data:
            perms = int(g.get("permissions", 0))
            is_admin_or_manage = (perms & 0x8) == 0x8 or (perms & 0x20) == 0x20
            if is_admin_or_manage and str(g["id"]) in bot_guild_ids:
                manageable_guilds.append(g)

        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {"user": user_data, "guilds": manageable_guilds}
        
        response = web.HTTPFound('/')
        response.set_cookie('session_id', session_id)
        return response

    async def home_page(self, request):
        session_id = request.cookies.get('session_id')
        user_session = self.sessions.get(session_id)

        if not user_session:
            return web.Response(text="""
            <!DOCTYPE html>
            <html lang="vi">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Elfaria Dashboard</title>
                <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
                <style>
                    body { margin: 0; font-family: 'Inter', sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; }
                    .login-box { text-align: center; background: rgba(30, 41, 59, 0.7); padding: 50px 40px; border-radius: 20px; backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); }
                    h1 { font-size: 2.5rem; margin-bottom: 10px; background: linear-gradient(to right, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
                    p { color: #94a3b8; margin-bottom: 30px; font-size: 1.1rem; }
                    .btn { display: inline-block; background: #5865F2; color: white; text-decoration: none; padding: 14px 32px; border-radius: 12px; font-weight: 600; font-size: 1.1rem; transition: all 0.3s ease; box-shadow: 0 4px 14px 0 rgba(88, 101, 242, 0.39); }
                    .btn:hover { background: #4752c4; transform: translateY(-2px); box-shadow: 0 6px 20px rgba(88, 101, 242, 0.4); }
                </style>
            </head>
            <body>
                <div class="login-box">
                    <h1>🤖 Elfaria Core</h1>
                    <p>Hệ thống quản trị trung tâm dành cho Quản trị viên.</p>
                    <a href="/login" class="btn">Đăng nhập bằng Discord</a>
                </div>
            </body>
            </html>
            """, content_type='text/html')

        guilds_html = "".join([f"""
            <a href="/server/{g['id']}" class="server-card">
                <img src="https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'" alt="Icon">
                <div class="info">
                    <h3>{g['name']}</h3>
                    <p>Nhấn để cấu hình ➔</p>
                </div>
            </a>
        """ for g in user_session["guilds"]])

        # ĐÃ SỬA LỖI NGOẶC KÉP Ở DÒNG DƯỚI NÀY:
        if not guilds_html: 
            guilds_html = "<div class='empty-state'>Bạn không quản lý máy chủ nào có chứa bot Elfaria.</div>"

        return web.Response(text=f"""
        <!DOCTYPE html>
        <html lang="vi">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Trang Chủ | Elfaria Dashboard</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap" rel="stylesheet">
            <style>
                body {{ margin: 0; font-family: 'Inter', sans-serif; background: #0f172a; color: #f8fafc; padding: 60px 20px; }}
                .container {{ max-width: 1000px; margin: 0 auto; }}
                .header {{ text-align: center; margin-bottom: 50px; }}
                .header h2 {{ font-size: 2.2rem; font-weight: 800; margin-bottom: 10px; }}
                .header span {{ color: #818cf8; }}
                .header p {{ color: #94a3b8; font-size: 1.1rem; }}
                .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 24px; }}
                .server-card {{ display: flex; align-items: center; background: #1e293b; padding: 20px; border-radius: 16px; text-decoration: none; color: white; border: 1px solid rgba(255,255,255,0.05); transition: all 0.3s ease; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
                .server-card:hover {{ transform: translateY(-5px); border-color: #6366f1; box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.2); }}
                .server-card img {{ width: 64px; height: 64px; border-radius: 50%; object-fit: cover; margin-right: 20px; border: 2px solid rgba(255,255,255,0.1); }}
                .info h3 {{ margin: 0 0 5px 0; font-size: 1.2rem; }}
                .info p {{ margin: 0; color: #94a3b8; font-size: 0.9rem; font-weight: 500; transition: color 0.3s ease; }}
                .server-card:hover .info p {{ color: #818cf8; }}
                .empty-state {{ text-align: center; padding: 40px; background: #1e293b; border-radius: 16px; grid-column: 1 / -1; color: #94a3b8; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Xin chào, <span>{user_session['user']['username']}</span>! 👋</h2>
                    <p>Chọn máy chủ bên dưới để bắt đầu tuỳ chỉnh tính năng cho bot.</p>
                </div>
                <div class="grid">
                    {guilds_html}
                </div>
            </div>
        </body>
        </html>
        """, content_type='text/html')

    async def server_panel(self, request):
        guild_id = request.match_info.get('guild_id')
        session_id = request.cookies.get('session_id')
        user_session = self.sessions.get(session_id)

        if not user_session: return web.HTTPFound('/')
        
        valid_guild = next((g for g in user_session["guilds"] if str(g["id"]) == guild_id), None)
        if not valid_guild: return web.HTTPForbidden(text="Bạn không có quyền quản lý server này!")

        config = self.load_config()
        server_config = config.get(guild_id, {"modules": {"ai_chat": True, "image_tools": True}})
        modules = server_config.get("modules", {})

        module_details = {
            "ai_chat": {"name": "Trợ lý Trí tuệ Nhân tạo (AI)", "desc": "Cho phép bot trả lời tự động bằng ngữ cảnh thông minh khi được tag."},
            "image_tools": {"name": "Công cụ Xử lý Ảnh", "desc": "Mở khoá lệnh !tachnen để xóa nền ảnh tự động bằng AI."}
        }

        modules_html = ""
        for key, info in module_details.items():
            is_checked = "checked" if modules.get(key, True) else ""
            modules_html += f"""
            <div class="module-card">
                <div class="module-info">
                    <h3>{info['name']}</h3>
                    <p>{info['desc']}</p>
                </div>
                <label class="switch">
                    <input type="checkbox" onchange="toggleModule('{key}', this.checked)" {is_checked}>
                    <span class="slider"></span>
                </label>
            </div>
            """

        html = f"""
        <!DOCTYPE html>
        <html lang="vi">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Cấu hình {valid_guild['name']}</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
            <style>
                body {{ margin: 0; font-family: 'Inter', sans-serif; background: #0f172a; color: #f8fafc; padding: 40px 20px; }}
                .container {{ max-width: 800px; margin: 0 auto; }}
                .top-bar {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 40px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 20px; }}
                .back-btn {{ color: #94a3b8; text-decoration: none; font-weight: 500; display: flex; align-items: center; gap: 8px; transition: color 0.2s; }}
                .back-btn:hover {{ color: white; }}
                .server-title {{ display: flex; align-items: center; gap: 15px; }}
                .server-title img {{ width: 48px; height: 48px; border-radius: 50%; border: 2px solid rgba(255,255,255,0.1); }}
                .server-title h1 {{ margin: 0; font-size: 1.8rem; font-weight: 700; }}
                
                .module-card {{ background: #1e293b; padding: 25px; border-radius: 16px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border: 1px solid rgba(255,255,255,0.05); transition: 0.3s; }}
                .module-card:hover {{ border-color: rgba(99, 102, 241, 0.5); background: #233044; }}
                .module-info h3 {{ margin: 0 0 8px 0; font-size: 1.2rem; color: white; font-weight: 600; }}
                .module-info p {{ margin: 0; color: #94a3b8; font-size: 0.95rem; line-height: 1.5; padding-right: 20px; }}
                
                .switch {{ position: relative; display: inline-block; width: 52px; height: 28px; flex-shrink: 0; }}
                .switch input {{ opacity: 0; width: 0; height: 0; }}
                .slider {{ position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #334155; transition: .4s; border-radius: 34px; box-shadow: inset 0 2px 4px rgba(0,0,0,0.3); }}
                .slider:before {{ position: absolute; content: ""; height: 20px; width: 20px; left: 4px; bottom: 4px; background-color: white; transition: .4s cubic-bezier(0.4, 0.0, 0.2, 1); border-radius: 50%; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }}
                input:checked + .slider {{ background-color: #10b981; }}
                input:checked + .slider:before {{ transform: translateX(24px); }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="top-bar">
                    <div class="server-title">
                        <img src="https://cdn.discordapp.com/icons/{valid_guild['id']}/{valid_guild['icon']}.png" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                        <h1>{valid_guild['name']}</h1>
                    </div>
                    <a href="/" class="back-btn">
                        <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path></svg>
                        Trở về
                    </a>
                </div>
                
                {modules_html}
            </div>

            <script>
                async function toggleModule(moduleName, isEnabled) {{
                    try {{
                        await fetch('/api/toggle-module', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ guild_id: "{guild_id}", module: moduleName, state: isEnabled }})
                        }});
                    }} catch (e) {{
                        console.error("Lỗi đồng bộ dữ liệu: ", e);
                    }}
                }}
            </script>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')

    async def toggle_module(self, request):
        data = await request.json()
        guild_id = data.get("guild_id")
        module_name = data.get("module")
        state = data.get("state")

        config = self.load_config()
        if guild_id not in config:
            config[guild_id] = {"modules": {}}
            
        config[guild_id]["modules"][module_name] = state
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