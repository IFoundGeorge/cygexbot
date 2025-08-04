import re
import json
import os
import discord
import requests
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

# ====== CARL-BOT LOG → YOUR MIRROR WEBHOOK MAP ======
channel_webhook_map = {
    1147510748663250954: 'https://discord.com/api/webhooks/1401397651655622827/sa44LbKLiBiqivhlvVNNjVnpJu92ilB2J7Louw_3Ei87t257sjVtkf-XYAEgsPrKQVe-',
    1386390379770679386: 'https://discord.com/api/webhooks/1401492460999413780/c_-mJBfwzohWja2yVtTpgec5l_Gzi9vfcr9IGz3GMlob2t6TEt_ajddyGPoTaUcmNbvN',
    1386389897459273780: 'https://discord.com/api/webhooks/1401493361516347392/SYznL9QzDXVF7ceNt7ygZ9zr_jn3Dc5O1OYauLASb0PF8cZV-fcSN8ParYYyiEYYq96',
    1386390075780239422: 'https://discord.com/api/webhooks/1401493669571465226/UQLz1LH5Y4VOdG835ki4kAh0G1mCdOUZ6W-zJ7IdOrDbcX4L9qWNMu1VcVnrgo1SLM_w',
    1386390252624547893: 'https://discord.com/api/webhooks/1401493800374767686/tpS-FadR9NAqxZMejlZjIK83Krg3pLd_BUivwRfRWznFCHHEiwkgXjp7EtjAtCHyC_8y',
    1386390501977794226: 'https://discord.com/api/webhooks/1401493904620261438/EfFK06JI3Sn65NyNlVF5QcMOJgLzBtoarV6ntfwe0LlrZgLvcLNZHy-8kGZE9-AaOZxB',
}

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

# Channel IDs for Carl bot
CARL_LOG_CHANNEL = 1147510748663250954
CARL_MESSAGE_CHANNEL = 1386390379770679386
CARL_MEMBER_CHANNEL = 1386389897459273780
CARL_SERVER_CHANNEL = 1386390075780239422
CARL_VOICE_CHANNEL = 1386390252624547893
CARL_JOIN_LEAVE_CHANNEL = 1386390501967794226

# Channel IDs
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
        # Show Carl channel selection menu
        embed = discord.Embed(
            title="Carl Bot Logs",
            description="Select which Carl bot log channel you want to view:",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Available Channels:",
            value="• Carl Log - General logs\n• Message Log - Message events\n• Member Log - Member events\n• Server Log - Server events\n• Voice Log - Voice channel events\n• Join/Leave Log - Member join/leave events",
            inline=False
        )
        
        carl_view = CarlChannelView(self)
        await interaction.response.edit_message(embed=embed, view=carl_view)
    
    @discord.ui.button(label="Ryno", style=discord.ButtonStyle.primary)
    async def ryno_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_logs(interaction, "Ryno", RYNO_LOG_CHANNEL)
    
    @discord.ui.button(label="Confession Logs", style=discord.ButtonStyle.primary)
    async def confession_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_logs(interaction, "Confession", CONFESSION_LOG_CHANNEL)
    
    async def show_logs(self, interaction: discord.Interaction, log_type: str, channel_id: int):
        # Get the guild from the bot's guilds since interaction.guild is None in DMs
        guild = None
        for g in interaction.client.guilds:
            if g.get_channel(channel_id):
                guild = g
                break
        
        if not guild:
            await interaction.response.send_message("Guild not found!", ephemeral=True)
            return
            
        channel = guild.get_channel(channel_id)
        if not channel:
            await interaction.response.send_message("Channel not found!", ephemeral=True)
            return
        
        # Fetch last 50 messages (newest first)
        messages = []
        async for message in channel.history(limit=50, oldest_first=False):
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
        
        # Send each message as a separate embed
        embeds = []
        for i, message in enumerate(page_messages, start=start_idx + 1):
            # Get message content and context
            content = message.content.strip() if message.content else ""
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            author_name = message.author.display_name if hasattr(message.author, 'display_name') else message.author.name
            
            # Create embed for this message
            embed = discord.Embed(
                title=f"{self.current_log_type} - Message {i}",
                description="",
                color=discord.Color.blue(),
                timestamp=message.created_at
            )
            
            # Add author info
            embed.set_author(name=author_name, icon_url=message.author.display_avatar.url if message.author.display_avatar else None)
            
            # Build the message description
            message_parts = []
            
            # Add text content if available
            if content:
                message_parts.append(content[:150] + "..." if len(content) > 150 else content)
            
            # Add embed details if message has embeds
            if message.embeds:
                for j, msg_embed in enumerate(message.embeds):
                    embed_parts = []
                    if msg_embed.title:
                        embed_parts.append(f"**{msg_embed.title}**")
                    if msg_embed.description:
                        desc = msg_embed.description[:100] + "..." if len(msg_embed.description) > 100 else msg_embed.description
                        embed_parts.append(desc)
                    if msg_embed.fields:
                        field_names = [field.name for field in msg_embed.fields[:3]]  # Show first 3 field names
                        embed_parts.append(f"Fields: {', '.join(field_names)}")
                    if msg_embed.footer and msg_embed.footer.text:
                        embed_parts.append(f"Footer: {msg_embed.footer.text}")
                    
                    if embed_parts:
                        message_parts.append(f"📎 Embed {j+1}: " + " | ".join(embed_parts))
                    else:
                        message_parts.append(f"📎 Embed {j+1}: [No visible content]")
            
            # Add attachment info if message has attachments
            if message.attachments:
                attachment_count = len(message.attachments)
                message_parts.append(f"📎 Contains {attachment_count} attachment{'s' if attachment_count > 1 else ''}")
            
            # Add system message info
            if message.type != discord.MessageType.default:
                message_parts.append(f"🔧 System message: {message.type.name}")
            
            # If no content and no special features, show context
            if not message_parts:
                message_parts.append("[Message with no visible content]")
            
            # Set the description
            embed.description = "\n".join(message_parts)
            
            # Add footer with pagination info
            embed.set_footer(text=f"Page {self.current_page + 1} • Message {i} of {len(self.messages)}")
            
            embeds.append(embed)
        
        # Determine which view to use based on whether this is a search result
        if hasattr(self, 'original_messages') and len(self.messages) < len(self.original_messages):
            # This is a search result, use SearchResultsView
            nav_view = SearchResultsView(self, self.original_messages)
        else:
            # This is the normal log view, use LogNavigationView
            nav_view = LogNavigationView(self)
        
        # Send all embeds
        await interaction.response.edit_message(embeds=embeds, view=nav_view)

# In-memory state for search mode
search_states = {}

class SearchView(discord.ui.View):
    def __init__(self, log_view: LogView):
        super().__init__(timeout=60)
        self.log_view = log_view
        self.selected_log_type = None
    
    @discord.ui.select(
        placeholder="Select log type to search in...",
        options=[
            discord.SelectOption(label="All Logs", value="all", description="Search in all available logs"),
            discord.SelectOption(label="Carl Log", value="carl", description="General Carl bot logs"),
            discord.SelectOption(label="Message Log", value="message", description="Message-related events"),
            discord.SelectOption(label="Member Log", value="member", description="Member events"),
            discord.SelectOption(label="Server Log", value="server", description="Server events"),
            discord.SelectOption(label="Voice Log", value="voice", description="Voice channel events"),
            discord.SelectOption(label="Join/Leave Log", value="join/leave", description="Member join/leave events"),
            discord.SelectOption(label="Ryno Log", value="ryno", description="Ryno bot logs"),
            discord.SelectOption(label="Confession Log", value="confession", description="Confession logs")
        ]
    )
    async def log_type_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_log_type = select.values[0]
        await interaction.response.send_message(f"Selected log type: {select.values[0]}", ephemeral=True)
    
    @discord.ui.button(label="🔍 Search by Username", style=discord.ButtonStyle.primary)
    async def search_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_log_type:
            await interaction.response.send_message("Please select a log type first!", ephemeral=True)
            return
        
        # Show username input modal
        modal = UsernameSearchModal(self.log_view, self.selected_log_type)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="◀️ Back", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Return to log view
        await self.log_view.display_page(interaction)

class UsernameSearchModal(discord.ui.Modal, title="Search by Username"):
    def __init__(self, log_view: LogView, log_type: str):
        super().__init__()
        self.log_view = log_view
        self.log_type = log_type
        self.original_messages = log_view.messages.copy()  # Store original messages
    
    username = discord.ui.TextInput(
        label="Username/Name to Search",
        placeholder="Enter username or display name to search for...",
        required=True,
        max_length=50
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        username = self.username.value.lower().strip()
        
        # Filter messages by username
        filtered = []
        for msg in self.log_view.messages:
            # Check if username matches the message author
            author_name = (msg.author.display_name or msg.author.name).lower()
            if username in author_name:
                filtered.append(msg)
                continue
            
            # Check if username appears in message content
            if username in (msg.content or '').lower():
                filtered.append(msg)
                continue
            
            # Check if username appears in embeds
            for emb in msg.embeds:
                if (emb.title and username in emb.title.lower()) or \
                   (emb.description and username in emb.description.lower()):
                    filtered.append(msg)
                    break
        
        # If specific log type is selected (not "all"), filter further
        if self.log_type != "all":
            log_type_filtered = []
            for msg in filtered:
                # Check if the log type appears in the message content or embeds
                if self.log_type in (msg.content or '').lower():
                    log_type_filtered.append(msg)
                    continue
                for emb in msg.embeds:
                    if (emb.title and self.log_type in emb.title.lower()) or \
                       (emb.description and self.log_type in emb.description.lower()):
                        log_type_filtered.append(msg)
                        break
            filtered = log_type_filtered
        
        # Update log_view to show only filtered messages
        self.log_view.messages = filtered
        self.log_view.current_page = 0
        
        if filtered:
            search_description = f"Username: '{username}'"
            if self.log_type != "all":
                search_description += f" | Log Type: '{self.log_type}'"
            
            # Create search results embed
            results_embed = discord.Embed(
                title=f"🔍 Search Results",
                description=f"Found {len(filtered)} results for {search_description}",
                color=discord.Color.green()
            )
            
            # Display the filtered results as individual embeds
            await self.log_view.display_page(interaction)
            
            # Send confirmation message
            await interaction.followup.send(
                f"✅ Search complete! Showing {len(filtered)} results.", 
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ No results found for username '{username}'" + 
                (f" in log type '{self.log_type}'" if self.log_type != "all" else ""), 
                ephemeral=True
            )
            # Restore original messages
            self.log_view.messages = self.original_messages

class SearchResultsView(discord.ui.View):
    def __init__(self, log_view: LogView, original_messages):
        super().__init__(timeout=None)
        self.log_view = log_view
        self.original_messages = original_messages
    
    @discord.ui.button(label="◀️ Back to All Logs", style=discord.ButtonStyle.secondary)
    async def back_to_all_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Restore original messages and display
        self.log_view.messages = self.original_messages
        self.log_view.current_page = 0
        await self.log_view.display_page(interaction)
    
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

class LogNavigationView(discord.ui.View):
    def __init__(self, log_view: LogView):
        super().__init__(timeout=None)
        self.log_view = log_view
    
    @discord.ui.button(label="🔍 Search", style=discord.ButtonStyle.primary)
    async def search_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Show the search view with dropdown
        search_view = SearchView(self.log_view)
        embed = discord.Embed(
            title="Search Logs",
            description="1. Select a log type from the dropdown\n2. Click 'Search by Username' to enter the username",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=search_view)
    
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

class CarlChannelView(discord.ui.View):
    def __init__(self, log_view: LogView):
        super().__init__(timeout=None)
        self.log_view = log_view
    
    @discord.ui.button(label="Carl Log", style=discord.ButtonStyle.primary)
    async def carl_log_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.log_view.show_logs(interaction, "Carl Log", CARL_LOG_CHANNEL)
    
    @discord.ui.button(label="Message Log", style=discord.ButtonStyle.primary)
    async def carl_message_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.log_view.show_logs(interaction, "Carl Message", CARL_MESSAGE_CHANNEL)
    
    @discord.ui.button(label="Member Log", style=discord.ButtonStyle.primary)
    async def carl_member_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.log_view.show_logs(interaction, "Carl Member", CARL_MEMBER_CHANNEL)
    
    @discord.ui.button(label="Server Log", style=discord.ButtonStyle.primary)
    async def carl_server_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.log_view.show_logs(interaction, "Carl Server", CARL_SERVER_CHANNEL)
    
    @discord.ui.button(label="Voice Log", style=discord.ButtonStyle.primary)
    async def carl_voice_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.log_view.show_logs(interaction, "Carl Voice", CARL_VOICE_CHANNEL)
    
    @discord.ui.button(label="Join/Leave Log", style=discord.ButtonStyle.primary)
    async def carl_join_leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.log_view.show_logs(interaction, "Carl Join/Leave", CARL_JOIN_LEAVE_CHANNEL)
    
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
    if message.author == bot.user:
        return

    # ====== RELAY BOT FUNCTIONALITY ======
    # Check if this message is from a monitored channel and should be relayed
    if message.guild and message.channel.id in channel_webhook_map:
        webhook_url = channel_webhook_map[message.channel.id]
        
        # Get the username/nickname
        display_name = message.author.nick if hasattr(message.author, 'nick') and message.author.nick else message.author.name
        
        # Combine text and embeds
        content_parts = []
        if message.content:
            content_parts.append(message.content)
        for embed in message.embeds:
            if embed.title:
                content_parts.append(f"**{embed.title}**")
            if embed.description:
                content_parts.append(embed.description)
        
        combined_content = "\n".join(content_parts).strip()
        
        # Create the main content
        data = {
            "content": f"📨 **Log from #{message.channel.name} by {display_name}:**\n{combined_content or '(No text)'}",
            "embeds": []
        }
        
        # Handle image attachments
        for att in message.attachments:
            if att.filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                data["embeds"].append({
                    "image": {"url": att.url},
                    "description": f"🖼️ Attachment: {att.filename}"
                })
        
        try:
            response = requests.post(webhook_url, json=data)
            if response.status_code not in [200, 204]:
                print(f"❌ Webhook failed: {response.status_code}, {response.text}")
        except Exception as e:
            print(f"⚠️ Error sending relay message: {e}")

    # ====== PROFANITY FILTER FUNCTIONALITY ======
    if not message.guild:
        # Handle DM messages (for search functionality)
        user_id = message.author.id
        if user_id in search_states and search_states[user_id]['searching']:
            search_term = message.content.lower().strip()
            log_view = search_states[user_id]['log_view']
            # Filter messages
            filtered = []
            for msg in log_view.messages:
                # Check text content
                if search_term in (msg.content or '').lower():
                    filtered.append(msg)
                    continue
                # Check embed fields
                for emb in msg.embeds:
                    if (emb.title and search_term in emb.title.lower()) or \
                       (emb.description and search_term in emb.description.lower()):
                        filtered.append(msg)
                        break
            # Update log_view to show only filtered messages
            log_view.messages = filtered
            log_view.current_page = 0
            search_states[user_id]['searching'] = False
            # Send results in DM
            await log_view.display_page(await message.author.send("Search results:"))
            await message.channel.send("Search complete. Use navigation to browse results or click 'Back to all logs' to exit search mode.")
            return
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


