import asyncio
import logging
import discord
from discord.ext import commands
import config
from database.db import create_pool, close_pool
import os
import sys
import atexit
import time


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("bot")

# Prevent multiple instances on Windows/Linux by locking a file
lock_file_handle = None

def acquire_lock():
    global lock_file_handle
    lock_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.lock")
    if os.path.exists(lock_path):
        try:
            os.remove(lock_path)
        except OSError:
            log.critical("❌ Another instance of the bot is already running (bot.lock is active). Exiting.")
            sys.exit(1)
            
    try:
        lock_file_handle = open(lock_path, "w")
        lock_file_handle.write(str(os.getpid()))
        lock_file_handle.flush()
    except OSError as e:
        log.critical(f"❌ Failed to acquire bot.lock: {e}. Exiting.")
        sys.exit(1)

def release_lock():
    global lock_file_handle
    if lock_file_handle:
        try:
            lock_file_handle.close()
        except OSError:
            pass
        lock_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.lock")
        try:
            if os.path.exists(lock_path):
                os.remove(lock_path)
        except OSError:
            pass

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


class AdaptBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=self._get_prefix,
            intents=intents,
            help_command=None,
            owner_ids=set(config.OWNER_IDS),
        )
        self.start_time = time.time()


    async def _get_prefix(self, bot, message: discord.Message):
        if not message.guild:
            return config.PREFIX
        from database.db import get_prefix
        return await get_prefix(message.guild.id)

    async def setup_hook(self):
        if config.DATABASE_URL:
            self.db_pool = await create_pool()
        else:
            log.warning("⚠️  DATABASE_URL not set — running without database")
            self.db_pool = None
        await self._load_cogs()
        await self._sync_commands()

    async def _load_cogs(self):
        cogs = [
            ("cogs.general",     True),
            ("cogs.utility",     config.ENABLE_UTILITY),
            ("cogs.settings",    config.ENABLE_SETTINGS),
            ("cogs.moderation",  config.ENABLE_MODERATION),
            ("cogs.welcome",     config.ENABLE_WELCOME),
            ("cogs.logging",     config.ENABLE_LOGGING),
            ("cogs.leveling",    config.ENABLE_LEVELING),
            ("cogs.economy",     config.ENABLE_ECONOMY),
            ("cogs.tickets",     config.ENABLE_TICKETS),
            ("cogs.automod",     config.ENABLE_AUTOMOD),
            ("cogs.roles",       config.ENABLE_ROLES),
            ("cogs.customcmds",  config.ENABLE_CUSTOMCMDS),
            ("cogs.developer",   config.ENABLE_DEVELOPER),
            ("cogs.games",       True),
            ("cogs.giveaway",    config.ENABLE_GIVEAWAY),
        ]
        for cog, enabled in cogs:
            if not enabled:
                continue
            try:
                await self.load_extension(cog)
                log.info(f"✅  Loaded: {cog}")
            except Exception as e:
                log.error(f"❌  Failed to load {cog}: {e}")

    async def _sync_commands(self):
        if config.GUILD_ID:
            guild = discord.Object(id=config.GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info(f"⚡  Commands synced to guild {config.GUILD_ID}")
        else:
            await self.tree.sync()
            log.info("🌐  Commands synced globally")

    async def on_ready(self):
        log.info(f"🤖  Logged in as {self.user} (ID: {self.user.id})")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.guilds)} servers | /help",
            )
        )

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandNotFound):
            return
        log.error(f"Command error in {ctx.command}: {error}")

    async def close(self):
        await close_pool()
        await super().close()


def start_health_check(bot):
    import threading
    import json
    import platform
    import psutil
    from http.server import SimpleHTTPRequestHandler
    from socketserver import TCPServer
    from utils.dashboard_template import DASHBOARD_HTML

    class DashboardHandler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/dashboard" or self.path == "/":
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(DASHBOARD_HTML.encode("utf-8"))
            elif self.path == "/api/stats":
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                
                # Uptime calculation
                uptime = time.time() - bot.start_time
                
                # Database check
                db_connected = False
                if hasattr(bot, "db_pool") and bot.db_pool is not None:
                    # check pool status
                    db_connected = not bot.db_pool.is_closed() if hasattr(bot.db_pool, "is_closed") else True

                # Cogs loading status
                cogs_status = {}
                all_cogs = [
                    "cogs.general", "cogs.utility", "cogs.settings", 
                    "cogs.moderation", "cogs.welcome", "cogs.logging", 
                    "cogs.leveling", "cogs.economy", "cogs.tickets", 
                    "cogs.automod", "cogs.roles", "cogs.customcmds", 
                    "cogs.developer", "cogs.games", "cogs.giveaway"
                ]
                for cog in all_cogs:
                    cogs_status[cog] = cog in bot.extensions

                # Memory usage
                process = psutil.Process(os.getpid())
                mem_rss = process.memory_info().rss / (1024 * 1024) # MB
                mem_percent = psutil.virtual_memory().percent

                stats = {
                    "bot_name": bot.user.name if bot.user else "Adapt Bot",
                    "latency_ms": bot.latency * 1000 if bot.latency is not None else 0,
                    "server_count": len(bot.guilds),
                    "member_count": sum(g.member_count for g in bot.guilds if g.member_count),
                    "uptime_seconds": uptime,
                    "database_connected": db_connected,
                    "cpu_usage_percent": psutil.cpu_percent(),
                    "memory_usage_percent": round(mem_percent, 1),
                    "memory_usage_mb": round(mem_rss, 1),
                    "pid": os.getpid(),
                    "python_version": platform.python_version(),
                    "os": platform.system() + " " + platform.release(),
                    "cogs": cogs_status
                }
                
                self.wfile.write(json.dumps(stats).encode("utf-8"))
            else:
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"OK")

        def log_message(self, format, *args):
            return

    port = int(os.environ.get("PORT", 8080))
    try:
        server = TCPServer(("0.0.0.0", port), DashboardHandler, bind_and_activate=False)
        server.allow_reuse_address = True
        server.server_bind()
        server.server_activate()
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        log.info(f"⚡ Started health check & dashboard server on port {port}")
    except Exception as e:
        log.error(f"❌ Failed to start dashboard server: {e}")


async def main():
    if not config.TOKEN:
        log.critical("DISCORD_TOKEN is not set.")
        return
    async with AdaptBot() as bot:
        start_health_check(bot)
        await bot.start(config.TOKEN)


if __name__ == "__main__":
    acquire_lock()
    atexit.register(release_lock)
    asyncio.run(main())

