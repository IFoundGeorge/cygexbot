import re
import json
import os
import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta, datetime
import asyncio
import random

# Load custom profanity patterns from profanity.json
def load_custom_patterns():
    try:
        print("🔍 Loading profanity patterns from profanity.json...")
        with open('profanity.json', 'r') as f:
            patterns = json.load(f)
        
        print(f"📝 Found {len(patterns)} patterns in JSON")
        compiled_patterns = []
        for i, pattern in enumerate(patterns):
            try:
                # Handle different pattern types
                if '\\*' in pattern:
                    # Handle asterisk patterns (already escaped in JSON)
                    regex_pattern = r'\b' + pattern + r'\b'
                elif pattern.startswith('\\b') and pattern.endswith('\\b'):
                    # Handle pre-formatted regex patterns with word boundaries
                    regex_pattern = pattern
                else:
                    # Handle regular word patterns
                    regex_pattern = r'\b' + re.escape(pattern) + r'\b'
                compiled_patterns.append(re.compile(regex_pattern, re.IGNORECASE))
                print(f"✅ Compiled pattern {i+1}: {pattern} -> {regex_pattern}")
            except re.error as e:
                print(f"⚠️ Invalid regex pattern '{pattern}': {e}")
                continue
        
        return compiled_patterns
    except FileNotFoundError:
        print("⚠️ profanity.json not found. No profanity patterns loaded.")
        return []
    except json.JSONDecodeError as e:
        print(f"⚠️ Error parsing profanity.json: {e}")
        return []
    except Exception as e:
        print(f"⚠️ Unexpected error loading patterns: {e}")
        return []

custom_patterns = load_custom_patterns()
print(f"🔍 Loaded {len(custom_patterns)} profanity patterns")

# Initialize profanity checker using only custom regex patterns
def is_profane(text):
    """Check if text contains profanity using custom regex patterns from profanity.json"""
    try:
        # Check with custom regex patterns
        for i, pattern in enumerate(custom_patterns):
            if pattern.search(text):
                print(f"🚫 Pattern {i+1} matched: {pattern.pattern}")
                # Check if it's just the exempted words
                if is_exempted_content(text):
                    print(f"✅ Content exempted: {text}")
                    return False
                return True
                
        return False
    except Exception as e:
        print(f"⚠️ Error checking profanity patterns: {e}")
        return False

def is_exempted_content(text):
    """Check if the text only contains exempted words (s word and d word)"""
    # Convert to lowercase for comparison
    text_lower = text.lower()
    
    # Define exempted words and their variations
    exempted_words = [
        'shit', 'sh*t', 'sh!t', 's***', 's**t', 's***t',
        'damn', 'd*mn', 'd*mn', 'd***', 'd**n', 'd***n'
    ]
    
    # Check if the text contains only exempted words
    for word in exempted_words:
        if word in text_lower:
            # If it's just the exempted word or with common punctuation, allow it
            import re
            # Remove common punctuation and check if it's just the exempted word
            cleaned_text = re.sub(r'[^\w\s]', '', text_lower).strip()
            if cleaned_text == word.replace('*', '').replace('!', ''):
                return True
    
    return False

def has_exempted_role(member):
    """Check if a member has any of the exempted roles"""
    exempted_roles = [
        "Senior Host Of Nikoh",
        "Moderator Of Nikoh", 
        "Technical Support",
        "Game Director",
        "Mod Director"
    ]
    
    # Only check roles if the object is a Member (not a User)
    if hasattr(member, "roles"):
        # Check for specific exempted roles only
        exempted_role_names = [role.name for role in member.roles if role.name in exempted_roles]
        return bool(exempted_role_names)
    return False

def is_test_command_allowed(ctx):
    """Check if command is allowed based on test mode"""
    global test_mode_active, test_restricted_mode, test_channel_id
    
    # If test mode is not active, allow all commands
    if not test_mode_active:
        return True
    
    # If in global mode, allow all commands
    if not test_restricted_mode:
        return True
    
    # If in restricted mode, only allow in test channel
    return str(ctx.channel.id) == test_channel_id

def save_json(data, path):
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)

# Role checker
def is_admin_or_trial_mod():
    async def predicate(ctx):
        if ctx.author.guild_permissions.administrator:
            return True
        trial_mod_role = discord.utils.get(ctx.guild.roles, name="Trial Mod of Nikoh")
        host_role = discord.utils.get(ctx.guild.roles, name="Host Of Nikoh")
        mod_role = discord.utils.get(ctx.guild.roles, name="Moderator Of Nikoh")
        if (trial_mod_role and trial_mod_role in ctx.author.roles) or (host_role and host_role in ctx.author.roles) or (mod_role and mod_role in ctx.author.roles):
            return True
        await ctx.send("❌ You don't have permission to use this command.", delete_after=5)
        return False
    return commands.check(predicate)

# Hardcoded bot token for local testing
TOKEN = os.environ.get("MY_SECRET_TOKEN")

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

# If there was a karaoke command loaded from an extension or earlier import, drop it.
bot.remove_command("karaoke")
bot.remove_command("karaoke_queue")
bot.remove_command("karaoke_queue_end")
bot.remove_command("karaoke_leave")
bot.remove_command("karaoke_remove")

karaoke_queue = []
karaoke_closed = False

# Test mode variables
test_mode_active = False
test_restricted_mode = True  # True = only specific channel, False = all channels
test_channel_id = "1387308205905936394"

# Channel IDs
CARL_LOG_CHANNEL = 1147510748663250954
RYNO_LOG_CHANNEL = 1388161864709701682  # Using server log as main
CONFESSION_LOG_CHANNEL = 1400898728428175400

class LogView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.current_page = 0
        self.current_log_type = None
        self.messages = []
    
    @discord.ui.button(label="Carl", style=discord.ButtonStyle.primary)
    async def carl_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_logs(interaction, "Carl", CARL_LOG_CHANNEL)
    
    @discord.ui.button(label="Ryno", style=discord.ButtonStyle.primary)
    async def ryno_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_logs(interaction, "Ryno", RYNO_LOG_CHANNEL)
    
    @discord.ui.button(label="Confession Logs", style=discord.ButtonStyle.primary)
    async def confession_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_logs(interaction, "Confession", CONFESSION_LOG_CHANNEL)
    
    async def show_logs(self, interaction: discord.Interaction, log_type: str, channel_id: int):
        channel = interaction.guild.get_channel(channel_id)
        if not channel:
            await interaction.response.send_message("Channel not found!", ephemeral=True)
            return
        
        # Fetch last 50 messages (we'll paginate through them)
        messages = []
        async for message in channel.history(limit=50):
            messages.append(message)
        
        self.messages = messages
        self.current_page = 0
        self.current_log_type = log_type
        
        await self.display_page(interaction)
    
    async def display_page(self, interaction: discord.Interaction):
        if not self.messages:
            await interaction.response.send_message("No messages found!", ephemeral=True)
            return
        
        start_idx = self.current_page * 10
        end_idx = min(start_idx + 10, len(self.messages))
        page_messages = self.messages[start_idx:end_idx]
        
        embed = discord.Embed(
            title=f"{self.current_log_type} Logs",
            description="",
            color=discord.Color.blue()
        )
        
        for i, message in enumerate(page_messages, start=start_idx + 1):
            embed.add_field(
                name=f"Message {i}",
                value=f"{message.content[:100]}{'...' if len(message.content) > 100 else ''}",
                inline=False
            )
        
        embed.set_footer(text=f"Page {self.current_page + 1} • Messages {start_idx + 1}-{end_idx} of {len(self.messages)}")
        
        # Create navigation view
        nav_view = LogNavigationView(self)
        
        await interaction.response.edit_message(embed=embed, view=nav_view)

class LogNavigationView(discord.ui.View):
    def __init__(self, log_view: LogView):
        super().__init__(timeout=None)
        self.log_view = log_view
    
    @discord.ui.button(label="◀️ Back", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Return to main menu
        main_embed = discord.Embed(
            title="Cygex Log",
            description="This log is specifically for the Nikoh server.\n\nAll important actions and updates will appear here.",
            color=discord.Color.blue()
        )
        main_view = LogView()
        await interaction.response.edit_message(embed=main_embed, view=main_view)
    
    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.log_view.current_page > 0:
            self.log_view.current_page -= 1
            await self.log_view.display_page(interaction)
        else:
            await interaction.response.send_message("You're already on the first page!", ephemeral=True)
    
    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        max_pages = (len(self.log_view.messages) - 1) // 10
        if self.log_view.current_page < max_pages:
            self.log_view.current_page += 1
            await self.log_view.display_page(interaction)
        else:
            await interaction.response.send_message("You're already on the last page!", ephemeral=True)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    user_id = 768301523972522004
    user = await bot.fetch_user(user_id)
    if user:
        # Fetch or create the DM channel
        dm_channel = await user.create_dm()
        # Delete all messages in the DM channel sent by the bot
        try:
            async for message in dm_channel.history(limit=100):
                if message.author == bot.user:
                    await message.delete()
        except Exception as e:
            print(f"Failed to delete previous messages: {e}")

        # Send the interactive embed with image
        embed = discord.Embed(
            title="Cygex Log",
            description="This log is specifically for the Nikoh server.\n\nAll important actions and updates will appear here.",
            color=discord.Color.blue()
        )
        file = discord.File("img/main.png", filename="main.png")
        embed.set_image(url="attachment://main.png")

        view = LogView()

        try:
            await user.send(embed=embed, view=view, file=file)
            print(f"Sent test embed with image to {user_id}")
        except Exception as e:
            print(f"Failed to send embed: {e}")
    else:
        print(f"User {user_id} not found.")

@bot.event
async def on_message(message):
    if message.author == bot.user or not message.guild:
        return

    # Debug: Print message info
    print(f"📝 Message from {message.author.name}: {message.content[:50]}...")

    # Only check for exempted roles if message.author has 'roles' (i.e., is a Member)
    if hasattr(message.author, 'roles'):
        if has_exempted_role(message.author):
            print(f"🛡️ {message.author.name} has exempted role - skipping profanity filter")
            await bot.process_commands(message)
            return

    # Profanity filter
    if message.content:
        print(f"🔍 Checking content: {message.content}")
        
        if is_profane(message.content):
            print(f"🚫 Profanity detected in message from {message.author.name}")
            try:
                await message.delete()
                warning_msg = await message.channel.send(
                    f"⚠️ {message.author.mention}, please keep the chat family-friendly! Your message was removed.",
                    delete_after=10
                )
                print(f"🚫 Profanity detected from {message.author.name} ({message.author.id}) in {message.guild.name} - Channel: {message.channel.name}")
                return
            except discord.Forbidden:
                print(f"❌ Cannot delete message from {message.author.name} - missing permissions")
            except discord.NotFound:
                print(f"❌ Message from {message.author.name} already deleted")
        else:
            print("✅ No profanity detected")

    await bot.process_commands(message)

@bot.command(name="k")
async def karaoke(ctx, *, arg=None):
    # Check test mode restrictions
    if not is_test_command_allowed(ctx):
        if test_mode_active and test_restricted_mode:
            await ctx.send(f"❌ Test mode is **RESTRICTED**. Commands only work in <#{test_channel_id}>!", delete_after=5)
        return
    
    # Check if command is used in karaoke voice channel
    karaoke_channels = ["1388174386523275284", "1386156487310835722"]
    if str(ctx.channel.id) not in karaoke_channels:
        await ctx.send("❌ Karaoke commands can only be used in the karaoke voice channels!", delete_after=5)
        return
    
    if arg and arg.lower() == "help":
        embed = discord.Embed(
            title="🎤 Karaoke Commands",
            description="Here are all the available karaoke commands:",
            color=discord.Color.magenta()
        )
        embed.add_field(
            name="!k",
            value="Join the karaoke queue",
            inline=False
        )
        embed.add_field(
            name="!k add @user",
            value="Add a user to the queue (Authorized users only)",
            inline=False
        )
        embed.add_field(
            name="!kl",
            value="Leave the karaoke queue",
            inline=False
        )
        embed.add_field(
            name="!kr @user",
            value="Remove a user from the queue (Moderator only)",
            inline=False
        )
        embed.add_field(
            name="!kq",
            value="View the current karaoke queue",
            inline=False
        )
        embed.add_field(
            name="!kn",
            value="Move to next person (Moderator only)",
            inline=False
        )
        embed.add_field(
            name="!kqe",
            value="Clear the entire queue (Moderator only)",
            inline=False
        )
        embed.add_field(
            name="!kc",
            value="Close karaoke (Moderator only)",
            inline=False
        )
        embed.add_field(
            name="!ko",
            value="Open karaoke (Moderator only)",
            inline=False
        )
        embed.set_footer(text="Moderator roles: Trial Mod of Nikoh, Host Of Nikoh, Moderator Of Nikoh")
        await ctx.send(embed=embed)
        return
    
    # Check if it's the add command
    if arg and arg.lower().startswith("add "):
        # Check if user is authorized to use add command
        authorized_users = ["1306577300304826369", "429920624131964928"]
        if str(ctx.author.id) not in authorized_users:
            await ctx.send("❌ You don't have permission to add users to the queue.", delete_after=5)
            return
        
        # Get the mentioned user
        if not ctx.message.mentions:
            await ctx.send("❌ Please mention a user to add to the queue. Usage: `!k add @user`")
            return
        
        target_user = ctx.message.mentions[0]
        target_user_id = str(target_user.id)
        
        if target_user_id in karaoke_queue:
            position = karaoke_queue.index(target_user_id) + 1
            await ctx.send(f"🎤 {target_user.mention} is already in the karaoke queue! Position: {position}")
        else:
            karaoke_queue.append(target_user_id)
            position = len(karaoke_queue)
            await ctx.send(f"✅ {target_user.mention} has been added to the karaoke queue by {ctx.author.mention}! Position: {position}")
        return
    
    # Check if karaoke is closed (except for add command which is handled above)
    if karaoke_closed:
        await ctx.send("🔒 Karaoke is currently CLOSED! Only authorized users can add people to the queue.", delete_after=5)
        return
    
    user_id = str(ctx.author.id)
    if user_id in karaoke_queue:
        position = karaoke_queue.index(user_id) + 1
        await ctx.send(f"🎤 {ctx.author.mention}, you're already in the karaoke queue! Position: {position}")
    else:
        karaoke_queue.append(user_id)
        position = len(karaoke_queue)
        await ctx.send(f"✅ {ctx.author.mention}, you've been added to the karaoke queue! Position: {position}")

@bot.command(name="kl")
async def karaoke_leave(ctx):
    # Check test mode restrictions
    if not is_test_command_allowed(ctx):
        if test_mode_active and test_restricted_mode:
            await ctx.send(f"❌ Test mode is **RESTRICTED**. Commands only work in <#{test_channel_id}>!", delete_after=5)
        return
    
    # Check if command is used in karaoke voice channel
    karaoke_channels = ["1388174386523275284", "1386156487310835722"]
    if str(ctx.channel.id) not in karaoke_channels:
        await ctx.send("❌ Karaoke commands can only be used in the karaoke voice channels!", delete_after=5)
        return
    
    user_id = str(ctx.author.id)
    if user_id in karaoke_queue:
        karaoke_queue.remove(user_id)
        await ctx.send(f"👋 {ctx.author.mention}, you have left the karaoke queue.")
    else:
        await ctx.send(f"❌ {ctx.author.mention}, you are not in the karaoke queue.")

@bot.command(name="kr")
@is_admin_or_trial_mod()
async def karaoke_remove(ctx, user: discord.Member = None):
    # Check test mode restrictions
    if not is_test_command_allowed(ctx):
        if test_mode_active and test_restricted_mode:
            await ctx.send(f"❌ Test mode is **RESTRICTED**. Commands only work in <#{test_channel_id}>!", delete_after=5)
        return
    
    # Check if command is used in karaoke voice channel
    karaoke_channels = ["1388174386523275284", "1386156487310835722"]
    if str(ctx.channel.id) not in karaoke_channels:
        await ctx.send("❌ Karaoke commands can only be used in the karaoke voice channels!", delete_after=5)
        return
    
    if not user:
        await ctx.send("❌ Please mention a user to remove. Usage: `!kr @user`")
        return
    
    user_id = str(user.id)
    if user_id in karaoke_queue:
        karaoke_queue.remove(user_id)
        await ctx.send(f"🗑️ {user.mention} has been removed from the karaoke queue by {ctx.author.mention}.")
    else:
        await ctx.send(f"❌ {user.mention} is not in the karaoke queue.")

@bot.command(name="kc")
@is_admin_or_trial_mod()
async def karaoke_close(ctx):
    global karaoke_closed
    # Check test mode restrictions
    if not is_test_command_allowed(ctx):
        if test_mode_active and test_restricted_mode:
            await ctx.send(f"❌ Test mode is **RESTRICTED**. Commands only work in <#{test_channel_id}>!", delete_after=5)
        return
    
    # Check if command is used in karaoke voice channel
    karaoke_channels = ["1388174386523275284", "1386156487310835722"]
    if str(ctx.channel.id) not in karaoke_channels:
        await ctx.send("❌ Karaoke commands can only be used in the karaoke voice channels!", delete_after=5)
        return
    
    karaoke_closed = True
    await ctx.send("🔒 Karaoke is now CLOSED! Only authorized users can add people to the queue.")

@bot.command(name="ko")
@is_admin_or_trial_mod()
async def karaoke_open(ctx):
    global karaoke_closed
    # Check test mode restrictions
    if not is_test_command_allowed(ctx):
        if test_mode_active and test_restricted_mode:
            await ctx.send(f"❌ Test mode is **RESTRICTED**. Commands only work in <#{test_channel_id}>!", delete_after=5)
        return
    
    # Check if command is used in karaoke voice channels
    karaoke_channels = ["1388174386523275284", "1386156487310835722"]
    if str(ctx.channel.id) not in karaoke_channels:
        await ctx.send("❌ Karaoke commands can only be used in the karaoke voice channels!", delete_after=5)
        return
    
    karaoke_closed = False
    await ctx.send("🎤 Karaoke is now OPEN! Users can join the queue again.")

@bot.command(name="kn")
@is_admin_or_trial_mod()
async def karaoke_next(ctx):
    # Check test mode restrictions
    if not is_test_command_allowed(ctx):
        if test_mode_active and test_restricted_mode:
            await ctx.send(f"❌ Test mode is **RESTRICTED**. Commands only work in <#{test_channel_id}>!", delete_after=5)
        return
    
    # Check if command is used in karaoke voice channel
    karaoke_channels = ["1388174386523275284", "1386156487310835722"]
    if str(ctx.channel.id) not in karaoke_channels:
        await ctx.send("❌ Karaoke commands can only be used in the karaoke voice channels!", delete_after=5)
        return
    
    if not karaoke_queue:
        await ctx.send("🎤 The karaoke queue is currently empty.")
        return
    
    # Remove the current person (first in queue)
    current_user_id = karaoke_queue.pop(0)
    
    try:
        current_member = await ctx.guild.fetch_member(int(current_user_id))
        current_name = current_member.display_name
    except (discord.NotFound, discord.HTTPException):
        current_name = f"User {current_user_id}"
    
    if karaoke_queue:
        try:
            next_member = await ctx.guild.fetch_member(int(karaoke_queue[0]))
            next_name = next_member.display_name
        except (discord.NotFound, discord.HTTPException):
            next_name = f"User {karaoke_queue[0]}"
        
        await ctx.send(f"🎤 {current_name} has finished! Next up: {next_member.mention}")
    else:
        await ctx.send(f"🎤 {current_name} has finished! The karaoke queue is now empty.")

@bot.command(name="kq")
async def karaoke_queue_cmd(ctx):
    # Check test mode restrictions
    if not is_test_command_allowed(ctx):
        if test_mode_active and test_restricted_mode:
            await ctx.send(f"❌ Test mode is **RESTRICTED**. Commands only work in <#{test_channel_id}>!", delete_after=5)
        return
    
    # Check if command is used in karaoke voice channel
    karaoke_channels = ["1388174386523275284", "1386156487310835722"]
    if str(ctx.channel.id) not in karaoke_channels:
        await ctx.send("❌ Karaoke commands can only be used in the karaoke voice channels!", delete_after=5)
        return
    
    if not karaoke_queue:
        await ctx.send("🎤 The karaoke queue is currently empty.")
        return
    lines = []
    for i, uid in enumerate(karaoke_queue, start=1):
        try:
            member = await ctx.guild.fetch_member(int(uid))
            name = member.display_name
        except discord.NotFound:
            name = f"User {uid} (left server)"
        except discord.HTTPException:
            name = f"User {uid} (error)"
        if i == 1:
            lines.append(f"Current: {name}")
        else:
            lines.append(f"{i}. {name}")
    embed = discord.Embed(
        title="🎤 Karaoke Queue",
        description="\n".join(lines),
        color=discord.Color.magenta()
    )
    await ctx.send(embed=embed)

@bot.command(name="kqe")
@is_admin_or_trial_mod()
async def karaoke_queue_end(ctx):
    # Check test mode restrictions
    if not is_test_command_allowed(ctx):
        if test_mode_active and test_restricted_mode:
            await ctx.send(f"❌ Test mode is **RESTRICTED**. Commands only work in <#{test_channel_id}>!", delete_after=5)
        return
    
    # Check if command is used in karaoke voice channel
    karaoke_channels = ["1388174386523275284", "1386156487310835722"]
    if str(ctx.channel.id) not in karaoke_channels:
        await ctx.send("❌ Karaoke commands can only be used in the karaoke voice channels!", delete_after=5)
        return
    
    global karaoke_queue
    if not karaoke_queue:
        await ctx.send("🎤 The karaoke queue is already empty.")
        return
    
    # Create confirmation embed
    embed = discord.Embed(
        title="⚠️ Confirm Queue Clear",
        description=f"Are you sure you want to clear the karaoke queue?\n\n**Current queue has {len(karaoke_queue)} people:**",
        color=discord.Color.red()
    )
    
    # Add current queue to embed
    queue_list = []
    for i, uid in enumerate(karaoke_queue[:5], start=1):  # Show first 5 people
        try:
            member = await ctx.guild.fetch_member(int(uid))
            name = member.display_name
        except (discord.NotFound, discord.HTTPException):
            name = f"User {uid}"
        queue_list.append(f"{i}. {name}")
    
    if len(karaoke_queue) > 5:
        queue_list.append(f"... and {len(karaoke_queue) - 5} more")
    
    embed.add_field(
        name="Queue Members",
        value="\n".join(queue_list) if queue_list else "Empty",
        inline=False
    )
    
    embed.add_field(
        name="Confirmation",
        value="React with ✅ to confirm or ❌ to cancel",
        inline=False
    )
    
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id
    
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)
        
        if str(reaction.emoji) == "✅":
            karaoke_queue.clear()
            await ctx.send("🛑 The karaoke queue has been cleared.")
        else:
            await ctx.send("❌ Queue clear cancelled.")
            
    except asyncio.TimeoutError:
        await ctx.send("⏰ Confirmation timed out. Queue was not cleared.")

@bot.command(name="test")
async def test_mode(ctx):
    """Toggle test mode for commands"""
    global test_mode_active, test_restricted_mode
    
    if not test_mode_active:
        # First activation - restricted mode
        test_mode_active = True
        test_restricted_mode = True
        embed = discord.Embed(
            title="🧪 Test Mode Activated",
            description="Test mode is now **RESTRICTED** to specific channel only.",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="Current Mode:",
            value="🟡 **RESTRICTED** - Commands only work in designated test channel",
            inline=False
        )
        embed.add_field(
            name="Test Channel:",
            value=f"<#{test_channel_id}>",
            inline=False
        )
        embed.add_field(
            name="Next Use:",
            value="Use `!test` again to enable **GLOBAL** mode (all channels)",
            inline=False
        )
        embed.set_footer(text="Test mode is now active")
    else:
        if test_restricted_mode:
            # Switch to global mode
            test_restricted_mode = False
            embed = discord.Embed(
                title="🌍 Test Mode - GLOBAL",
                description="Test mode is now **GLOBAL** - works in all channels!",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Current Mode:",
                value="🟢 **GLOBAL** - Commands work in all channels",
                inline=False
            )
            embed.add_field(
                name="Next Use:",
                value="Use `!test` again to **DEACTIVATE** test mode",
                inline=False
            )
        else:
            # Deactivate test mode
            test_mode_active = False
            test_restricted_mode = True
            embed = discord.Embed(
                title="❌ Test Mode Deactivated",
                description="Test mode has been **DEACTIVATED**.",
                color=discord.Color.red()
            )
            embed.add_field(
                name="Status:",
                value="🔴 **DEACTIVATED** - Normal operation restored",
                inline=False
            )
            embed.add_field(
                name="Next Use:",
                value="Use `!test` again to activate **RESTRICTED** mode",
                inline=False
            )
    
    await ctx.send(embed=embed)
    print(f"🧪 Test mode toggled by {ctx.author.name}: Active={test_mode_active}, Restricted={test_restricted_mode}")

@bot.command(name="testprofanity")
async def test_profanity(ctx):
    """Test command to check if profanity filter is working"""
    # Test the patterns directly
    test_words = ["ass", "fuck", "bitch", "shit", "damn"]
    results = []
    
    for word in test_words:
        is_profane_result = is_profane(word)
        results.append(f"{word}: {'🚫 BLOCKED' if is_profane_result else '✅ ALLOWED'}")
    
    embed = discord.Embed(
        title="🧪 Profanity Filter Test",
        description="Testing patterns with sample words:",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="Test Results",
        value="\n".join(results),
        inline=False
    )
    
    embed.add_field(
        name="Patterns Loaded",
        value=f"{len(custom_patterns)} patterns loaded",
        inline=False
    )
    
    await ctx.send(embed=embed)
    print(f"🧪 Profanity test requested by {ctx.author.name}")

@bot.command(name="profanitystatus")
@is_admin_or_trial_mod()
async def profanity_status(ctx):
    """Show the status of profanity filter systems"""
    # Check test mode restrictions
    if not is_test_command_allowed(ctx):
        if test_mode_active and test_restricted_mode:
            await ctx.send(f"❌ Test mode is **RESTRICTED**. Commands only work in <#{test_channel_id}>!", delete_after=5)
        return
    embed = discord.Embed(
        title="🛡️ Profanity Filter Status",
        description="Current profanity detection systems:",
        color=discord.Color.blue()
    )
    
    # Check custom patterns
    if custom_patterns:
        embed.add_field(
            name="✅ Custom Regex Patterns",
            value=f"Loaded {len(custom_patterns)} patterns from profanity.json",
            inline=False
        )
    else:
        embed.add_field(
            name="⚠️ Custom Regex Patterns",
            value="No patterns loaded (profanity.json not found or empty)",
            inline=False
        )
    
    embed.add_field(
        name="📝 Note",
        value="Profanity detection now uses only custom regex patterns from profanity.json",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name="reloadprofanity")
@is_admin_or_trial_mod()
async def reload_profanity(ctx):
    """Reload custom profanity patterns from profanity.json"""
    # Check test mode restrictions
    if not is_test_command_allowed(ctx):
        if test_mode_active and test_restricted_mode:
            await ctx.send(f"❌ Test mode is **RESTRICTED**. Commands only work in <#{test_channel_id}>!", delete_after=5)
        return
    global custom_patterns
    try:
        custom_patterns = load_custom_patterns()
        if custom_patterns:
            await ctx.send(f"✅ Reloaded {len(custom_patterns)} custom profanity patterns!")
        else:
            await ctx.send("⚠️ No custom patterns loaded. Check if profanity.json exists and is valid.")
    except Exception as e:
        await ctx.send(f"❌ Error reloading patterns: {str(e)}")

@bot.command(name="exemptedwords")
@is_admin_or_trial_mod()
async def show_exempted_words(ctx):
    """Show currently exempted words from profanity filter"""
    # Check test mode restrictions
    if not is_test_command_allowed(ctx):
        if test_mode_active and test_restricted_mode:
            await ctx.send(f"❌ Test mode is **RESTRICTED**. Commands only work in <#{test_channel_id}>!", delete_after=5)
        return
    embed = discord.Embed(
        title="🛡️ Exempted Words",
        description="These words are currently exempted from the profanity filter:",
        color=discord.Color.green()
    )
    
    exempted_list = [
        "shit, sh*t, sh!t, s***, s**t, s***t",
        "damn, d*mn, d*mn, d***, d**n, d***n"
    ]
    
    embed.add_field(
        name="Currently Exempted:",
        value="\n".join(exempted_list),
        inline=False
    )
    
    embed.add_field(
        name="Note:",
        value="These words are allowed when used alone or with basic punctuation.",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name="exemptedroles")
@is_admin_or_trial_mod()
async def show_exempted_roles(ctx):
    """Show the list of roles exempted from profanity filtering"""
    # Check test mode restrictions
    if not is_test_command_allowed(ctx):
        if test_mode_active and test_restricted_mode:
            await ctx.send(f"❌ Test mode is **RESTRICTED**. Commands only work in <#{test_channel_id}>!", delete_after=5)
        return
    embed = discord.Embed(
        title="🛡️ Exempted Roles",
        description="Users with these roles are exempted from profanity filtering:",
        color=discord.Color.blue()
    )
    
    exempted_roles = [
        "Senior Host Of Nikoh",
        "Moderator Of Nikoh", 
        "Technical Support",
        "Game Director",
        "Mod Director"
    ]
    
    embed.add_field(
        name="Specific Exempted Roles",
        value="\n".join([f"• {role}" for role in exempted_roles]),
        inline=False
    )
    
    embed.add_field(
        name="Note",
        value="Only these specific roles are exempted. Administrator roles are no longer automatically exempted.",
        inline=False
    )
    
    embed.set_footer(text="Users with these roles can use any language without being filtered.")
    
    await ctx.send(embed=embed)

bot.run(TOKEN)


