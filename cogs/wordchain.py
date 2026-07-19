import discord
from discord.ext import commands
from discord import app_commands
import os
import datetime
import json # Thêm thư viện xử lý JSON

class WordChain(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "wordchain_data.json" # File lưu trữ bộ nhớ
        
        # Khởi tạo biến lưu trữ
        self.active_channels = {} 
        self.game_state = {} 
        
        self.emoji_correct = "<a:verify:1526434881859489843>"
        self.emoji_wrong = "<a:misc_cross:1526435817839530035>"
        self.emoji_used = "<a:maruloader:1526436267011735713>"
        self.emoji_spam = "<a:Warning:1526436603541590047>"

        # Tải bộ nhớ từ file JSON nếu có
        self.load_data()

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
    # HỆ THỐNG QUẢN LÝ BỘ NHỚ (LOAD/SAVE)
    # ==========================================
    def load_data(self):
        """Đọc dữ liệu từ file JSON khi bot khởi động"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.active_channels = data.get('active_channels', {})
                    raw_state = data.get('game_state', {})
                    
                    # Chuyển đổi 'used' từ dạng list (trong JSON) trở lại thành set (để xử lý nhanh hơn)
                    for guild_id_str, state in raw_state.items():
                        self.game_state[guild_id_str] = {
                            'last_word': state['last_word'],
                            'used': set(state['used']),
                            'last_user': state['last_user']
                        }
                print("-> Cog [WordChain] Đã khôi phục bộ nhớ trò chơi từ Disk.")
            except Exception as e:
                print(f"-> Cog [WordChain] Lỗi khi đọc file bộ nhớ: {e}")

    def save_data(self):
        """Lưu toàn bộ tiến trình hiện tại vào file JSON"""
        state_to_save = {}
        for guild_id_str, state in self.game_state.items():
            state_to_save[guild_id_str] = {
                'last_word': state['last_word'],
                'used': list(state['used']), # Ép kiểu set thành list để JSON hiểu được
                'last_user': state['last_user']
            }
        
        data_to_dump = {
            'active_channels': self.active_channels,
            'game_state': state_to_save
        }
        
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_dump, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"-> Cog [WordChain] Lỗi khi ghi file bộ nhớ: {e}")

    # ==========================================
    # LỆNH ĐIỀU KHIỂN CHẾ ĐỘ
    # ==========================================
    @app_commands.command(name="start_noitu_vn", description="Bắt đầu chơi nối từ Tiếng Việt (Nối theo tiếng)")
    @app_commands.default_permissions(manage_messages=True)
    async def start_vn(self, interaction: discord.Interaction):
        guild_str = str(interaction.guild_id) # Phải ép thành chuỗi (str) cho JSON
        self.active_channels[guild_str] = {'channel': interaction.channel_id, 'mode': 'vn'}
        self.game_state[guild_str] = {'last_word': '', 'used': set(), 'last_user': 0}
        
        self.save_data() # LƯU TRẠNG THÁI NGAY SAU KHI TẠO GAME MỚI
        
        await interaction.response.send_message(
            "🇻🇳 **Trò chơi Nối từ Tiếng Việt đã bắt đầu!**\n"
            "Luật chơi: Gõ từ ghép có đúng **2 tiếng** (VD: *hoa hồng*).\n"
            "⚠️ Kỷ luật: Ai tự nối 2 lần liên tiếp sẽ bị MUTE 1 phút!\n"
            "Mời người đầu tiên phát động!"
        )

    @app_commands.command(name="start_noitu_en", description="Bắt đầu chơi Word Chain Tiếng Anh (Nối theo chữ cái)")
    @app_commands.default_permissions(manage_messages=True)
    async def start_en(self, interaction: discord.Interaction):
        guild_str = str(interaction.guild_id)
        self.active_channels[guild_str] = {'channel': interaction.channel_id, 'mode': 'en'}
        self.game_state[guild_str] = {'last_word': '', 'used': set(), 'last_user': 0}
        
        self.save_data() # LƯU TRẠNG THÁI
        
        await interaction.response.send_message(
            "🇬🇧 **Trò chơi English Word Chain đã bắt đầu!**\n"
            "Luật chơi: Gõ **1 từ duy nhất**, chữ cái đầu phải khớp với chữ cái cuối của từ trước (VD: *appl**e** -> **e**lephan**t** -> **t**iger*).\n"
            "⚠️ Kỷ luật: Spam 2 lần liên tiếp = MUTE 1 phút!\n"
            "Hãy gõ một từ tiếng Anh bất kỳ để mở màn nhé!"
        )

    @app_commands.command(name="stop_noitu", description="Dừng trò chơi nối từ hiện tại")
    @app_commands.default_permissions(manage_messages=True)
    async def stop_game(self, interaction: discord.Interaction):
        guild_str = str(interaction.guild_id)
        if guild_str in self.active_channels:
            del self.active_channels[guild_str]
            del self.game_state[guild_str]
            
            self.save_data() # XÓA DỮ LIỆU CŨNG PHẢI LƯU LẠI VÀO FILE
            
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

        guild_str = str(message.guild.id)
        
        if guild_str not in self.active_channels:
            return
            
        game_info = self.active_channels[guild_str]
        if game_info['channel'] != message.channel.id:
            return

        word = message.content.lower().strip()
        words_split = word.split()
        mode = game_info['mode']
        state = self.game_state[guild_str]

        # SÀNG LỌC ĐỊNH DẠNG
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

        # KIỂM TRA TRÙNG LẶP
        if word in state['used']:
            await message.add_reaction(self.emoji_used)
            warning = await message.channel.send(f"Từ **{word}** đã được dùng rồi! Hãy nghĩ từ khác nhé.")
            await warning.delete(delay=3)
            return

        # Vượt qua bài kiểm tra -> Đánh dấu hợp lệ
        state['last_word'] = word
        state['used'].add(word)
        state['last_user'] = message.author.id
        
        self.save_data() # LƯU TRẠNG THÁI NGAY SAU KHI CÓ TỪ HỢP LỆ
        
        await message.add_reaction(self.emoji_correct)

async def setup(bot):
    await bot.add_cog(WordChain(bot))