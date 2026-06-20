import logging
import asyncpg
import config

log = logging.getLogger("db")

_pool: asyncpg.Pool | None = None


async def create_pool() -> asyncpg.Pool:
    global _pool
    _pool = await asyncpg.create_pool(dsn=config.DATABASE_URL, min_size=1, max_size=5, command_timeout=60)
    log.info("✅  Database pool created")
    
    # Auto-migrate database schema for customizable AutoMod
    try:
        async with _pool.acquire() as conn:
            await conn.execute("""
                ALTER TABLE guild_settings 
                ADD COLUMN IF NOT EXISTS automod_spam_count INT DEFAULT 5,
                ADD COLUMN IF NOT EXISTS automod_spam_interval INT DEFAULT 5,
                ADD COLUMN IF NOT EXISTS automod_spam_action VARCHAR(20) DEFAULT 'timeout',
                ADD COLUMN IF NOT EXISTS automod_links_action VARCHAR(20) DEFAULT 'delete',
                ADD COLUMN IF NOT EXISTS automod_invites BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS automod_invites_action VARCHAR(20) DEFAULT 'delete',
                ADD COLUMN IF NOT EXISTS automod_badwords_action VARCHAR(20) DEFAULT 'delete',
                ADD COLUMN IF NOT EXISTS automod_mentions BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS automod_mentions_limit INT DEFAULT 5,
                ADD COLUMN IF NOT EXISTS automod_mentions_action VARCHAR(20) DEFAULT 'delete',
                ADD COLUMN IF NOT EXISTS automod_whitelist_roles BIGINT[] DEFAULT '{}',
                ADD COLUMN IF NOT EXISTS automod_whitelist_channels BIGINT[] DEFAULT '{}';
            """)
            log.info("✅  Database schema auto-migrated successfully")
    except Exception as e:
        log.warning(f"⚠️  Database schema auto-migration warning: {e}")
        
    return _pool


# ── Pool ──────────────────────────────────────────────────────────────────────



async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        log.info("🔌  Database pool closed")

def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool has not been initialised yet.")
    return _pool


# ── Guild Settings ────────────────────────────────────────────────────────────
import json
import os

LOCAL_SETTINGS_FILE = "database/local_settings.json"

def _load_local_settings() -> dict:
    if os.path.exists(LOCAL_SETTINGS_FILE):
        try:
            with open(LOCAL_SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_local_settings(data: dict):
    try:
        os.makedirs(os.path.dirname(LOCAL_SETTINGS_FILE), exist_ok=True)
        with open(LOCAL_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        log.error(f"Failed to save local settings: {e}")

GUILD_DEFAULTS = {
    "prefix": ".",
    "leveling_enabled": True,
    "xp_cooldown": 60,
    "xp_min": 15,
    "xp_max": 25,
    "level_up_message": "🎉 {user} has reached level {level}!",
    "level_up_channel_id": None,
    "economy_enabled": True,
    "currency_name": "coins",
    "currency_emoji": "🪙",
    "daily_amount": 100,
    "ticket_category_id": None,
    "ticket_support_role_id": None,
    "ticket_enabled": True,
    "log_channel_id": None,
    "mod_log_channel_id": None,
    "automod_enabled": False,
    "automod_spam": False,
    "automod_links": False,
    "automod_badwords": False,
    "automod_badwords_list": [],
    "automod_log_channel_id": None,
    "giveaway_emoji": "🎉",
    "giveaway_color": 5869821,
    "giveaway_ping_role_id": None,
    "giveaway_pin": False,
    "automod_spam_count": 5,
    "automod_spam_interval": 5,
    "automod_spam_action": "timeout",
    "automod_links_action": "delete",
    "automod_invites": False,
    "automod_invites_action": "delete",
    "automod_badwords_action": "delete",
    "automod_mentions": False,
    "automod_mentions_limit": 5,
    "automod_mentions_action": "delete",
    "automod_whitelist_roles": [],
    "automod_whitelist_channels": []
}

async def get_guild(guild_id: int) -> dict | None:
    if _pool is None:
        local_data = _load_local_settings()
        guild_key = str(guild_id)
        g_data = {"guild_id": guild_id}
        g_data.update(GUILD_DEFAULTS)
        if guild_key in local_data:
            g_data.update(local_data[guild_key])
        return g_data

    row = await get_pool().fetchrow("SELECT * FROM guild_settings WHERE guild_id = $1", guild_id)
    if not row:
        return None
    
    # Merge row with default settings so that missing keys don't trigger KeyError
    data = dict(row)
    for k, v in GUILD_DEFAULTS.items():
        if k not in data or data[k] is None:
            data[k] = v
    return data

async def ensure_guild(guild_id: int) -> dict:
    """Get guild settings, creating a default row if it doesn't exist."""
    row = await get_guild(guild_id)
    if _pool is not None and not row:
        await get_pool().execute(
            "INSERT INTO guild_settings (guild_id) VALUES ($1) ON CONFLICT DO NOTHING", guild_id
        )
        row = await get_guild(guild_id)
    return row

async def set_guild(guild_id: int, **kwargs) -> None:
    """Update one or more guild_settings columns."""
    if not kwargs:
        return
    if _pool is None:
        local_data = _load_local_settings()
        guild_key = str(guild_id)
        if guild_key not in local_data:
            local_data[guild_key] = {}
        local_data[guild_key].update(kwargs)
        _save_local_settings(local_data)
        return

    cols = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(kwargs))
    await get_pool().execute(
        f"UPDATE guild_settings SET {cols} WHERE guild_id = $1",
        guild_id, *kwargs.values()
    )

async def get_prefix(guild_id: int) -> str:
    row = await get_guild(guild_id)
    return row["prefix"] if row and "prefix" in row else config.PREFIX



# ── Mod Logs ──────────────────────────────────────────────────────────────────

async def add_mod_log(guild_id, target_id, moderator_id, action, reason=None, duration=None) -> int:
    row = await get_pool().fetchrow(
        "INSERT INTO mod_logs (guild_id, target_id, moderator_id, action, reason, duration) VALUES ($1,$2,$3,$4,$5,$6) RETURNING id",
        guild_id, target_id, moderator_id, action, reason, duration
    )
    return row["id"]

async def get_mod_logs(guild_id: int, target_id: int) -> list:
    return await get_pool().fetch(
        "SELECT * FROM mod_logs WHERE guild_id=$1 AND target_id=$2 ORDER BY created_at DESC", guild_id, target_id
    )


# ── Warnings ──────────────────────────────────────────────────────────────────

async def add_warning(guild_id, user_id, moderator_id, reason) -> int:
    row = await get_pool().fetchrow(
        "INSERT INTO warnings (guild_id, user_id, moderator_id, reason) VALUES ($1,$2,$3,$4) RETURNING id",
        guild_id, user_id, moderator_id, reason
    )
    return row["id"]

async def get_warnings(guild_id: int, user_id: int) -> list:
    return await get_pool().fetch(
        "SELECT * FROM warnings WHERE guild_id=$1 AND user_id=$2 ORDER BY created_at DESC", guild_id, user_id
    )

async def clear_warnings(guild_id: int, user_id: int) -> int:
    result = await get_pool().execute("DELETE FROM warnings WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)
    return int(result.split()[-1])


# ── Leveling ──────────────────────────────────────────────────────────────────

async def get_level(guild_id: int, user_id: int) -> asyncpg.Record | None:
    return await get_pool().fetchrow("SELECT * FROM levels WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)

async def add_xp(guild_id: int, user_id: int, xp: int) -> asyncpg.Record:
    return await get_pool().fetchrow(
        """INSERT INTO levels (guild_id, user_id, xp, last_message_at) VALUES ($1,$2,$3,NOW())
           ON CONFLICT (guild_id, user_id) DO UPDATE SET xp=levels.xp+EXCLUDED.xp, last_message_at=NOW()
           RETURNING *""",
        guild_id, user_id, xp
    )

async def set_level(guild_id: int, user_id: int, level: int) -> None:
    await get_pool().execute("UPDATE levels SET level=$3 WHERE guild_id=$1 AND user_id=$2", guild_id, user_id, level)

async def get_leaderboard(guild_id: int, limit: int = 10) -> list:
    return await get_pool().fetch("SELECT * FROM levels WHERE guild_id=$1 ORDER BY xp DESC LIMIT $2", guild_id, limit)

async def get_level_roles(guild_id: int) -> list:
    return await get_pool().fetch("SELECT * FROM level_roles WHERE guild_id=$1 ORDER BY level", guild_id)

async def set_level_role(guild_id: int, level: int, role_id: int) -> None:
    await get_pool().execute(
        "INSERT INTO level_roles (guild_id, level, role_id) VALUES ($1,$2,$3) ON CONFLICT (guild_id, level) DO UPDATE SET role_id=$3",
        guild_id, level, role_id
    )

async def remove_level_role(guild_id: int, level: int) -> None:
    await get_pool().execute("DELETE FROM level_roles WHERE guild_id=$1 AND level=$2", guild_id, level)


# ── Economy ───────────────────────────────────────────────────────────────────

async def get_economy(guild_id: int, user_id: int) -> asyncpg.Record | None:
    return await get_pool().fetchrow("SELECT * FROM economy WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)

async def ensure_economy(guild_id: int, user_id: int) -> asyncpg.Record:
    await get_pool().execute(
        "INSERT INTO economy (guild_id, user_id) VALUES ($1,$2) ON CONFLICT DO NOTHING", guild_id, user_id
    )
    return await get_economy(guild_id, user_id)

async def add_balance(guild_id: int, user_id: int, amount: int) -> asyncpg.Record:
    return await get_pool().fetchrow(
        "UPDATE economy SET balance=balance+$3 WHERE guild_id=$1 AND user_id=$2 RETURNING *",
        guild_id, user_id, amount
    )

async def set_daily(guild_id: int, user_id: int) -> None:
    await get_pool().execute("UPDATE economy SET last_daily=NOW() WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)

async def get_economy_leaderboard(guild_id: int, limit: int = 10) -> list:
    return await get_pool().fetch(
        "SELECT * FROM economy WHERE guild_id=$1 ORDER BY balance+bank DESC LIMIT $2", guild_id, limit
    )


# ── Shop ──────────────────────────────────────────────────────────────────────

async def get_shop(guild_id: int) -> list:
    return await get_pool().fetch("SELECT * FROM shop_items WHERE guild_id=$1 ORDER BY price", guild_id)

async def get_shop_item(item_id: int) -> asyncpg.Record | None:
    return await get_pool().fetchrow("SELECT * FROM shop_items WHERE id=$1", item_id)

async def add_shop_item(guild_id, name, description, price, role_id=None, stock=None) -> int:
    row = await get_pool().fetchrow(
        "INSERT INTO shop_items (guild_id, name, description, price, role_id, stock) VALUES ($1,$2,$3,$4,$5,$6) RETURNING id",
        guild_id, name, description, price, role_id, stock
    )
    return row["id"]

async def remove_shop_item(item_id: int) -> None:
    await get_pool().execute("DELETE FROM shop_items WHERE id=$1", item_id)


# ── Tickets ───────────────────────────────────────────────────────────────────

async def create_ticket(guild_id, channel_id, user_id, topic=None) -> int:
    row = await get_pool().fetchrow(
        "INSERT INTO tickets (guild_id, channel_id, user_id, topic) VALUES ($1,$2,$3,$4) RETURNING id",
        guild_id, channel_id, user_id, topic
    )
    return row["id"]

async def get_ticket(channel_id: int) -> asyncpg.Record | None:
    return await get_pool().fetchrow("SELECT * FROM tickets WHERE channel_id=$1", channel_id)

async def close_ticket(channel_id: int) -> None:
    await get_pool().execute(
        "UPDATE tickets SET status='closed', closed_at=NOW() WHERE channel_id=$1", channel_id
    )

async def get_user_open_ticket(guild_id: int, user_id: int) -> asyncpg.Record | None:
    return await get_pool().fetchrow(
        "SELECT * FROM tickets WHERE guild_id=$1 AND user_id=$2 AND status='open'", guild_id, user_id
    )


# ── Reaction Roles ────────────────────────────────────────────────────────────

async def add_reaction_role(guild_id, channel_id, message_id, emoji, role_id) -> None:
    await get_pool().execute(
        "INSERT INTO reaction_roles (guild_id, channel_id, message_id, emoji, role_id) VALUES ($1,$2,$3,$4,$5) ON CONFLICT (message_id, emoji) DO UPDATE SET role_id=$5",
        guild_id, channel_id, message_id, emoji, role_id
    )

async def get_reaction_role(message_id: int, emoji: str) -> asyncpg.Record | None:
    return await get_pool().fetchrow("SELECT * FROM reaction_roles WHERE message_id=$1 AND emoji=$2", message_id, emoji)

async def get_reaction_roles(guild_id: int) -> list:
    return await get_pool().fetch("SELECT * FROM reaction_roles WHERE guild_id=$1", guild_id)

async def remove_reaction_role(message_id: int, emoji: str) -> None:
    await get_pool().execute("DELETE FROM reaction_roles WHERE message_id=$1 AND emoji=$2", message_id, emoji)


# ── Custom Commands ───────────────────────────────────────────────────────────

async def get_custom_command(guild_id: int, name: str) -> asyncpg.Record | None:
    return await get_pool().fetchrow("SELECT * FROM custom_commands WHERE guild_id=$1 AND name=$2", guild_id, name)

async def get_custom_commands(guild_id: int) -> list:
    return await get_pool().fetch("SELECT * FROM custom_commands WHERE guild_id=$1 ORDER BY name", guild_id)

async def add_custom_command(guild_id, name, response, created_by) -> None:
    await get_pool().execute(
        "INSERT INTO custom_commands (guild_id, name, response, created_by) VALUES ($1,$2,$3,$4)",
        guild_id, name, response, created_by
    )

async def edit_custom_command(guild_id, name, response) -> None:
    await get_pool().execute("UPDATE custom_commands SET response=$3 WHERE guild_id=$1 AND name=$2", guild_id, name, response)

async def delete_custom_command(guild_id: int, name: str) -> None:
    await get_pool().execute("DELETE FROM custom_commands WHERE guild_id=$1 AND name=$2", guild_id, name)

async def increment_command_uses(guild_id: int, name: str) -> None:
    await get_pool().execute("UPDATE custom_commands SET uses=uses+1 WHERE guild_id=$1 AND name=$2", guild_id, name)


# ── Automod ───────────────────────────────────────────────────────────────────

async def add_automod_log(guild_id, user_id, rule, content=None, action_taken=None) -> None:
    await get_pool().execute(
        "INSERT INTO automod_logs (guild_id, user_id, rule, content, action_taken) VALUES ($1,$2,$3,$4,$5)",
        guild_id, user_id, rule, content, action_taken
    )

async def add_automod_whitelist_role(guild_id: int, role_id: int) -> None:
    if _pool is None:
        cfg = await get_guild(guild_id)
        roles = list(cfg.get("automod_whitelist_roles") or [])
        if role_id not in roles:
            roles.append(role_id)
            await set_guild(guild_id, automod_whitelist_roles=roles)
        return
    await get_pool().execute(
        "UPDATE guild_settings SET automod_whitelist_roles = array_append(COALESCE(automod_whitelist_roles, ARRAY[]::BIGINT[]), $2) WHERE guild_id = $1",
        guild_id, role_id
    )

async def remove_automod_whitelist_role(guild_id: int, role_id: int) -> None:
    if _pool is None:
        cfg = await get_guild(guild_id)
        roles = list(cfg.get("automod_whitelist_roles") or [])
        if role_id in roles:
            roles.remove(role_id)
            await set_guild(guild_id, automod_whitelist_roles=roles)
        return
    await get_pool().execute(
        "UPDATE guild_settings SET automod_whitelist_roles = array_remove(COALESCE(automod_whitelist_roles, ARRAY[]::BIGINT[]), $2) WHERE guild_id = $1",
        guild_id, role_id
    )

async def add_automod_whitelist_channel(guild_id: int, channel_id: int) -> None:
    if _pool is None:
        cfg = await get_guild(guild_id)
        channels = list(cfg.get("automod_whitelist_channels") or [])
        if channel_id not in channels:
            channels.append(channel_id)
            await set_guild(guild_id, automod_whitelist_channels=channels)
        return
    await get_pool().execute(
        "UPDATE guild_settings SET automod_whitelist_channels = array_append(COALESCE(automod_whitelist_channels, ARRAY[]::BIGINT[]), $2) WHERE guild_id = $1",
        guild_id, channel_id
    )

async def remove_automod_whitelist_channel(guild_id: int, channel_id: int) -> None:
    if _pool is None:
        cfg = await get_guild(guild_id)
        channels = list(cfg.get("automod_whitelist_channels") or [])
        if channel_id in channels:
            channels.remove(channel_id)
            await set_guild(guild_id, automod_whitelist_channels=channels)
        return
    await get_pool().execute(
        "UPDATE guild_settings SET automod_whitelist_channels = array_remove(COALESCE(automod_whitelist_channels, ARRAY[]::BIGINT[]), $2) WHERE guild_id = $1",
        guild_id, channel_id
    )




# ── Giveaways ─────────────────────────────────────────────────────────────────

async def create_giveaway(guild_id, channel_id, message_id, prize, description, winners_count, end_time, host_id) -> None:
    await get_pool().execute(
        """INSERT INTO giveaways (guild_id, channel_id, message_id, prize, description, winners_count, end_time, host_id, status)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'active')""",
        guild_id, channel_id, message_id, prize, description, winners_count, end_time, host_id
    )

async def get_giveaway(message_id: int) -> asyncpg.Record | None:
    return await get_pool().fetchrow("SELECT * FROM giveaways WHERE message_id = $1", message_id)

async def get_active_giveaways() -> list:
    return await get_pool().fetch("SELECT * FROM giveaways WHERE status = 'active'")

async def get_guild_giveaways(guild_id: int) -> list:
    return await get_pool().fetch("SELECT * FROM giveaways WHERE guild_id = $1 ORDER BY end_time DESC", guild_id)

async def update_giveaway(message_id: int, **kwargs) -> None:
    if not kwargs:
        return
    cols = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(kwargs))
    await get_pool().execute(
        f"UPDATE giveaways SET {cols} WHERE message_id = $1",
        message_id, *kwargs.values()
    )

async def add_giveaway_participant(message_id: int, user_id: int) -> None:
    await get_pool().execute(
        "UPDATE giveaways SET participants = array_append(COALESCE(participants, ARRAY[]::BIGINT[]), $2) WHERE message_id = $1 AND NOT ($2 = ANY(COALESCE(participants, ARRAY[]::BIGINT[])))",
        message_id, user_id
    )

async def remove_giveaway_participant(message_id: int, user_id: int) -> None:
    await get_pool().execute(
        "UPDATE giveaways SET participants = array_remove(COALESCE(participants, ARRAY[]::BIGINT[]), $2) WHERE message_id = $1",
        message_id, user_id
    )

