import os
import io
import datetime
from aiohttp import ClientSession

import discord
from discord.ext import commands

from utils import canvas
from subprocess import Popen, PIPE

bot = commands.Bot(command_prefix=commands.when_mentioned_or("~"),
					description='Relatively simply awesome bot.',
					case_insensitive=True,
					intents=discord.Intents.all())

bot.remove_command('help')

bot.uptime = datetime.datetime.now()
bot.messages_in = bot.messages_out = 0
bot.region = 'USA'

@bot.event
async def on_ready():
	bot.client = ClientSession()
	print('Logged in as {0} ({0.id})'.format(bot.user))

	bot.load_extension('cogs.music')
	process = Popen(['java', '-jar', 'Lavalink.jar'], stdout=PIPE, stderr=PIPE) # Start Lavalink
	print('Music.....Activated')

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

@bot.command(name='help', aliases=['h'])
async def help(ctx, arg: str=''):
	"""Display help"""
	embed = discord.Embed(title="Relatively simply awesome bot.", colour=discord.Colour(0x7f20a0))

	embed.set_thumbnail(url="https://i.ibb.co/yqgDwNh/hexbot.jpg")
	embed.set_author(name="HexBot Help", url="https://discord.com/oauth2/authorize?client_id=747461870629290035&scope=bot&permissions=57344", icon_url="https://i.ibb.co/yqgDwNh/hexbot.jpg")
	embed.set_footer(text="HexBot by [Prototype]#7731✨")

	if arg.strip().lower() == '-a':
		# Full version
		embed.add_field(name=":musical_note: Music Commands:", value="```equalizer     - Use equalizer\nlyrics <song> - Get lyrics of the song\nnow|np        - Displays now playing song\npause|resume  - Pause/Resume current song\nplay|p <song> - Plays specified song\nqueue|q       - Displays current queue\nremove <idx>  - Remove song from queue\nrepeat        - Enable/Disable repeat\nresume        - Resumes the paused song\nseek          - Seek current track\nsave|star     - Save song to your DM\nshuffle       - Enable/Disable shuffle\nskip          - Skips current song\nstop|dis      - Stops and disconnects bot\nvolume <val>  - Changes the volume[0-1000]```", inline=False)
		embed.add_field(name=":stuck_out_tongue_winking_eye: Fun Commands:", value="```ai            - Start AI chat\nadvice        - Get some advice\nascii <link>  - Get ascii art of user/img\nbored|suggest - Suggestion for boredom\nfilter        - Apply filters to image\nfortune|quote - Fortune Cookie!\n    <category>[factoid|fortune|people]\ntextart       - Generate text art\nwallpaper     - Get wallpaper```", inline=False)
		embed.add_field(name=":tools: Utility Commands:", value="```convert       - Currency Converter\n    <val><from><to>\nencode <txt>  - Encode and style the text\nlist          - Displays the list of\n                voice connected users\npalette <hex> - Get color palette\npokedex       - Get Pokémon info\nrhyme <word>  - Get rhyming words\ntrace <ip>    - Locate IP address\ntranslate     - Translate the text\n    <id><txt>\nserver <serv> - Get server info\nshorten|url   - Shorten an URL\nuser @user    - Get user info\nweather <loc> - Get weather of location\nwordinfo      - Get word info```", inline=False)
		embed.add_field(name="<:doge:761603676510093312> Meme Commands:", value="```bill          - Generate bill meme\ndrake <a, b>  - Generate Drake meme\nfml           - Generate FML\njoke          - Get a random joke\n                [pun|dark|riddle|geek]\nmeme|maymay   - Get MayMays\nroast @user   - Roasts the mentioned user\ntinder @u1@u2 - Get Tinder image\ntrigger @user - Trigger an user\nxkcd|comic    - Get random xkcd comics```", inline=False)
		embed.add_field(name=":joystick: Game Commands:", value="```8ball         - Magic 8Ball!\n    <question>\nhangman       - Play Hangman\nquiz|trivia   - Start a quiz game\npoll          - Create a quick poll\n    <question> <choices>\nrps           - Play Rock, Paper, Scissors\ntally         - Tally the created poll\nteams         - Makes random teams(def. 2)\ntoss|flip     - Flips a Coin\nttt           - Play Tic-Tac-Toe!\nwumpus        - Play Wumpus game```", inline=False)
		embed.add_field(name=":gear: Misc Commands:", value="```clear|cls     - Delete the messages\nhelp          - Display this message\nping|latency  - Pong!\nsupport       - Contact Bot owner```", inline=False)
	else:
		# Short version
		embed.description = 'Type `~help -a` for detailed help.'
		embed.add_field(name=":musical_note: Music:", value="`equalizer`, `lyrics`, `now`, `pause`, `p`, `play`, `queue`, `remove`, `repeat`, `resume`, `seek`, `save`, `shuffle`, `skip`, `stop`, `volume`")
		embed.add_field(name=":stuck_out_tongue_winking_eye: Fun:", value="`ai`, `advice`, `ascii`, `bored`, `filter`, `fortune`, `quote`, `textart`, `wallpaper`")
		embed.add_field(name=":tools: Utility:", value="`convert`, `encode`, `list`, `palette`, `pokedex`, `rhyme`, `trace`, `translate`, `server`, `shorten`, `user`, `weather`, `wordinfo`")
		embed.add_field(name="<:doge:761603676510093312> Meme:", value="`bill`, `drake`, `fml`, `joke`, `meme`, `roast`, `tinder`, `trigger`, `xkcd`")
		embed.add_field(name=":joystick: Game:", value="`8ball`, `hangman`, `trivia`, `poll`, `rps`, `tally`, `teams`, `toss`, `ttt`, `wumpus`")
		embed.add_field(name=":gear: Misc:", value="`clear`, `help`, `ping`, `support`")
	try:
		await ctx.send(embed=embed)
	except Exception:
		await ctx.send("I don't have permission to send embeds here :disappointed_relieved:")

# Load Modules
modules = ['misc', 'games', 'debug', 'media']

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