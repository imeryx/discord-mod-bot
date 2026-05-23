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
            <body style="background:#2b2d31; color:white; font-family:sans-serif; text-align:center; padding-top:150px;">
                <h1>🤖 Elfaria Bot Dashboard</h1>
                <p>Vui lòng đăng nhập để quản lý các máy chủ của bạn.</p>
                <a href="/login" style="display:inline-block; margin-top:20px; background:#5865F2; padding:12px 25px; color:white; text-decoration:none; border-radius:4px; font-weight:bold;">Đăng nhập bằng Discord</a>
            </body>
            """, content_type='text/html')

        guilds_html = "".join([f"""
            <a href="/server/{g['id']}" style="display:flex; align-items:center; background:#1e1e24; padding:15px; margin:10px auto; max-width:400px; border-radius:8px; text-decoration:none; color:white; transition:0.2s;">
                <img src="https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'" style="width:40px; border-radius:50%; margin-right:15px;">
                <b>{g['name']}</b>
            </a>
        """ for g in user_session["guilds"]])

        if not guilds_html: guilds_html = "<p style='color:#ed4245;'>Bạn không quản lý máy chủ nào có chứa bot Elfaria.</p>"

        return web.Response(text=f"""
        <body style="background:#2b2d31; color:white; font-family:sans-serif; text-align:center; padding-top:50px;">
            <h2>Xin chào, {user_session['user']['username']}!</h2>
            <p>Chọn máy chủ để tùy chỉnh lệnh:</p>
            {guilds_html}
        </body>
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
            "ai_chat": {"name": "Trợ lý AI", "desc": "Chat AI với bot."},
            "image_tools": {"name": "Tách Nền Ảnh", "desc": "Lệnh !tachnen."}
        }

        modules_html = ""
        for key, info in module_details.items():
            is_checked = "checked" if modules.get(key, True) else ""
            modules_html += f"""
            <div style="background:#2b2d31; padding:20px; border-radius:8px; display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
                <div>
                    <h3 style="margin:0;">{info['name']}</h3>
                    <p style="margin:5px 0 0; color:#a3a6aa; font-size:14px;">{info['desc']}</p>
                </div>
                <label class="switch" style="position:relative; display:inline-block; width:44px; height:24px;">
                    <input type="checkbox" onchange="toggleModule('{key}', this.checked)" {is_checked} style="opacity:0; width:0; height:0;">
                    <span class="slider" style="position:absolute; cursor:pointer; top:0; left:0; right:0; bottom:0; background-color:#72767d; border-radius:34px; transition:.4s;"></span>
                </label>
            </div>
            """

        html = f"""
        <!DOCTYPE html>
        <html lang="vi">
        <head>
            <meta charset="UTF-8">
            <title>Quản lý - {valid_guild['name']}</title>
            <style>
                body {{ background: #1e1e24; color: white; font-family: sans-serif; padding: 40px; max-width: 800px; margin: auto; }}
                a.back-btn {{ color: #5865F2; text-decoration: none; font-weight: bold; margin-bottom: 20px; display: inline-block; }}
                input:checked + .slider {{ background-color: #43b581; }}
                input:checked + .slider::before {{ transform: translateX(20px); }}
                .slider::before {{ position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; border-radius: 50%; transition: .4s; }}
            </style>
        </head>
        <body>
            <a href="/" class="back-btn">⬅ Quay lại danh sách Server</a>
            <h1>⚙ Cấu hình: {valid_guild['name']}</h1>
            {modules_html}
            <script>
                async function toggleModule(moduleName, isEnabled) {{
                    await fetch('/api/toggle-module', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ guild_id: "{guild_id}", module: moduleName, state: isEnabled }})
                    }});
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