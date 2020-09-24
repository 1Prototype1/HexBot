import os
import io
import datetime
from aiohttp import ClientSession

import discord
from discord.ext import commands

bot = commands.Bot(command_prefix=commands.when_mentioned_or("~"),
					description='Relatively simply awesome bot.',
					case_insensitive=True)

bot.remove_command('help')

bot.uptime = datetime.datetime.now()
bot.messages_in = bot.messages_out = 0
bot.region = 'USA'

@bot.event
async def on_ready():
	bot.client = ClientSession()
	print('Logged in as {0} ({0.id})'.format(bot.user))
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
		url = 'https://some-random-api.ml/welcome/img/4/stars'
		params = 	{'type': 'join',
					'username': str(member.name),
					'discriminator': str(member.discriminator),
					'guildName': 'HexBot',
					'memberCount': '16',
					'avatar': str(member.avatar_url_as(size=512)),
					'textcolor': 'green'
					}
		async with bot.client.get(url, params=params) as r:
			if r.status != 200:
				return
			data = io.BytesIO(await r.read())
		try:	
			await sys_channel.send(content=member.mention, file=discord.File(data, 'welcome.png'))
		except discord.Forbidden:
			pass

@bot.event
async def on_member_remove(member):
	sys_channel = member.guild.system_channel
	if sys_channel:
		url = 'https://some-random-api.ml/welcome/img/4/stars'
		params = 	{'type': 'leave',
					'username': str(member.name),
					'discriminator': str(member.discriminator),
					'guildName': 'HexBot',
					'memberCount': '16',
					'avatar': str(member.avatar_url_as(size=512)),
					'textcolor': 'green'
					}
		async with bot.client.get(url, params=params) as r:
			if r.status != 200:
				return
			data = io.BytesIO(await r.read())
		try:	
			await sys_channel.send(file=discord.File(data, 'leave.png'))
		except discord.Forbidden:
			pass

@bot.command(name='help', aliases=['h'])
async def help(ctx):
	"""Display help"""
	embed = discord.Embed(title="Relatively simply awesome bot.", colour=discord.Colour(0x7f20a0))

	embed.set_thumbnail(url="https://i.ibb.co/yqgDwNh/hexbot.jpg")
	embed.set_author(name="HexBot Help", url="https://discord.com/oauth2/authorize?client_id=747461870629290035&scope=bot&permissions=24576", icon_url="https://i.ibb.co/yqgDwNh/hexbot.jpg")
	embed.set_footer(text="HexBot by [Prototype]#7731✨")

	embed.add_field(name=":musical_note: Music Commands:", value="```join|connect  - Joins a voice channel\nlyrics <song> - Get lyrics of the song\nnp            - Displays now playing song\npause         - Pauses the current song\nplay|p <song> - Plays specified song\nqueue|q       - Displays current queue\nresume        - Resumes the paused song\nsave|star     - Save song to your DM\nskip          - Skips current song\nstop|dis      - Stops and disconnects bot\nvolume        - Changes the player's volume```", inline=False)
	embed.add_field(name=":joystick: Fun Commands:", value="```8ball         - Magic 8Ball!\n\t<question>\nai            - Start AI chat\ndrake <a, b>  - Generate Drake meme\nfilter        - Apply filters to image\nfml           - Generate FML\nfortune|quote - Fortune Cookie!\n\t<category>[factoid|fortune|people]\nhangman       - Play Hangman\njoke          - Get a random joke\n\t\t\t\t[pun|dark|riddle|geek]\nmeme|maymay   - Get MayMays\npokedex       - Get Pokémon info\npoll          - Create a quick poll\n\t<question> <choices>\nquiz|trivia   - Start a quiz game\nroast user    - Roasts the mentioned user\nrps           - Play Rock, Paper, Scissors\ntally         - Tally the created poll\ntinder @u1@u2 - Get Tinder image\nteams         - Makes random teams(def. 2)\ntoss|flip     - Flips a Coin\ntrigger @user - Trigger an user\nttt           - Play Tic-Tac-Toe!\nwumpus        - Play Wumpus game\nxkcd|comic    - Get random xkcd comics```", inline=False)
	embed.add_field(name=":tools: Misc Commands:", value="```ascii <link>  - Get ascii art of user/img\nconvert       - Currency Converter\n\t<val><from><to>\nclear|cls     - Delete the messages\nencode <txt>  - Encode and style the text\nhelp          - Display this message\nlist          - Displays the list of\n\t\t\t\tvoice connected users\npalette <hex> - Get color palette\nping|latency  - Pong!\nserver <serv> - Get server info\nshorten|url   - Shorten an URL\nsupport       - Contact Bot owner\ntextart       - Generate text art\ntrace <ip>    - Locate IP address\ntranslate     - Translate the text\n\t<id><txt>\nuser @user    - Get user info\nwallpaper     - Get wallpaper\nweather <loc> - Get weather of location```", inline=False)

	try:
		await ctx.send(embed=embed)
	except Exception:
		await ctx.send("I don't have permission to send embeds here :disappointed_relieved:")

# Load Modules
modules = ['misc', 'games', 'music', 'debug', 'media']
try:
	for module in modules:
		bot.load_extension('cogs.' + module)
		print('Loaded: ' + module)
except Exception as e:
	print(f'Error loading {module}: {e}')
else:
# All good ready to start!
	print('Starting Bot...')
	bot.run(os.environ['BOT_Token'])