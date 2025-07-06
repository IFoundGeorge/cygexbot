import re
import json
import os
import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta
import time

# --- Role check decorators ---
def is_admin_or_trial_mod():
    async def predicate(ctx):
        if ctx.author.guild_permissions.administrator:
            return True
        trial_mod_role = discord.utils.get(ctx.guild.roles, name="Trial Mod of Nikoh")  # updated
        if trial_mod_role and trial_mod_role in ctx.author.roles:
            return True
        await ctx.send("❌ You don't have permission to use this command.", delete_after=5)
        return False
    return commands.check(predicate)

def is_admin_or_trial_mod_appcmd():
    async def predicate(interaction: discord.Interaction):
        if interaction.user.guild_permissions.administrator:
            return True
        trial_mod_role = discord.utils.get(interaction.guild.roles, name="Trial Mod of Nikoh")  # updated
        if trial_mod_role and trial_mod_role in interaction.user.roles:
            return True
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return False
    return app_commands.check(predicate)

# 🔐 Bot token
TOKEN = "Insert Token Here"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

log_channel = None

def load_patterns_from_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []

def save_patterns_to_json(patterns, path):
    with open(path, "w") as f:
        json.dump(patterns, f, indent=4)

profanity_patterns = load_patterns_from_json("profanity.json")
extra_patterns = load_patterns_from_json("extra_patterns.json")

# 🚨 Warning system
warning_data_path = "user_warnings.json"

def load_warnings():
    if os.path.exists(warning_data_path):
        with open(warning_data_path, "r") as f:
            return json.load(f)
    return {}

def save_warnings(data):
    with open(warning_data_path, "w") as f:
        json.dump(data, f, indent=4)

user_warnings = load_warnings()

# ✅ Dismiss Button View
class DismissView(discord.ui.View):
    def __init__(self, author: discord.User):
        super().__init__(timeout=60)
        self.author = author

    @discord.ui.button(label="Dismiss", style=discord.ButtonStyle.secondary)
    async def dismiss(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ You can't dismiss this message.", ephemeral=True)
            return
        await interaction.message.delete()

@bot.event
async def on_ready():
    synced = await tree.sync()
    print(f"✅ Logged in as {bot.user.name}")
    print(f"✅ Slash commands synced globally: {len(synced)} commands")

@bot.event
async def on_message(message):
    global log_channel

    if message.author == bot.user or not message.guild:
        return

    all_patterns = profanity_patterns + extra_patterns
    matched_pattern = None

    for pattern_text in all_patterns:
        pattern = re.compile(pattern_text, re.IGNORECASE)
        if pattern.search(message.content):
            matched_pattern = pattern.pattern
            break

    if matched_pattern:
        try:
            await message.delete()
            view = DismissView(message.author)
            await message.channel.send(
                f"⚠️ {message.author.mention}, please avoid using offensive language.",
                view=view
            )
        except discord.Forbidden:
            print("❌ Missing permission to delete message.")
        except discord.HTTPException as e:
            print(f"❌ Error deleting message: {e}")

        user_id = str(message.author.id)
        if user_id not in user_warnings:
            user_warnings[user_id] = {"warnings": 0, "timeout_stage": 0}

        user_warnings[user_id]["warnings"] += 1
        warning_count = user_warnings[user_id]["warnings"]
        save_warnings(user_warnings)

        if log_channel:
            embed = discord.Embed(
                title="🚨 Profanity Detected and Message Deleted",
                description=f"`{message.content}`",
                color=discord.Color.red()
            )
            embed.set_author(name=message.author.name, icon_url=message.author.display_avatar.url)
            embed.add_field(name="Matched Pattern", value=f"`{matched_pattern}`", inline=False)
            embed.add_field(name="Channel", value=message.channel.mention, inline=True)
            embed.add_field(name="User", value=message.author.mention, inline=True)
            embed.add_field(name="Warnings", value=str(warning_count), inline=True)
            embed.set_footer(text=f"User ID: {message.author.id}")
            await log_channel.send(embed=embed)

    await bot.process_commands(message)

@tree.command(name="regexlist", description="List all current regex patterns.")
@is_admin_or_trial_mod_appcmd()
async def regexlist(interaction: discord.Interaction):
    all_patterns = profanity_patterns + extra_patterns

    if not all_patterns:
        await interaction.response.send_message("❌ No regex patterns found.", ephemeral=True)
        return

    chunk_size = 10
    chunks = [all_patterns[i:i+chunk_size] for i in range(0, len(all_patterns), chunk_size)]

    embeds = []
    for i, chunk in enumerate(chunks):
        embed = discord.Embed(
            title=f"📜 Regex Pattern List (Page {i+1}/{len(chunks)})",
            description="\n".join(f"`{p}`" for p in chunk),
            color=discord.Color.blurple()
        )
        embeds.append(embed)

    if len(embeds) == 1:
        await interaction.response.send_message(embed=embeds[0], ephemeral=True)
    else:
        await interaction.response.send_message("📁 Multiple regex pages found:", ephemeral=True)
        for embed in embeds:
            await interaction.followup.send(embed=embed, ephemeral=True)

@tree.command(name="regexlog", description="Set the log channel for regex matches.")
@app_commands.describe(channel="Channel to log matches in")
@is_admin_or_trial_mod_appcmd()
async def regexlog(interaction: discord.Interaction, channel: discord.TextChannel):
    global log_channel
    log_channel = channel
    await interaction.response.send_message(f"✅ Regex log channel set to {channel.mention}", ephemeral=True)

@tree.command(name="regexadd", description="Add a new regex pattern to scan for.")
@app_commands.describe(pattern="The regex expression to add")
@is_admin_or_trial_mod_appcmd()
async def regexadd(interaction: discord.Interaction, pattern: str):
    try:
        re.compile(pattern)
        extra_patterns.append(pattern)
        save_patterns_to_json(extra_patterns, "extra_patterns.json")
        await interaction.response.send_message(f"✅ Pattern added: `{pattern}`", ephemeral=True)
    except re.error:
        await interaction.response.send_message("❌ Invalid regex pattern.", ephemeral=True)

@bot.command()
async def test(ctx):
    await ctx.send("Bot is working!")

@tree.command(name="warn", description="Warn a user for a reason.")
@app_commands.describe(user="The user to warn", reason="Reason for the warning")
@is_admin_or_trial_mod_appcmd()
async def warn(interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
    user_id = str(user.id)
    if user_id not in user_warnings:
        user_warnings[user_id] = {"warnings": 0, "timeout_stage": 0}
    user_warnings[user_id]["warnings"] += 1
    save_warnings(user_warnings)

    embed = discord.Embed(
        title="⚠️ User Warned",
        description=f"{user.mention} has been warned.",
        color=discord.Color.orange()
    )
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Total Warnings", value=str(user_warnings[user_id]["warnings"]), inline=True)
    embed.set_footer(text=f"Warned by {interaction.user}", icon_url=interaction.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

    try:
        await user.send(f"You have been warned in **{interaction.guild.name}** for: {reason}")
    except discord.Forbidden:
        pass  # User has DMs closed

@tree.command(name="whois", description="Show detailed info about a user.")
@app_commands.describe(user="The user to get info on (leave blank for yourself)")
@is_admin_or_trial_mod_appcmd()
async def whois(interaction: discord.Interaction, user: discord.Member = None):
    user = user or interaction.user
    embed = discord.Embed(
        title=f"Whois: {user}",
        color=user.color if hasattr(user, "color") else discord.Color.blurple(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="ID", value=user.id, inline=True)
    embed.add_field(name="Display Name", value=user.display_name, inline=True)
    embed.add_field(name="Account Created", value=user.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
    embed.add_field(name="Joined Server", value=user.joined_at.strftime("%Y-%m-%d %H:%M:%S") if user.joined_at else "Unknown", inline=False)
    embed.add_field(
        name="Roles",
        value=", ".join([role.mention for role in user.roles if role != interaction.guild.default_role]) or "None",
        inline=False
    )
    embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You don't have permission to use this command.", delete_after=5)
    else:
        raise error  # Re-raise other errors so you still see tracebacks for bugs

STAFF_FOLDER = "staff"  # Folder where your images are stored

class StaffEmbedView(discord.ui.View):
    def __init__(self, current_role="main"):
        super().__init__(timeout=None)
        self.current_role = current_role
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        if self.current_role == "main":
            button_labels = [
                ("owner", "Owner"),
                ("co-owner", "Co Owner"),
                ("admin", "Admin"),
                ("techsupport", "Tech Support"),
                ("moddirector", "Mod Director"),
                ("gamedirector", "Game Director"),
                ("eventdirector", "Event Director"),
            ]
            for key, label in button_labels:
                self.add_item(RoleButton(key, label))
        else:
            self.add_item(BackButton())

    def get_embed(self):
        embed = discord.Embed(
            title="LEADERS OF NIKOH" if self.current_role == "main" else self.current_role.replace("-", " ").title(),
            color=discord.Color.blurple()
        )
        embed.set_image(url=ROLE_IMAGES[self.current_role])
        if self.current_role != "main":
            embed.add_field(name="Role", value=self.current_role.replace("-", " ").title(), inline=False)
        return embed

class RoleButton(discord.ui.Button):
    def __init__(self, role, label):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.role = role

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=self.role.replace("-", " ").title(),
            color=discord.Color.blurple()
        )
        embed.set_image(url=ROLE_IMAGES[self.role])
        embed.add_field(name="Role", value=self.role.replace("-", " ").title(), inline=False)
        await interaction.response.send_message(embed=embed, view=discord.ui.View().add_item(EphemeralBackButton()), ephemeral=True)

class EphemeralBackButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Back", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()  # Acknowledge the button click
        await interaction.delete_original_response()  # Delete the ephemeral message

class EphemeralMainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        # Add your role buttons here if you want more navigation

@tree.command(name="embedstaff", description="Show interactive staff embed in a specific channel.")
@app_commands.describe(channel="The channel to send the staff embed in")
async def embedstaff(interaction: discord.Interaction, channel: discord.TextChannel):
    view = StaffEmbedView()
    await channel.send(embed=view.get_embed(), view=view)
    await interaction.response.send_message(
        f"✅ Staff embed sent to {channel.mention}. Anyone can use the buttons and see info privately.",
        ephemeral=True
    )

ROLE_IMAGES = {
    "main": "https://imgur.com/naXgUAt.png",
    "owner": "https://imgur.com/U1EAovf.png",
    "co-owner": "https://imgur.com/t3YLXqQ.png",
    "admin": "https://imgur.com/jsgJBLe.png",
    "techsupport": "https://imgur.com/i2Rv9pi.png",
    "moddirector": "https://imgur.com/8w575Zj.png",
    "gamedirector": "https://imgur.com/VBB8OLq.png",
    "eventdirector": "https://imgur.com/ItHTpl0.png"
}

bot.run(TOKEN)
