import os
import io
import datetime
from aiohttp import ClientSession
import ksoftapi

import discord
from discord.ext import commands

from utils import canvas

bot = commands.Bot(command_prefix=commands.when_mentioned_or("~"),
                    description='Relatively simply awesome bot.',
                    case_insensitive=True,
                    intents=discord.Intents.all())

bot.remove_command('help')

bot.uptime = datetime.datetime.now()
bot.messages_in = bot.messages_out = 0
bot.region = 'Mumbai, IN'

@bot.event
async def on_ready():
    print('Logged in as {0} ({0.id})'.format(bot.user))
    bot.kclient = ksoftapi.Client(os.environ['KSoft_Token'])
    bot.client = ClientSession()

    # Load Modules
    modules = ['music', 'fun', 'utility', 'meme', 'game', 'misc', 'debug']
    try:
        for module in modules:
            bot.load_extension('cogs.' + module)
            print('Loaded: ' + module)
    except Exception as e:
        print(f'Error loading {module}: {e}')

    print('Bot.....Activated')
    await bot.change_presence(status=discord.Status.idle, activity=discord.Game(name="Nothing"))

@bot.event
async def on_message(message):
    # Sent message
    if message.author.id == bot.user.id:
        if hasattr(bot, 'messages_out'):
            bot.messages_out += 1
    # Received message (Count only commands messages)
    elif message.content.startswith('~'):
        if hasattr(bot, 'messages_in'):
            bot.messages_in += 1

    await bot.process_commands(message)

@bot.event
async def on_guild_join(guild):
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            await channel.send('Hey there! Thank you for adding me!\nMy prefix is `~`\nStart by typing `~help`')
            break

@bot.event
async def on_member_join(member):
    sys_channel = member.guild.system_channel
    if sys_channel:
        data = await canvas.member_banner('Welcome', str(member), str(member.avatar_url_as(format='png', size=256)))
        with io.BytesIO() as img:
            data.save(img, 'PNG')
            img.seek(0)
            try:
                await sys_channel.send(content=member.mention, file=discord.File(fp=img, filename='welcome.png'))
            except discord.Forbidden:
                pass

@bot.event
async def on_member_remove(member):
    sys_channel = member.guild.system_channel
    if sys_channel:
        data = await canvas.member_banner('Bye Bye', str(member), str(member.avatar_url_as(format='png', size=256)))
        with io.BytesIO() as img:
            data.save(img, 'PNG')
            img.seek(0)
            try:
                await sys_channel.send(file=discord.File(fp=img, filename='leave.png'))
            except discord.Forbidden:
                pass

# All good ready to start!
print('Starting Bot...')
bot.run(os.environ['BOT_Token'])
