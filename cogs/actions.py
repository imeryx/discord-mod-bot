import discord
from discord.ext import commands
import random
import aiohttp

class Actions(commands.Cog):
    # Khai báo dữ liệu làm thuộc tính của class để tránh lỗi Attribute Error
    ACTION_DATA = {
        "hug": ["ôm chầm lấy", "siết chặt", "trao cái ôm ấm áp cho", "vừa ôm vỗ lưng", "ôm từ phía sau", "ôm thật dịu dàng"],
        "cuddle": ["đang cuộn tròn ôm ấp", "rúc vào lòng", "ôm ấp thật thoải mái cùng", "đang cùng cuộn chăn ôm", "cuddle nhẹ nhàng với", "ôm ấp đầy tình cảm với"],
        "kiss": ["trao một nụ hôn lên má", "hôn nhẹ lên trán", "hôn thật nồng cháy", "hôn vào tay", "đặt một nụ hôn ngọt ngào", "hôn thật tình cảm"],
        "lick": ["liếm má", "liếm nhẹ lên tay", "liếm trêu đùa", "liếm mặt", "liếm lên mũi", "liếm đầy tinh nghịch"],
        "nom": ["ngấu nghiến cắn nhẹ", "nom vào tai", "cắn yêu vào tay", "nom má", "cắn nhẹ vào vai", "nom đầy đáng yêu"],
        "pat": ["vỗ đầu", "xoa đầu nhẹ nhàng", "vỗ đầu đầy cưng chiều", "xoa đầu thật yêu", "vỗ vỗ mái tóc", "vỗ đầu như cún cưng"],
        "poke": ["chọc vào má", "chọc lét", "chọc vào vai", "chọc nhẹ vào bụng", "chọc vào mũi", "chọc đùa"],
        "slap": ["tát nhẹ", "tát vào mặt", "tát một cái đau điếng", "tát cảnh cáo", "tát trượt", "tát thật mạnh"],
        "stare": ["nhìn chằm chằm vào", "liếc nhìn đầy bí ẩn", "nhìn đắm đuối", "nhìn không rời mắt", "nhìn với ánh mắt kỳ lạ", "nhìn một cách khó hiểu"],
        "highfive": ["đập tay high-five", "high-five thật mạnh", "high-five kiểu sành điệu", "đập tay chúc mừng", "high-five ăn mừng", "high-five thật kêu"],
        "bite": ["cắn nhẹ vào tay", "cắn yêu", "cắn vào vai", "cắn trêu đùa", "cắn vào má", "cắn thật mạnh"],
        "greet": ["chào hỏi nhiệt tình", "vẫy tay chào", "cúi chào", "chào một cách vui vẻ", "chào bằng cái bắt tay", "chào đầy thân thiện"],
        "punch": ["đấm nhẹ", "đấm vào vai", "đấm một cái thật đau", "đấm trêu", "đấm vào bụng", "đấm thật mạnh"],
        "handholding": ["nắm chặt tay", "cầm tay đi dạo", "nắm tay đầy tình cảm", "đan tay vào nhau", "nắm lấy bàn tay", "cầm tay thật âu yếm"],
        "tickle": ["chọc lét", "chọc cười đến lăn lộn", "chọc vào nách", "chọc lét thật mạnh", "chọc lét khiến đối phương cười", "chọc lét trêu đùa"],
        "kill": ["thủ tiêu", "tiêu diệt", "loại bỏ", "kết thúc", "xử lý", "tiễn đi"],
        "hold": ["ôm giữ lấy", "giữ chặt", "nâng niu", "ôm ấp", "nắm giữ", "ôm không rời"],
        "pats": ["vỗ vỗ yêu thương", "xoa xoa đầu", "xoa má", "vỗ nhẹ", "xoa xoa thật dịu dàng", "vỗ đầu vỗ vai"],
        "wave": ["vẫy tay chào", "vẫy vẫy", "vẫy tay nhiệt tình", "vẫy tay tạm biệt", "vẫy tay đầy thân thiện", "vẫy tay chào kiểu vui vẻ"],
        "boop": ["chạm nhẹ vào mũi", "boop cái mũi", "chọc vào mũi", "boop boop", "chạm vào chóp mũi", "boop đầy đáng yêu"],
        "snuggle": ["rúc vào lòng", "snuggle ấm áp", "ôm ấp thắm thiết", "cùng snuggle", "snuggle thật dịu dàng", "ôm chặt tình cảm"],
        "bully": ["trêu chọc", "bắt nạt nhẹ", "làm khó", "trêu đùa", "bắt nạt đầy tinh nghịch", "cà khịa"]
    }

    API_MAPPING = {
        "hug": "hug", "kiss": "kiss", "pat": "pat", 
        "slap": "slap", "cuddle": "cuddle", "bite": "bite",
        "poke": "poke", "tickle": "tickle", "handholding": "handhold",
        "boop": "boop", "snuggle": "snuggle"
    }

    def __init__(self, bot):
        self.bot = bot
        # Đăng ký các lệnh
        for action in self.ACTION_DATA.keys():
            self.register_action(action)

    def register_action(self, action_name):
        @commands.command(name=action_name)
        async def action_cmd(ctx, member: discord.Member):
            if member.id == ctx.author.id:
                return await ctx.send(f"Bạn tự {action_name} chính mình sao? 😅")
            
            action_text = random.choice(self.ACTION_DATA.get(action_name, ["tương tác với"]))
            gif_url = None

            try:
                endpoint = self.API_MAPPING.get(action_name)
                if endpoint:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"https://nekos.best/api/v2/{endpoint}") as response:
                            if response.status == 200:
                                data = await response.json()
                                gif_url = data['results'][0]['url']
            except Exception as e:
                print(f"Lỗi khi lấy GIF từ API: {e}")
            
            embed = discord.Embed(
                description=f"🐰 **{ctx.author.name}** {action_text} **{member.name}**.",
                color=discord.Color.from_rgb(random.randint(0,255), random.randint(0,255), random.randint(0,255))
            )
            if gif_url:
                embed.set_image(url=gif_url)
            
            await ctx.send(embed=embed)
            
        # Thêm lệnh vào bot
        self.bot.add_command(action_cmd)

async def setup(bot):
    await bot.add_cog(Actions(bot))