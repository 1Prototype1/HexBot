import os
import io
from datetime import datetime
from aiohttp import ClientSession
import ksoftapi

import discord
from discord.ext import commands
from discord.ext.commands import AutoShardedBot as asb

from utils import canvas

loaded = False

class HexBot(asb):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or("~"),
            description='Relatively simply awesome bot.',
            case_insensitive=True,
            intents=discord.Intents.all(),
            help_command=None
        )
        self.remove_command("help")
        self.launchtime = datetime.now()
        self.messages_in = 0
        self.messages_out = 0
        self.region = "Mumbai, IN"
        self.cog_blacklist = [
            "__init__.py"
        ]
        
        # Load cogs
        if not loaded:
            print("Loading cogs...")
            for filename in os.listdir("./cogs"):
                if filename.endswith(".py") and filename not in self.cog_blacklist:
                    try:
                        self.load_extension(f"cogs.{filename[:-3]}")
                        print(f"    Loaded '{filename}'")
                    except Exception as e:
                        print(str(e))
            loaded = True

    async def on_connect(self):
        print("Connected to Discord") # figured you might wanted this as you wanna know when its losing connection

    async def on_ready(self):
        print("Ready: " + self.user.name)
        self.kclient = ksoftapi.Client(os.environ['KSoft_Token'])
        self.client = ClientSession()
        
        await self.change_presence(status=discord.Status.idle, activity=discord.Game(name="Nothing"))

    async def on_message(self, message):
        if message == None: return
        if message.content == "": return

        if message.author.id == self.user.id:
            self.messages_out += 1

        elif message.content.startswith(self.get_prefix):
            self.messages_in += 1

        await self.process_commands(message)

    async def on_guild_join(self, guild):
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                return await channel.send('Hey there! Thank you for adding me!\nMy prefix is `~`\nStart by typing `~help`')

    async def on_member_join(self, member):
        sys_channel = member.guild.system_channel
        if sys_channel:
            data = await canvas.member_banner('Welcome', str(member), str(member.avatar_url_as(format='png', size=256)))
            with io.BytesIO() as img:
                data.save(img, 'PNG')
                img.seek(0)
                # are you sure its deleting the file after sending? make sure to check this
                try:
                    await sys_channel.send(content=member.mention, file=discord.File(fp=img, filename='welcome.png'))
                except Exception:
                    return

    async def on_member_remove(self, member):
        sys_channel = member.guild.system_channel
        if sys_channel:
            data = await canvas.member_banner('Bye Bye', str(member), str(member.avatar_url_as(format='png', size=256)))
            with io.BytesIO() as img:
                data.save(img, 'PNG')
                img.seek(0)
                # are you sure its deleting the file after sending? make sure to check this
                try:
                    await sys_channel.send(file=discord.File(fp=img, filename='leave.png'))
                except discord.Forbidden:
                    return

# All good ready to start!
if __name__ == "__main__":
    bot = HexBot()
    bot.run(os.environ['BOT_Token'])
