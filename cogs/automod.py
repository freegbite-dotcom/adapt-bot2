import re
import time
import datetime
import discord
from discord.ext import commands
from collections import defaultdict
from database import db
from utils.embeds import log_event


# ── Regex Patterns ────────────────────────────────────────────────────────────
URL_PATTERN = re.compile(
    r"(https?://|discord\.gg/|www\.)[^\s]+"
    r"|[a-zA-Z0-9\-]+\.(com|net|org|io|gg|xyz|co|me|tv|live|app|dev|gg)[^\s]*",
    re.IGNORECASE,
)
INVITE_PATTERN = re.compile(
    r"(discord\.gg|discord\.com/invite|discordapp\.com/invite)/[a-zA-Z0-9\-]+",
    re.IGNORECASE,
)


class AutoMod(commands.Cog):
    """Automatic moderation — spam, links, invites, bad words, and mentions."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # { guild_id: { user_id: [timestamps] } }
        self._message_cache: dict[int, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        if message.author.guild_permissions.manage_messages:
            return  # Mods are exempt

        cfg = await db.get_guild(message.guild.id)
        if not cfg or not cfg["automod_enabled"]:
            return

        # Whitelists check
        whitelist_roles = cfg.get("automod_whitelist_roles") or []
        whitelist_channels = cfg.get("automod_whitelist_channels") or []

        if message.channel.id in whitelist_channels:
            return
        if any(r.id in whitelist_roles for r in message.author.roles):
            return

        # Run checks - first match wins
        if cfg["automod_spam"] and await self._check_spam(message, cfg):
            return
        if cfg["automod_invites"] and await self._check_invites(message, cfg):
            return
        if cfg["automod_links"] and await self._check_links(message, cfg):
            return
        if cfg["automod_mentions"] and await self._check_mentions(message, cfg):
            return
        if cfg["automod_badwords"] and await self._check_badwords(message, cfg):
            return

    # ── Spam Check ────────────────────────────────────────────────────────────
    async def _check_spam(self, message: discord.Message, cfg) -> bool:
        uid = message.author.id
        gid = message.guild.id
        now = time.monotonic()
        
        spam_count = cfg.get("automod_spam_count", 5)
        spam_interval = float(cfg.get("automod_spam_interval", 5))
        action = cfg.get("automod_spam_action", "timeout")

        times = self._message_cache[gid][uid]
        times = [t for t in times if now - t < spam_interval]
        times.append(now)
        self._message_cache[gid][uid] = times

        if len(times) < spam_count:
            return False

        # Clear cache for this user
        self._message_cache[gid][uid] = []

        # Delete recent messages from user in this channel
        try:
            def is_spam(m):
                return m.author.id == uid
            await message.channel.purge(limit=spam_count + 2, check=is_spam)
        except discord.Forbidden:
            pass

        reason = f"Automated anti-spam threshold exceeded ({spam_count} msgs in {spam_interval}s)"
        await self._execute_action(message, cfg, "spam", action, reason, "Anti-Spam Triggered")
        return True

    # ── Invites Check ─────────────────────────────────────────────────────────
    async def _check_invites(self, message: discord.Message, cfg) -> bool:
        if not INVITE_PATTERN.search(message.content):
            return False

        try:
            await message.delete()
        except discord.Forbidden:
            pass

        action = cfg.get("automod_invites_action", "delete")
        reason = "Posting Discord server invite links is prohibited"
        await self._execute_action(message, cfg, "invites", action, reason, message.content)
        return True

    # ── Links Check ───────────────────────────────────────────────────────────
    async def _check_links(self, message: discord.Message, cfg) -> bool:
        # Ignore if it is just a Discord invite (checked separately)
        if INVITE_PATTERN.search(message.content):
            return False
        if not URL_PATTERN.search(message.content):
            return False

        try:
            await message.delete()
        except discord.Forbidden:
            pass

        action = cfg.get("automod_links_action", "delete")
        reason = "Posting links is not allowed in this channel"
        await self._execute_action(message, cfg, "links", action, reason, message.content)
        return True

    # ── Mentions Check ────────────────────────────────────────────────────────
    async def _check_mentions(self, message: discord.Message, cfg) -> bool:
        limit = cfg.get("automod_mentions_limit", 5)
        
        # Calculate unique user & role mentions
        mention_count = len(message.mentions) + len(message.role_mentions)
        if mention_count <= limit:
            return False

        try:
            await message.delete()
        except discord.Forbidden:
            pass

        action = cfg.get("automod_mentions_action", "delete")
        reason = f"Message exceeded mass-mention limit of {limit} ({mention_count} mentions)"
        await self._execute_action(message, cfg, "mentions", action, reason, f"{mention_count} mentions")
        return True

    # ── Bad Words Check ───────────────────────────────────────────────────────
    async def _check_badwords(self, message: discord.Message, cfg) -> bool:
        words = cfg.get("automod_badwords_list") or []
        content = message.content.lower()

        triggered = next((w for w in words if re.search(rf"\b{re.escape(w)}\b", content)), None)
        if not triggered:
            return False

        try:
            await message.delete()
        except discord.Forbidden:
            pass

        action = cfg.get("automod_badwords_action", "delete")
        reason = f"Prohibited word detected: '{triggered}'"
        await self._execute_action(message, cfg, "badwords", action, reason, f"Word: '{triggered}'")
        return True

    # ── Action Execution Handler ──────────────────────────────────────────────
    async def _execute_action(self, message: discord.Message, cfg, rule: str, action: str, reason: str, detail: str = None):
        guild = message.guild
        member = message.author
        action = action.lower()

        # Send temporary warning to channel (unless kicked/banned)
        warning_msg = f"⚠️ {member.mention} — {reason}"
        
        action_desc = "Message deleted"
        
        # Determine punishment
        if action == "warn":
            # Add warning to database
            await db.add_warning(guild.id, member.id, self.bot.user.id, f"[AutoMod] {reason}")
            action_desc = "Warning logged"
            try:
                await message.channel.send(f"⚠️ {member.mention} — {reason}. **Warning logged**.", delete_after=5)
            except discord.Forbidden:
                pass
                
        elif action == "timeout":
            action_desc = "5 minute timeout applied"
            try:
                await member.timeout(datetime.timedelta(minutes=5), reason=f"[AutoMod] {reason}")
                await message.channel.send(f"🛡️ {member.mention} — {reason}. **5 minute timeout applied**.", delete_after=8)
            except discord.Forbidden:
                pass
                
        elif action == "kick":
            action_desc = "Kicked from server"
            try:
                await member.kick(reason=f"[AutoMod] {reason}")
                await message.channel.send(f"🛡️ **{member}** was kicked. **Reason:** {reason}.", delete_after=10)
            except discord.Forbidden:
                pass
                
        elif action == "ban":
            action_desc = "Banned from server"
            try:
                await member.ban(reason=f"[AutoMod] {reason}", delete_message_seconds=0)
                await message.channel.send(f"🚨 **{member}** was banned. **Reason:** {reason}.", delete_after=10)
            except discord.Forbidden:
                pass
        else:
            # "delete" or fallback
            try:
                await message.channel.send(warning_msg, delete_after=5)
            except discord.Forbidden:
                pass

        # Try to DM user
        try:
            await member.send(
                f"🛡️ Your message in **{guild.name}** was moderated.\n"
                f"**Reason:** {reason}\n"
                f"**Action Taken:** {action_desc}"
            )
        except (discord.Forbidden, discord.HTTPException):
            pass

        # Log action to database
        await db.add_automod_log(guild.id, member.id, rule, detail or reason, action_desc)

        # Log action to mod channel
        await self._log_to_channel(guild, cfg, rule, member, reason, action_desc, detail)

    async def _log_to_channel(self, guild: discord.Guild, cfg, rule: str, member: discord.Member, reason: str, action_taken: str, detail: str):
        channel_id = cfg.get("automod_log_channel_id") or cfg.get("log_channel_id")
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if not channel:
            return

        icons = {"spam": "🔁", "links": "🔗", "invites": "📨", "badwords": "🤬", "mentions": "🔊"}
        embed = log_event(
            f"{icons.get(rule, '🛡️')} AutoMod — {rule.title()}",
            color=discord.Color.orange(),
        )
        embed.add_field(name="Member", value=f"{member.mention} (`{member}`)", inline=True)
        embed.add_field(name="Action Taken", value=f"**{action_taken}**", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        if detail and rule not in ["spam", "mentions"]:
            embed.add_field(name="Trigger Content", value=detail[:300], inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)

        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoMod(bot))
