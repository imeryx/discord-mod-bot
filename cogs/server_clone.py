import discord
from discord.ext import commands
from discord import app_commands
import json
import io
from datetime import datetime, timezone


class ServerClone(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("-> Cog [ServerClone] đã được tải thành công!")

    # ================= LỆNH BACKUP CẤU TRÚC SERVER =================
    @app_commands.command(
        name="backup_structure",
        description="Sao lưu toàn bộ cấu trúc server (vai trò, kênh, danh mục) ra file JSON"
    )
    @app_commands.default_permissions(administrator=True)
    async def backup_structure(self, interaction: discord.Interaction):
        """Gathers roles, categories, text channels, and voice channels
        from the current guild and sends the structure as an ephemeral
        JSON attachment (no messages are saved)."""

        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message(
                "❌ Lệnh này chỉ có thể dùng trong server!", ephemeral=True
            )

        # Defer vì quá trình thu thập dữ liệu có thể mất thời gian
        await interaction.response.defer(ephemeral=True)

        # ---------- 1. Thu thập Roles ----------
        roles_data = []
        for role in guild.roles:
            if role.is_default():
                continue  # Bỏ qua @everyone

            roles_data.append({
                "name": role.name,
                "color": str(role.color),
                "hoist": role.hoist,
                "position": role.position,
                "mentionable": role.mentionable,
                "permissions": role.permissions.value,
                "icon_url": role.icon.url if role.icon else None,
                "unicode_emoji": role.unicode_emoji,
            })

        # Sắp xếp theo vị trí giảm dần (role cao nhất trước)
        roles_data.sort(key=lambda r: r["position"], reverse=True)

        # ---------- 2. Thu thập Categories & Channels ----------
        categories_data = []
        uncategorized_channels = []

        for category in guild.categories:
            cat_entry = {
                "name": category.name,
                "position": category.position,
                "nsfw": category.nsfw,
                "permission_overwrites": self._serialize_overwrites(category),
                "text_channels": [],
                "voice_channels": [],
            }

            for ch in category.text_channels:
                cat_entry["text_channels"].append(self._serialize_text_channel(ch))

            for ch in category.voice_channels:
                cat_entry["voice_channels"].append(self._serialize_voice_channel(ch))

            categories_data.append(cat_entry)

        # Kênh không thuộc danh mục nào
        for ch in guild.channels:
            if ch.category is not None:
                continue
            if isinstance(ch, discord.TextChannel):
                uncategorized_channels.append({
                    "type": "text",
                    **self._serialize_text_channel(ch)
                })
            elif isinstance(ch, discord.VoiceChannel):
                uncategorized_channels.append({
                    "type": "voice",
                    **self._serialize_voice_channel(ch)
                })

        # ---------- 3. Xây dựng JSON tổng thể ----------
        backup = {
            "guild_name": guild.name,
            "guild_id": guild.id,
            "icon_url": guild.icon.url if guild.icon else None,
            "banner_url": guild.banner.url if guild.banner else None,
            "description": guild.description,
            "verification_level": str(guild.verification_level),
            "default_notifications": str(guild.default_notifications),
            "explicit_content_filter": str(guild.explicit_content_filter),
            "afk_timeout": guild.afk_timeout,
            "afk_channel": guild.afk_channel.name if guild.afk_channel else None,
            "system_channel": guild.system_channel.name if guild.system_channel else None,
            "rules_channel": guild.rules_channel.name if guild.rules_channel else None,
            "backup_timestamp": datetime.now(timezone.utc).isoformat(),
            "roles": roles_data,
            "categories": categories_data,
            "uncategorized_channels": uncategorized_channels,
        }

        # ---------- 4. Ghi vào bộ nhớ và gửi ----------
        json_bytes = json.dumps(backup, indent=2, ensure_ascii=False).encode("utf-8")
        buffer = io.BytesIO(json_bytes)
        filename = f"backup_{guild.name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"

        file = discord.File(fp=buffer, filename=filename)

        embed = discord.Embed(
            title="✅ Sao lưu cấu trúc server thành công!",
            description=(
                f"**Server:** {guild.name}\n"
                f"**Roles:** {len(roles_data)}\n"
                f"**Danh mục:** {len(categories_data)}\n"
                f"**Kênh không danh mục:** {len(uncategorized_channels)}"
            ),
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text="Backup Structure • Không bao gồm tin nhắn")

        await interaction.followup.send(embed=embed, file=file, ephemeral=True)

    # ================= HELPER: Serialize Permission Overwrites =================
    def _serialize_overwrites(self, channel) -> list:
        """Chuyển đổi permission overwrites của một kênh/danh mục thành dạng list dict."""
        overwrites = []
        for target, overwrite in channel.overwrites.items():
            allow, deny = overwrite.pair()
            overwrites.append({
                "target_name": target.name,
                "target_type": "role" if isinstance(target, discord.Role) else "member",
                "target_id": target.id,
                "allow": allow.value,
                "deny": deny.value,
            })
        return overwrites

    # ================= HELPER: Serialize Text Channel =================
    def _serialize_text_channel(self, ch: discord.TextChannel) -> dict:
        return {
            "name": ch.name,
            "position": ch.position,
            "topic": ch.topic,
            "nsfw": ch.nsfw,
            "slowmode_delay": ch.slowmode_delay,
            "default_auto_archive_duration": ch.default_auto_archive_duration,
            "permission_overwrites": self._serialize_overwrites(ch),
        }

    # ================= HELPER: Serialize Voice Channel =================
    def _serialize_voice_channel(self, ch: discord.VoiceChannel) -> dict:
        return {
            "name": ch.name,
            "position": ch.position,
            "bitrate": ch.bitrate,
            "user_limit": ch.user_limit,
            "rtc_region": str(ch.rtc_region) if ch.rtc_region else None,
            "permission_overwrites": self._serialize_overwrites(ch),
        }

    # ================= LỆNH LOAD BACKUP =================
    @app_commands.command(
        name="load_backup",
        description="Khôi phục cấu trúc server từ file JSON backup (tạo roles, danh mục, kênh)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(attachment="File JSON backup đã được tạo bởi /backup_structure")
    async def load_backup(self, interaction: discord.Interaction, attachment: discord.Attachment):
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message(
                "❌ Lệnh này chỉ có thể dùng trong server!", ephemeral=True
            )

        # Kiểm tra đuôi file
        if not attachment.filename.endswith(".json"):
            return await interaction.response.send_message(
                "❌ File không hợp lệ! Vui lòng gửi file có định dạng `.json`.", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        # ---------- Đọc và parse JSON ----------
        try:
            file_bytes = await attachment.read()
            data = json.loads(file_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return await interaction.followup.send(
                "❌ Không thể đọc file JSON! File có thể bị hỏng hoặc sai định dạng.", ephemeral=True
            )
        except Exception as e:
            return await interaction.followup.send(
                f"❌ Lỗi khi tải file: {e}", ephemeral=True
            )

        created_roles = 0
        created_categories = 0
        created_text = 0
        created_voice = 0
        errors = []

        # ---------- 1. Tạo Roles (từ thấp lên cao) ----------
        role_map: dict[str, discord.Role] = {}  # name -> created role
        roles_list = data.get("roles", [])
        # Sắp xếp theo position tăng dần để tạo role thấp trước
        roles_list.sort(key=lambda r: r.get("position", 0))

        for role_data in roles_list:
            try:
                name = role_data["name"]
                # Bỏ qua nếu role đã tồn tại
                existing = discord.utils.get(guild.roles, name=name)
                if existing:
                    role_map[name] = existing
                    continue

                color_value = role_data.get("color", "#000000")
                color = discord.Color.from_str(color_value) if color_value else discord.Color.default()

                new_role = await guild.create_role(
                    name=name,
                    color=color,
                    hoist=role_data.get("hoist", False),
                    mentionable=role_data.get("mentionable", False),
                    permissions=discord.Permissions(role_data.get("permissions", 0)),
                )
                role_map[name] = new_role
                created_roles += 1
            except Exception as e:
                errors.append(f"Role `{role_data.get('name', '?')}`: {e}")

        # ---------- 2. Tạo Categories & Channels ----------
        for cat_data in data.get("categories", []):
            try:
                cat_name = cat_data["name"]
                overwrites = self._deserialize_overwrites(guild, cat_data.get("permission_overwrites", []), role_map)

                category = await guild.create_category(
                    name=cat_name,
                    overwrites=overwrites,
                    position=cat_data.get("position", None),
                )
                created_categories += 1

                # --- Text channels trong danh mục ---
                for tc_data in cat_data.get("text_channels", []):
                    try:
                        tc_overwrites = self._deserialize_overwrites(guild, tc_data.get("permission_overwrites", []), role_map)
                        await guild.create_text_channel(
                            name=tc_data["name"],
                            category=category,
                            topic=tc_data.get("topic"),
                            nsfw=tc_data.get("nsfw", False),
                            slowmode_delay=tc_data.get("slowmode_delay", 0),
                            default_auto_archive_duration=tc_data.get("default_auto_archive_duration", 1440),
                            overwrites=tc_overwrites,
                            position=tc_data.get("position", None),
                        )
                        created_text += 1
                    except Exception as e:
                        errors.append(f"Text `{tc_data.get('name', '?')}`: {e}")

                # --- Voice channels trong danh mục ---
                for vc_data in cat_data.get("voice_channels", []):
                    try:
                        vc_overwrites = self._deserialize_overwrites(guild, vc_data.get("permission_overwrites", []), role_map)
                        await guild.create_voice_channel(
                            name=vc_data["name"],
                            category=category,
                            bitrate=min(vc_data.get("bitrate", 64000), guild.bitrate_limit),
                            user_limit=vc_data.get("user_limit", 0),
                            rtc_region=vc_data.get("rtc_region"),
                            overwrites=vc_overwrites,
                            position=vc_data.get("position", None),
                        )
                        created_voice += 1
                    except Exception as e:
                        errors.append(f"Voice `{vc_data.get('name', '?')}`: {e}")

            except Exception as e:
                errors.append(f"Category `{cat_data.get('name', '?')}`: {e}")

        # ---------- 3. Tạo kênh không thuộc danh mục nào ----------
        for ch_data in data.get("uncategorized_channels", []):
            try:
                ch_overwrites = self._deserialize_overwrites(guild, ch_data.get("permission_overwrites", []), role_map)
                ch_type = ch_data.get("type", "text")

                if ch_type == "text":
                    await guild.create_text_channel(
                        name=ch_data["name"],
                        topic=ch_data.get("topic"),
                        nsfw=ch_data.get("nsfw", False),
                        slowmode_delay=ch_data.get("slowmode_delay", 0),
                        default_auto_archive_duration=ch_data.get("default_auto_archive_duration", 1440),
                        overwrites=ch_overwrites,
                        position=ch_data.get("position", None),
                    )
                    created_text += 1
                elif ch_type == "voice":
                    await guild.create_voice_channel(
                        name=ch_data["name"],
                        bitrate=min(ch_data.get("bitrate", 64000), guild.bitrate_limit),
                        user_limit=ch_data.get("user_limit", 0),
                        rtc_region=ch_data.get("rtc_region"),
                        overwrites=ch_overwrites,
                        position=ch_data.get("position", None),
                    )
                    created_voice += 1
            except Exception as e:
                errors.append(f"Uncategorized `{ch_data.get('name', '?')}`: {e}")

        # ---------- 4. Gửi kết quả ----------
        embed = discord.Embed(
            title="✅ Khôi phục cấu trúc server hoàn tất!",
            color=discord.Color.green() if not errors else discord.Color.orange(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Roles đã tạo", value=str(created_roles), inline=True)
        embed.add_field(name="Danh mục đã tạo", value=str(created_categories), inline=True)
        embed.add_field(name="Kênh Text đã tạo", value=str(created_text), inline=True)
        embed.add_field(name="Kênh Voice đã tạo", value=str(created_voice), inline=True)

        if errors:
            error_text = "\n".join(errors[:15])  # Giới hạn 15 lỗi để tránh tràn embed
            if len(errors) > 15:
                error_text += f"\n...và {len(errors) - 15} lỗi khác"
            embed.add_field(name="⚠️ Lỗi", value=error_text, inline=False)

        embed.set_footer(text="Load Backup • Server Clone")
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ================= HELPER: Deserialize Permission Overwrites =================
    def _deserialize_overwrites(
        self,
        guild: discord.Guild,
        overwrites_data: list,
        role_map: dict[str, discord.Role],
    ) -> dict:
        """Chuyển list dict overwrites từ JSON thành dict[target, PermissionOverwrite]."""
        result = {}
        for ow in overwrites_data:
            target = None
            if ow["target_type"] == "role":
                # Tìm trong role_map trước, sau đó fallback theo ID
                target = role_map.get(ow["target_name"]) or guild.get_role(ow["target_id"])
            else:
                target = guild.get_member(ow["target_id"])

            if target is None:
                continue

            result[target] = discord.PermissionOverwrite.from_pair(
                discord.Permissions(ow.get("allow", 0)),
                discord.Permissions(ow.get("deny", 0)),
            )
        return result


async def setup(bot):
    await bot.add_cog(ServerClone(bot))
