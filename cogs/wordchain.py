import discord
from discord.ext import commands
from discord import app_commands
import os
import datetime 

class WordChain(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Lưu trữ cấu hình kênh: guild_id -> {'channel': channel_id, 'mode': 'vn' hoặc 'en'}
        self.active_channels = {} 
        self.game_state = {} 
        
        self.emoji_correct = "<a:verify:1526434881859489843>"
        self.emoji_wrong = "<a:misc_cross:1526435817839530035>"
        self.emoji_used = "<a:maruloader:1526436267011735713>"
        self.emoji_spam = "<a:Warning:1526436603541590047>"

        # 1. Tải từ điển TIẾNG VIỆT
        self.dict_vn = set()
        if os.path.exists("tu_dien_vn.txt"):
            with open("tu_dien_vn.txt", "r", encoding="utf-8") as f:
                self.dict_vn = set(word.strip().lower() for word in f.readlines() if word.strip())
            print(f"-> Cog [WordChain] Đã tải {len(self.dict_vn)} từ vựng Tiếng Việt.")
        else:
            print("-> Cog [WordChain] Cảnh báo: Thiếu file tu_dien_vn.txt!")

        # 2. Tải từ điển TIẾNG ANH
        self.dict_en = set()
        if os.path.exists("tu_dien_en.txt"):
            with open("tu_dien_en.txt", "r", encoding="utf-8") as f:
                self.dict_en = set(word.strip().lower() for word in f.readlines() if word.strip())
            print(f"-> Cog [WordChain] Đã tải {len(self.dict_en)} từ vựng Tiếng Anh.")
        else:
            print("-> Cog [WordChain] Cảnh báo: Thiếu file tu_dien_en.txt!")

    # ==========================================
    # LỆNH ĐIỀU KHIỂN CHẾ ĐỘ
    # ==========================================
    @app_commands.command(name="start_noitu_vn", description="Bắt đầu chơi nối từ Tiếng Việt (Nối theo tiếng)")
    @app_commands.default_permissions(manage_messages=True)
    async def start_vn(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        self.active_channels[guild_id] = {'channel': interaction.channel_id, 'mode': 'vn'}
        self.game_state[guild_id] = {'last_word': '', 'used': set(), 'last_user': 0}
        
        await interaction.response.send_message(
            "🇻🇳 **Trò chơi Nối từ Tiếng Việt đã bắt đầu!**\n"
            "Luật chơi: Gõ từ ghép có đúng **2 tiếng** (VD: *hoa hồng*).\n"
            "⚠️ Kỷ luật: Ai tự nối 2 lần liên tiếp sẽ bị MUTE 1 phút!\n"
            "Mời người đầu tiên phát động!"
        )

    @app_commands.command(name="start_noitu_en", description="Bắt đầu chơi Word Chain Tiếng Anh (Nối theo chữ cái)")
    @app_commands.default_permissions(manage_messages=True)
    async def start_en(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        self.active_channels[guild_id] = {'channel': interaction.channel_id, 'mode': 'en'}
        self.game_state[guild_id] = {'last_word': '', 'used': set(), 'last_user': 0}
        
        await interaction.response.send_message(
            "🇬🇧 **Trò chơi English Word Chain đã bắt đầu!**\n"
            "Luật chơi: Gõ **1 từ duy nhất**, chữ cái đầu phải khớp với chữ cái cuối của từ trước (VD: *appl**e** -> **e**lephan**t** -> **t**iger*).\n"
            "⚠️ Kỷ luật: Spam 2 lần liên tiếp = MUTE 1 phút!\n"
            "Hãy gõ một từ tiếng Anh bất kỳ để mở màn nhé!"
        )

    @app_commands.command(name="stop_noitu", description="Dừng trò chơi nối từ hiện tại")
    @app_commands.default_permissions(manage_messages=True)
    async def stop_game(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        if guild_id in self.active_channels:
            del self.active_channels[guild_id]
            del self.game_state[guild_id]
            await interaction.response.send_message("🛑 **Đã dừng trò chơi nối từ.** Hẹn gặp lại!")
        else:
            await interaction.response.send_message("⚠️ Server này hiện không có trò chơi nào đang chạy.", ephemeral=True)

    # ==========================================
    # LẮNG NGHE TIN NHẮN (TRỌNG TÀI)
    # ==========================================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        guild_id = message.guild.id
        
        if guild_id not in self.active_channels:
            return
            
        game_info = self.active_channels[guild_id]
        if game_info['channel'] != message.channel.id:
            return

        word = message.content.lower().strip()
        words_split = word.split()
        mode = game_info['mode']
        state = self.game_state[guild_id]

        # SÀNG LỌC ĐỊNH DẠNG: Bỏ qua các câu chat nhảm để không làm gián đoạn game
        if mode == 'vn' and len(words_split) != 2:
            return 
        if mode == 'en':
            if len(words_split) != 1 or not word.isalpha():
                return 

        # XỬ PHẠT: Nối 2 lần liên tiếp
        if state['last_user'] == message.author.id and state['last_word'] != '':
            await message.add_reaction(self.emoji_spam)
            try:
                duration = datetime.timedelta(minutes=1)
                await message.author.timeout(duration, reason="Phạm luật WordChain: Nối 2 lần liên tiếp")
                await message.channel.send(f"🚨 **BÍP BÍP!** {message.author.mention} đã bị cấm ngôn 1 phút vì tội tham lam, tự mình nối 2 lần liên tiếp! 🛑")
            except discord.Forbidden:
                pass
            return

        # KIỂM TRA LUẬT THEO TỪNG NGÔN NGỮ
        if mode == 'vn':
            if self.dict_vn and word not in self.dict_vn:
                await message.add_reaction(self.emoji_wrong)
                return
            
            if state['last_word'] != '':
                last_syllable = state['last_word'].split()[-1]
                first_syllable = words_split[0]
                if first_syllable != last_syllable:
                    await message.add_reaction(self.emoji_wrong)
                    return

        elif mode == 'en':
            if self.dict_en and word not in self.dict_en:
                await message.add_reaction(self.emoji_wrong)
                return
            
            if state['last_word'] != '':
                last_char = state['last_word'][-1]
                first_char = word[0]
                if first_char != last_char:
                    await message.add_reaction(self.emoji_wrong)
                    return

        # KIỂM TRA TRÙNG LẶP (Chung cho 2 chế độ)
        if word in state['used']:
            await message.add_reaction(self.emoji_used)
            warning = await message.channel.send(f"Từ **{word}** đã được dùng rồi! Hãy nghĩ từ khác nhé.")
            await warning.delete(delay=3)
            return

        # Vượt qua bài kiểm tra
        state['last_word'] = word
        state['used'].add(word)
        state['last_user'] = message.author.id
        await message.add_reaction(self.emoji_correct)

async def setup(bot):
    await bot.add_cog(WordChain(bot))