import discord
from discord.ext import commands
import requests
import json
import os
import re

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

WATCHLIST_FILE = os.path.join(os.path.dirname(__file__), 'watchlist.json')
BASE_API_URL = "http://localhost:8000"

def load_watchlist():
    if not os.path.exists(WATCHLIST_FILE):
        return {}
    with open(WATCHLIST_FILE, "r") as f:
        return json.load(f)

def save_watchlist(watchlist):
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(watchlist, f, indent=2)

def is_valid_crn(crn):
    return re.fullmatch(r"\d{5}", crn) is not None

def validate_term(term):
    term_map = {
        "Fall 2025": "202610",
        "Spring 2026": "202620"
    }
    return term_map.get(term) or term if term.isdigit() else None

def check_crn_exists(crn, term_code):
    try:
        url = f"{BASE_API_URL}/check_seats?crn={crn}&term={term_code}"
        resp = requests.get(url, timeout=5)
        data = resp.json()
        return 'error' not in data and 'Remaining' in data
    except:
        return False

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

# ───── !watch (by CRN) ──────────────────────────────────────────
@bot.command()
async def watch(ctx, crn: str, term: str):
    crn = crn.strip()
    term_code = validate_term(term)

    if not is_valid_crn(crn):
        await ctx.send("❌ CRN must be a 5-digit number.")
        return
    if not term_code:
        await ctx.send("❌ Invalid term. Use `Fall 2025`, `Spring 2026`, or `202610`.")
        return
    if not check_crn_exists(crn, term_code):
        await ctx.send(f"❌ CRN `{crn}` does not exist or has no available section.")
        return

    user_id = str(ctx.author.id)
    watchlist = load_watchlist()
    if user_id not in watchlist:
        watchlist[user_id] = []

    entry = {"crn": crn, "term": term_code}
    if entry in watchlist[user_id]:
        await ctx.send("⚠️ You're already watching this course.")
        return

    watchlist[user_id].append(entry)
    save_watchlist(watchlist)
    await ctx.send(f"👀 You're now watching CRN `{crn}` for term `{term_code}`.")

@watch.error
async def watch_error(ctx, error):
    await ctx.send("❌ Usage: `!watch <crn> <term>`\nExample: `!watch 12384 202610`")

# ───── !unwatch (by CRN) ────────────────────────────────────────
@bot.command()
async def unwatch(ctx, crn: str, term: str):
    crn = crn.strip()
    term_code = validate_term(term)

    if not is_valid_crn(crn):
        await ctx.send("❌ Invalid CRN format.")
        return
    if not term_code:
        await ctx.send("❌ Invalid term code.")
        return

    user_id = str(ctx.author.id)
    watchlist = load_watchlist()
    if user_id not in watchlist:
        await ctx.send("ℹ️ You’re not watching any courses.")
        return

    before = len(watchlist[user_id])
    watchlist[user_id] = [entry for entry in watchlist[user_id] if not (entry['crn'] == crn and entry['term'] == term_code)]
    after = len(watchlist[user_id])
    save_watchlist(watchlist)

    if before == after:
        await ctx.send("ℹ️ That CRN wasn't in your watchlist.")
    else:
        await ctx.send(f"✅ Stopped watching CRN `{crn}` for term `{term_code}`.")

@unwatch.error
async def unwatch_error(ctx, error):
    await ctx.send("❌ Usage: `!unwatch <crn> <term>`\nExample: `!unwatch 12384 202610`")

# ───── !check (by CRN) ───────────────────────────────────────────
@bot.command()
async def check(ctx, crn: str, term: str):
    crn = crn.strip()
    term_code = validate_term(term)

    if not is_valid_crn(crn):
        await ctx.send("❌ CRN must be a 5-digit number.")
        return
    if not term_code:
        await ctx.send("❌ Invalid term. Use something like `Fall 2025` or `202610`.")
        return

    try:
        url = f"{BASE_API_URL}/check_seats?crn={crn}&term={term_code}"
        response = requests.get(url, timeout=5)
        result = response.json()
        if 'error' in result or 'Remaining' not in result:
            await ctx.send(f"❌ CRN `{crn}` does not exist or isn't available.")
            return

        title = result['CourseTitle'].split(" - ")[0].strip()
        remaining = result['Remaining']
        await ctx.send(f"📊 **{title}** (CRN `{crn}` — Term `{term_code}`): **{remaining}** seats remaining.")

    except Exception:
        await ctx.send("⚠️ Error checking seat availability.")

@check.error
async def check_error(ctx, error):
    await ctx.send("❌ Usage: `!check <crn> <term>`\nExample: `!check 12384 202610`")

# ───── !list ─────────────────────────────────────────────────────
@bot.command()
async def list(ctx):
    user_id = str(ctx.author.id)

    if not os.path.exists(WATCHLIST_FILE):
        await ctx.send("🗒️ You're not watching any courses.")
        return

    with open(WATCHLIST_FILE, 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            await ctx.send("⚠️ Error reading your watchlist.")
            return

    if user_id not in data or len(data[user_id]) == 0:
        await ctx.send("🗒️ You're not watching any courses.")
        return

    msg = f"📋 Courses you're watching:\n"
    for entry in data[user_id]:
        crn = entry.get("crn")
        term = entry.get("term")

        if not is_valid_crn(crn):
            continue

        try:
            response = requests.get(f"{BASE_API_URL}/check_seats?crn={crn}&term={term}", timeout=5)
            result = response.json()
            if 'error' in result or 'Remaining' not in result:
                continue
            remaining = result['Remaining']
            title = result['CourseTitle'].split(" - ")[0].strip()
            msg += f"• **{title}** — CRN `{crn}`, Seats Remaining: **{remaining}**\n"
        except:
            continue

    await ctx.send(msg)

# ───── START BOT ─────────────────────────────────────────────────
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
