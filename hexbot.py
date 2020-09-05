import os
import asyncio
from functools import partial
import sys
import traceback
import itertools
import time
import random
import discord
from discord.ext import commands
from async_timeout import timeout
from youtube_dl import YoutubeDL

import fortune
import aiopentdb
from speedtest import Speedtest
import xkcd
import ksoftapi
from games import tictactoe, wumpus, hangman

# Cog Modules
import userinfo


ytdlopts = {
	'format': 'bestaudio/best',
	'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
	'restrictfilenames': True,
	'noplaylist': True,
	'nocheckcertificate': True,
	'ignoreerrors': False,
	'logtostderr': False,
	'quiet': True,
	'no_warnings': True,
	'default_search': 'auto',
	'source_address': '0.0.0.0'  # ipv6 addresses cause issues sometimes
}

ffmpegopts = {
	'before_options': '-nostdin',
	'options': '-vn'
}

ytdl = YoutubeDL(ytdlopts)


class VoiceConnectionError(commands.CommandError):
	"""Custom Exception class for connection errors."""

class InvalidVoiceChannel(VoiceConnectionError):
	"""Exception for cases of invalid Voice Channels."""

class YTDLSource(discord.PCMVolumeTransformer):

	def __init__(self, source, *, data, requester):
		super().__init__(source)
		self.requester = requester

		self.title = data.get('title')
		self.url = data.get('url')
		self.thumbnail = data.get('thumbnail')
		self.duration = data.get('duration')
		self.web_url = data.get('webpage_url')

		# https://github.com/rg3/youtube-dl/blob/master/README.md

	def __getitem__(self, item: str):
		"""Allows us to access attributes similar to a dict. This is only useful when you are NOT downloading."""
		return self.__getattribute__(item)

	@classmethod
	async def create_source(cls, ctx, search: str, *, loop, download=True):
		loop = loop or asyncio.get_event_loop()

		to_run = partial(ytdl.extract_info, url=search, download=download)
		data = await loop.run_in_executor(None, to_run)

		if 'entries' in data:
			# take first item from a playlist
			data = data['entries'][0]

		await ctx.send(f'```json\n"Added {data["title"]} to the Queue."\n```')

		if download:
			source = ytdl.prepare_filename(data)
		else:
			return {'webpage_url': data['webpage_url'], 'requester': ctx.author, 'title': data['title']}

		return cls(discord.FFmpegPCMAudio(source), data=data, requester=ctx.author)

	@classmethod
	async def regather_stream(cls, data, *, loop):
		"""Used for preparing a stream, instead of downloading.
		Since Youtube Streaming links expire."""
		loop = loop or asyncio.get_event_loop()
		requester = data['requester']

		to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=True)
		data = await loop.run_in_executor(None, to_run)

		return cls(discord.FFmpegPCMAudio(data['url']), data=data, requester=requester)

class MusicPlayer:
	"""A class which is assigned to each guild using the bot for Music.
	This class implements a queue and loop, which allows for different guilds to listen to different playlists
	simultaneously.
	When the bot disconnects from the Voice it's instance will be destroyed.
	"""

	__slots__ = ('bot', '_guild', '_channel', '_cog', 'queue', 'next', 'current', 'np', 'volume')

	def __init__(self, ctx):
		self.bot = ctx.bot
		self._guild = ctx.guild
		self._channel = ctx.channel
		self._cog = ctx.cog

		self.queue = asyncio.Queue()
		self.next = asyncio.Event()

		self.np = None  # Now playing message
		self.volume = .2
		self.current = None

		ctx.bot.loop.create_task(self.player_loop())

	async def player_loop(self):
		"""Our main player loop."""
		await self.bot.wait_until_ready()

		while not self.bot.is_closed():
			self.next.clear()

			try:
				# Wait for the next song. If we timeout cancel the player and disconnect...
				async with timeout(300):  # 5 minutes...
					source = await self.queue.get()
			except asyncio.TimeoutError:
				return self.destroy(self._guild)

			if not isinstance(source, YTDLSource):
				# Source was probably a stream (not downloaded)
				# So we should regather to prevent stream expiration
				try:
					source = await YTDLSource.regather_stream(source, loop=self.bot.loop)
				except Exception as e:
					await self._channel.send(f'There was an error processing your song.\n'
											 f'```css\n[{e}]\n```')
					continue

			source.volume = self.volume
			self.current = source

			self._guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
			embed = discord.Embed(colour=discord.Colour(0x59FFC8), description=f"[{source.title}]({source.web_url})")
			embed.set_thumbnail(url=source.thumbnail)
			embed.set_author(name="Now Playing 🎵", url=f"{source.url}", icon_url="https://i.ibb.co/DGsmTvh/star.gif")
			self.np = await self._channel.send(embed=embed)
			await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=source.title))
			await self.next.wait()

			# Make sure the FFmpeg process is cleaned up.
			source.cleanup()
			self.current = None

			try:
				# We are no longer playing this song...
				await self.np.delete()
				await bot.change_presence(status=discord.Status.idle, activity=discord.Game(name="Nothing"))
			except discord.HTTPException:
				pass

	def destroy(self, guild):
		"""Disconnect and cleanup the player."""
		return self.bot.loop.create_task(self._cog.cleanup(guild))

class Music(commands.Cog):
	"""Music related commands."""

	__slots__ = ('bot', 'players')

	def __init__(self, bot):
		self.bot = bot
		self.players = {}

	async def cleanup(self, guild):
		try:
			await guild.voice_client.disconnect()
			await bot.change_presence(status=discord.Status.idle, activity=discord.Game(name="Nothing"))
		except AttributeError:
			pass

		try:
			del self.players[guild.id]
		except KeyError:
			pass

	async def __local_check(self, ctx):
		"""A local check which applies to all commands in this cog."""
		if not ctx.guild:
			raise commands.NoPrivateMessage
		return True

	async def __error(self, ctx, error):
		"""A local error handler for all errors arising from commands in this cog."""
		if isinstance(error, commands.NoPrivateMessage):
			try:
				return await ctx.send('This command can not be used in Private Messages.')
			except discord.HTTPException:
				pass
		elif isinstance(error, InvalidVoiceChannel):
			await ctx.send('Error connecting to Voice Channel. '
						   'Please make sure you are in a valid channel or provide me with one')

		print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
		traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

	def get_player(self, ctx):
		"""Retrieve the guild player, or generate one."""
		try:
			player = self.players[ctx.guild.id]
		except KeyError:
			player = MusicPlayer(ctx)
			self.players[ctx.guild.id] = player

		return player

	@commands.command(name='connect', aliases=['join'])
	async def connect_(self, ctx, *, channel: discord.VoiceChannel=None):
		"""Connect to voice.
		Parameters
		------------
		channel: discord.VoiceChannel [Optional]
			The channel to connect to. If a channel is not specified, an attempt to join the voice channel you are in
			will be made.
		This command also handles moving the bot to different channels.
		"""
		if not channel:
			try:
				channel = ctx.author.voice.channel
			except AttributeError:
				await ctx.send("Please join a channel or specify a valid channel :warning:")
				raise InvalidVoiceChannel('No channel to join. Please either specify a valid channel or join one.')

		vc = ctx.voice_client

		if vc:
			if vc.channel.id == channel.id:
				return
			try:
				await vc.move_to(channel)
			except asyncio.TimeoutError:
				await ctx.send(f"I can't join `{channel}`:disappointed_relieved:")
				raise VoiceConnectionError(f'Moving to channel: <{channel}> timed out.')
		else:
			try:
				await channel.connect(timeout=5.0)
			except asyncio.TimeoutError:
				await ctx.send(f"I can't join `{channel}`:disappointed_relieved:")
				raise VoiceConnectionError(f'Connecting to channel: <{channel}> timed out.')

		await ctx.send(f'Connected to: **{channel}**', delete_after=20)

	@commands.command(name='play', aliases=['sing', 'p'])
	async def play_(self, ctx, *, search: str = ""):
		"""Request a song and add it to the queue.
		This command attempts to join a valid voice channel if the bot is not already in one.
		Uses YTDL to automatically search and retrieve a song.
		Parameters
		------------
		search: str [Required]
			The song to search and retrieve using YTDL. This could be a simple search, an ID or URL.
		"""
		if search=="":
			return await ctx.send("Please specify song name :musical_note:")

		await ctx.trigger_typing()

		vc = ctx.voice_client

		if not vc:
			await ctx.invoke(self.connect_)

		player = self.get_player(ctx)

		# If download is False, source will be a dict which will be used later to regather the stream.
		# If download is True, source will be a discord.FFmpegPCMAudio with a VolumeTransformer.
		source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop, download=True)

		await player.queue.put(source)

	@commands.command(name='pause')
	async def pause_(self, ctx):
		"""Pause the currently playing song."""
		vc = ctx.voice_client

		if not vc or not vc.is_playing():
			return await ctx.send('I\'m not currently playing anything :warning:', delete_after=20)
		if vc.is_paused():
			return

		vc.pause()
		await ctx.message.add_reaction('⏸')

		def check(reaction, user):
			return user != bot.user and (str(reaction.emoji) == '⏸')
		try:
			reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
		except asyncio.TimeoutError:
			await ctx.message.clear_reaction('⏸')
		else:
			vc.resume()
			await ctx.message.clear_reaction('⏸')

	@commands.command(name='resume')
	async def resume_(self, ctx):
		"""Resume the currently paused song."""
		vc = ctx.voice_client

		if not vc or not vc.is_connected():
			return await ctx.send('I\'m not currently playing anything :warning:', delete_after=20)
		if not vc.is_paused():
			return

		vc.resume()
		await ctx.message.add_reaction('▶')

	@commands.command(name='skip', aliases=['next'])
	async def skip_(self, ctx):
		"""Skip the song."""
		vc = ctx.voice_client

		if not vc or not vc.is_connected():
			return await ctx.send('I\'m not currently playing anything :warning:', delete_after=20)

		if vc.is_paused():
			pass
		elif not vc.is_playing():
			return

		vc.stop()
		await ctx.send(f'**`{ctx.author}`**: Skipped the song :fast_forward:')

	@commands.command(name='queue', aliases=['q', 'playlist'])
	async def queue_info(self, ctx):
		"""Retrieve a basic queue of upcoming songs."""
		vc = ctx.voice_client

		if not vc or not vc.is_connected():
			return await ctx.send('I\'m not currently connected to voice! :mute:', delete_after=20)

		player = self.get_player(ctx)
		if player.queue.empty():
			return await ctx.send('There are currently no more queued songs :warning:')

		# Grab up to 5 entries from the queue...
		upcoming = list(itertools.islice(player.queue._queue, 0, 5))

		fmt = '\n'.join(f'**`{_["title"]}`**' for _ in upcoming)
		embed = discord.Embed(title=f'Upcoming next {len(upcoming)}:', description=fmt)

		await ctx.send(embed=embed)

	@commands.command(name='np', aliases=['current', 'currentsong', 'playing'])
	async def now_playing_(self, ctx):
		"""Display information about the currently playing song."""
		vc = ctx.voice_client

		if not vc or not vc.is_connected():
			return await ctx.send('I\'m not currently connected to voice! :mute:', delete_after=20)
		player = self.get_player(ctx)
		if not player.current:
			return await ctx.send('I\'m not currently playing anything :warning:')
		try:
			# Remove our previous now_playing message.
			await player.np.delete()
		except discord.HTTPException:
			pass

		embed = discord.Embed(colour=discord.Colour(0x59FFC8), description=f"[{vc.source.title}]({vc.source.web_url})")
		embed.set_thumbnail(url=vc.source.thumbnail)
		embed.set_author(name="Now Playing 🎵", url=f"{vc.source.url}", icon_url="https://i.ibb.co/DGsmTvh/star.gif")
		embed.set_footer(text=f"Requested by: {vc.source.requester}", icon_url=vc.source.requester.avatar_url)

		player.np = await ctx.send(embed=embed)

	@commands.command(name='save', aliases=['star'])
	async def savetodm(self, ctx):
		"""Send DM of currently playing song"""
		vc = ctx.voice_client

		if not vc or not vc.is_connected():
			return await ctx.send('I\'m not currently connected to voice! :mute:', delete_after=20)
		player = self.get_player(ctx)
		if not player.current:
			return await ctx.send('I\'m not currently playing anything :warning:')

		embed = discord.Embed(colour=discord.Colour(0x59FFC8), description=f"[{vc.source.title}]({vc.source.web_url})")
		embed.set_thumbnail(url=vc.source.thumbnail)
		embed.set_author(name="Now Playing 🎵", url=f"{vc.source.url}", icon_url="https://i.ibb.co/DGsmTvh/star.gif")
		embed.set_footer(text=f"Requested by: {vc.source.requester}", icon_url=vc.source.requester.avatar_url)

		user = ctx.author
		await user.send(embed=embed)
		await ctx.send(f"Current song has been sent to you {ctx.author.mention} :floppy_disk:")

	@commands.command(name='volume', aliases=['vol'])
	async def change_volume(self, ctx, *, vol: float):
		"""Change the player volume.
		Parameters
		------------
		volume: float or int [Required]
			The volume to set the player to in percentage. This must be between 1 and 100.
		"""
		vc = ctx.voice_client

		if not vc or not vc.is_connected():
			return await ctx.send('I\'m not currently connected to voice :mute:', delete_after=20)

		if not 0 < vol < 101:
			return await ctx.send('Please enter a value between 1 and 100.')

		player = self.get_player(ctx)

		if vc.source:
			vc.source.volume = vol / 100

		player.volume = vol / 100
		await ctx.send(f'**`{ctx.author}`**: Set the volume to **{vol}%**')

	@commands.command(name='stop', aliases=['dis', 'disconnect'])
	async def stop_(self, ctx):
		"""Stop the currently playing song and destroy the player.
		!Warning!
			This will destroy the player assigned to your guild, also deleting any queued songs and settings.
		"""
		vc = ctx.voice_client

		if not vc or not vc.is_connected():
			return await ctx.send('I\'m not currently playing anything!', delete_after=20)

		await self.cleanup(ctx.guild)

	@commands.command(name='lyrics', aliases=['ly'])
	async def get_lyrics(self, ctx):
		"""Get lyrics of current song"""
		vc = ctx.voice_client
		if not vc or not vc.is_connected():
			return await ctx.send('I\'m not currently connected to voice! :mute:', delete_after=20)
		player = self.get_player(ctx)
		if not player.current:
			return await ctx.send('I\'m not currently playing anything :warning:')
		query = vc.source.title
		
		kclient = ksoftapi.Client(os.environ['KSoft_Token'])
		try:
			async with ctx.typing():
				results = await kclient.music.lyrics(query)
		except ksoftapi.NoResults:
			await ctx.send(f'No lyrics found for `{query}`')
		else:
			lyrics = results[0].lyrics
			embed = discord.Embed(title=vc.source.title, color=discord.Color(0xCCFF00), url=vc.source.web_url, description=lyrics[:2048])
			embed.set_thumbnail(url=vc.source.thumbnail)
			embed.set_author(name="Lyrics:")
			lyrics = lyrics[2048:]
			embeds = [embed] # create embeds' list for long lyrics
			while len(lyrics) > 0 and len(embeds) < 10: # limiting embeds to 10
				embed = discord.Embed(color=discord.Color(0xCCFF00), description=lyrics[:2048])
				lyrics = lyrics[len(embeds)*2048:]
				embeds.append(embed)
			embeds[-1].set_footer(text="Source: KSoft.Si") # set footer for last embed
			for embed in embeds:
				await ctx.send(embed=embed)
		finally:
			await kclient.close()

class Misc(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.command(name='list')
	async def listusers(self, ctx):
		"""Displays the list of connected users"""
		members = ctx.author.voice.channel.members
		memnames = []
		for member in members:
			memnames.append(member.name)
		await ctx.send(f"Members in {ctx.author.voice.channel.name}:\n```\n" + "\n".join(memnames) +"\n```")
	
	@commands.command(name='teams', aliases=['team'])
	async def teams(self, ctx, num=2):
		"""Makes random teams with specified number(def. 2)"""
		members = ctx.author.voice.channel.members
		memnames = []
		for member in members:
			memnames.append(member.name)
		
		remaining = memnames
		if len(memnames)>=num:
			for i in range(num):
				team = random.sample(remaining,len(memnames)//num)
				remaining = [x for x in remaining if x not in team]
				await ctx.send(f"Team {chr(65+i)}\n" + "```CSS\n" + '\n'.join(team) + "\n```")
		if len(remaining)> 0:
			await ctx.send("Remaining\n```diff\n- " + '\n- '.join(remaining) + "\n```")


	@commands.command(name='clear', aliases=['cls'])
	async def clear(self, ctx, limit=20):
		"""Delete the messages sent in current text-channel"""
		if 1>limit>100:
			limit = 20
		messages = []
		try:
			await ctx.message.channel.purge(limit=limit)
		except discord.Forbidden:
			await ctx.send("I don't have permission to `Manage Messages`:disappointed_relieved:")

	@commands.command(name='ping', aliases=['latency'])
	async def ping(self, ctx):
		""" Pong! """
		before = time.monotonic()
		message = await ctx.send("Pong!")
		ping = (time.monotonic() - before) * 1000
		await message.edit(content=f"Pong!  \nTook `{int(ping)}ms`\nLatency: `{int(bot.latency*1000)}ms`")

	@commands.command(name='speedtest')
	async def speed_test(self, ctx):		
		"""Speedtest"""
		async with ctx.typing():
			if await bot.is_owner(ctx.author):
				s = Speedtest()
				s.get_best_server()
				s.download()
				s.upload()
				s = s.results.dict()
				
				await ctx.send(f"Ping: `{s['ping']}ms`\nDownload: `{round(s['download']/10**6, 3)} Mbits/s`\nUpload: `{round(s['upload']/10**6, 3)} Mbits/s`\nServer: `{s['server']['sponsor']}, {s['server']['name']}, {s['server']['country']}`\nBot: `{s['client']['isp']}({s['client']['ip']}) {s['client']['country']} {s['client']['isprating']}`")
			else:
				await ctx.send("Only bot owner is permitted to use this command :man_technologist_tone1:")

	@commands.command(name='weather')
	async def weather(self, ctx, *, location: str = ""):
		"""Get weather"""
		if location == "":
			return await ctx.send('Please provide location :map:')

		kclient = ksoftapi.Client(os.environ['KSoft_Token'])
		try:
			async with ctx.typing():
				w = await kclient.kumo.basic_weather(location, icon_pack='color')
		except ksoftapi.NoResults:
			await ctx.send('Unable to locate :mag_right:')
		else:
			infos = [['Apparent Temperature', 'apparent_temperature', 1, ' °C'], ['Precipitation Intensity', 'precip_intensity', 1, ' mm/h'], ['Precipitation Probability', 'precip_probability', 100, ' %'], ['Dew Point', 'dew_point', 1, ' °C'], ['Humidity', 'humidity', 100, ' %'], ['Pressure', 'pressure', 1, ' mbar'], ['Wind Speed', 'wind_speed', 1, ' km/h'], ['Cloud Cover', 'cloud_cover', 100, ' %'], ['Visibility', 'visibility', 1, ' km'], ['UV Index', 'uv_index', 1, ''], ['Ozone', 'ozone', 1, '']]
			gmap = f"[🗺](https://www.google.com/maps/search/?api=1&query='{w.location.address}')"
			gmap = gmap.replace("'", "%22");gmap = gmap.replace(" ", "%20")

			info = [f'{gmap} **{w.location.address}**\n']
			for i in infos:
				info.append(f'{i[0]}: `{getattr(w, i[1])*i[2]}{i[3]}`')

			embed = discord.Embed(title=f"{w.summary} {w.temperature}°C", colour=discord.Colour(0xffff66), description='\n'.join(info))
			embed.set_thumbnail(url=w.icon_url)
			embed.set_author(name='Weather:', icon_url=w.icon_url)
			await ctx.send(embed=embed)

		finally:
			await kclient.close()

	@commands.command(name='convert', aliases=['currency'])
	async def currency(self, ctx, value: str="", _from: str="", to: str=""):
		if value=="" or _from=="" or to=="":
			return await ctx.send("Please enter values in proper format\n`~convert [value] [from] [to]`\neg: `~convert 16 usd inr`")

		kclient = ksoftapi.Client(os.environ['KSoft_Token'])
		try:
			async with ctx.typing():
				c = await kclient.kumo.currency_conversion(_from, to, value)
		except (ksoftapi.NoResults, ksoftapi.errors.APIError):
			await ctx.send('Conversion Failed :x:')
		else:
			await ctx.send(f":currency_exchange: Conversion:\n`{value} {_from.upper()}` = `{c.pretty}`")
		finally:
			await kclient.close()

	@commands.command(name='trace', aliases=['ip'])
	async def trace(self, ctx, ip: str=""):
		if ip=="":
			return await ctx.send("Please enter an `IP` address :satellite:")

		kclient = ksoftapi.Client(os.environ['KSoft_Token'])
		try:
			async with ctx.typing():
				info = await kclient.kumo.trace_ip(ip)
		except (ksoftapi.NoResults, ksoftapi.errors.APIError):
			await ctx.send('Unable to locate :x:\nEnter valid IP')
		else:
			details = [['City', 'city'], ['Continent code', 'continent_code'], ['Continent name', 'continent_name'], ['Country code', 'country_code'], ['Country_name', 'country_name'], ['DMA code', 'dma_code'], ['Latitude', 'latitude'], ['Longitude', 'longitude'], ['Postal code', 'postal_code'], ['Region', 'region'], ['Timezone', 'time_zone']]
			description = []
			for i in details:
				description.append(f'{i[0]}: `{getattr(info, i[1])}`')
			description.append(f':map:Map: [GoogleMaps]({info.gmap})')

			embed = discord.Embed(title=":satellite_orbital: IP information:", colour=discord.Colour(0xff00cc), description="\n".join(description))
			embed.set_footer(text=ip, icon_url=ctx.author.avatar_url)
			await ctx.send(embed=embed)
		finally:
			await kclient.close()
	
	@commands.command(name='owner', aliases=['support', 'contact'])
	async def support(self, ctx, *, msg: str = ""):
		if msg == "":
			return await ctx.send("Please enter a message to send towards Bot Owner", delete_after=5.0)

		embed = discord.Embed(colour=discord.Colour(0x5dadec), description=msg)
		embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
		embed.set_footer(text=f"{ctx.guild} : {ctx.guild.id}", icon_url=ctx.guild.icon_url)

		info = await bot.application_info()
		await info.owner.send(embed=embed)
		await ctx.send("Bot owner notified!")


	@listusers.before_invoke
	@teams.before_invoke
	async def ensure_author_voice(self, ctx):
		if not ctx.author.voice:
			await ctx.send("You are not connected to a voice channel :mute:")

class Games(commands.Cog):
	"""Play various Games"""

	def __init__(self, bot):
		self.bot = bot

	@commands.command(name='poll')
	async def quickpoll(self, ctx, question, *options: str):
		"""Create a quick poll[~poll "question" choices]"""
		if len(options) <= 1:
			await ctx.send('You need more than one option to make a poll!')
			return
		if len(options) > 10:
			await ctx.send('You cannot make a poll for more than 10 things!')
			return

		if len(options) == 2 and options[0] == 'yes' and options[1] == 'no':
			reactions = ['✅', '❌']
		else:
			reactions = ['1⃣', '2⃣', '3⃣', '4⃣', '5⃣', '6⃣', '7⃣', '8⃣', '9⃣', '🔟']

		description = []
		for x, option in enumerate(options):
			description += '\n {} {}'.format(reactions[x], option)
		embed = discord.Embed(title=question, description=''.join(description), color=discord.Colour(0xFF355E))
		react_message = await ctx.send(embed=embed)
		for reaction in reactions[:len(options)]:
			await react_message.add_reaction(reaction)
		embed.set_footer(text='Poll ID: {}'.format(react_message.id))
		await react_message.edit(embed=embed)

	@commands.command(name='tally')
	async def tally(self, ctx, id):
		"""Tally the created poll"""
		poll_message = await ctx.message.channel.fetch_message(id)
		if not poll_message.embeds:
			return
		embed = poll_message.embeds[0]
		if poll_message.author != bot.user:
			return
		if not embed.footer.text.startswith('Poll ID:'):
			return
		unformatted_options = [x.strip() for x in embed.description.split('\n')]
		opt_dict = {x[:2]: x[3:] for x in unformatted_options} if unformatted_options[0][0] == '1' \
			else {x[:1]: x[2:] for x in unformatted_options}
		# check if we're using numbers for the poll, or x/checkmark, parse accordingly
		voters = [bot.user.id]  # add the bot's ID to the list of voters to exclude it's votes

		tally = {x: 0 for x in opt_dict.keys()}
		for reaction in poll_message.reactions:
			if reaction.emoji in opt_dict.keys():
				reactors = await reaction.users().flatten()
				for reactor in reactors:
					if reactor.id not in voters:
						tally[reaction.emoji] += 1
						voters.append(reactor.id)

		output = 'Results of the poll for "{}":\n'.format(embed.title) + \
				'\n'.join(['{}: {}'.format(opt_dict[key], tally[key]) for key in tally.keys()])
		await ctx.send(output)

	@commands.command(name='quiz', aliases=['trivia'])
	async def quiz(self, ctx):
		"""Start an interactive quiz game"""
		client = aiopentdb.Client()
		try:
			async with ctx.typing():
				question = await client.fetch_questions(
					amount=1
					# difficulty=aiopentdb.Difficulty.easy
				)
				question = question[0]
				if question.type.value == 'boolean':
					options = ['True', 'False']
				else:
					options = [question.correct_answer]
					options.extend(question.incorrect_answers)
					options = random.sample(options, len(options)) # Shuffle
				answer = options.index(question.correct_answer)

				if len(options) == 2 and options[0] == 'True' and options[1] == 'False':
					reactions = ['✅', '❌']
				else:
					reactions = ['1⃣', '2⃣', '3⃣', '4⃣']

				description = []
				for x, option in enumerate(options):
					description += '\n {} {}'.format(reactions[x], option)

				embed = discord.Embed(title=question.content, description=''.join(description), color=discord.Colour(0xFF9933))
				embed.set_footer(text='Answer using the reactions below⬇')
				quiz_message = await ctx.send(embed=embed)
				for reaction in reactions:
					await quiz_message.add_reaction(reaction)

				def check(reaction, user):
					return user != bot.user and user == ctx.author and (str(reaction.emoji) == '1️⃣' or '2️⃣' or '3️⃣' or '4️⃣' or '✅' or '❌')

				try:
					reaction, user = await bot.wait_for('reaction_add', timeout=10.0, check=check)
				except asyncio.TimeoutError:
					await ctx.send(f"Time's Up! :stopwatch:\nAnswer is **{options[answer]}**")
				else:
					if str(reaction.emoji) == reactions[answer]:
						await ctx.send("Correct answer:sparkles:")
					else:
						await ctx.send(f"Wrong Answer :no_entry_sign:\nAnswer is **{options[answer]}**")
		finally:
			await client.close()

	@commands.command(name='toss', aliases=['flip'])
	async def toss(self, ctx):
		"""Flips a Coin"""
		coin = ['+ heads', '- tails']
		await ctx.send(f"```diff\n{random.choice(coin)}\n```")

	@commands.command(name='fortune', aliases=['cookie', 'quote', 'fact', 'factoid'])
	async def fortune(self, ctx, category='random'):
		"""Fortune Cookie! (You can also specify category[factoid,fortune,people])"""
		categories = ['fortune', 'factoid', 'people']
		if category in categories:
			await ctx.send(f"```fix\n{fortune.get_random_fortune(f'fortunes/{category}')}\n```")
		else:
			await ctx.send(f"```fix\n{fortune.get_random_fortune(f'fortunes/{random.choice(categories)}')}\n```")
	
	@commands.command(name='xkcd', aliases=['comic', 'comics'])
	async def comic(self, ctx):
		"""xkcd Comics"""
		async with ctx.typing():
			c = xkcd.getRandomComic()
		embed = discord.Embed(title=c.getTitle())
		embed.set_image(url=c.getImageLink())
		embed.set_footer(text =c.getAltText())
		await ctx.send(embed=embed)

	@commands.command(name="8ball")
	async def eight_ball(self, ctx, ques=""):
		"""Magic 8Ball"""
		if ques=="":
			await ctx.send("Ask me a question first")
		else:
			choices = ["It is certain.", "It is decidedly so.", "Without a doubt.", "Yes – definitely.", "You may rely on it.", "As I see it, yes.", "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.", "Reply hazy, try again.", "Ask again later.", "Better not tell you now.", "Cannot predict now.", "Concentrate and ask again.", "Don't count on it.", "My reply is no.", "My sources say no.", "Outlook not so good.", "Very doubtful."]
			await ctx.send(f":8ball: says: ||{random.choice(choices)}||")

	@commands.command(name='tictactoe', aliases=['ttt'])
	async def ttt(self, ctx):
		"""Play Tic-Tac-Toe"""
		await tictactoe.play_game(bot, ctx, chance_for_error=0.2) # Win Plausible

	@commands.command(name='meme', aliases=['maymay'])
	async def meme(self, ctx):
		"""Get MayMay"""
		kclient = ksoftapi.Client(os.environ['KSoft_Token'])
		try:
			async with ctx.typing():
				maymay = await kclient.images.random_meme()
		except ksoftapi.NoResults:
			await ctx.send('Error getting maymay :cry:')
		else:
			embed = discord.Embed(title=maymay.title)
			embed.set_image(url=maymay.image_url)
			await ctx.send(embed=embed)

		finally:
			await kclient.close()

	@commands.command(name='rps', aliases=['rockpaperscissors'])
	async def rps(self, ctx):
		"""Play Rock, Paper, Scissors game"""
		def check_win(p, b):
			if p=='🌑':
				return False if b=='📄' else True
			elif p=='📄':
				return False if b=='✂' else True
			else: # p=='✂'
				return False if b=='🌑' else True

		async with ctx.typing():
			reactions = ['🌑', '📄', '✂']
			game_message = await ctx.send("**Rock Paper Scissors**\nChoose your shape:", delete_after=15.0)
			for reaction in reactions:
				await game_message.add_reaction(reaction)
			bot_emoji = random.choice(reactions)
				
		def check(reaction, user):
			return user != bot.user and user == ctx.author and (str(reaction.emoji) == '🌑' or '📄' or '✂')
		try:
			reaction, user = await bot.wait_for('reaction_add', timeout=10.0, check=check)
		except asyncio.TimeoutError:
			await ctx.send(f"Time's Up! :stopwatch:")
		else:
			await ctx.send(f"**:man_in_tuxedo_tone1:\t{reaction.emoji}\n:robot:\t{bot_emoji}**")
			# if conds
			if str(reaction.emoji) == bot_emoji:
				await ctx.send("**It's a Tie :ribbon:**")
			elif check_win(str(reaction.emoji), bot_emoji):
				await ctx.send("**You win :sparkles:**")
			else:
				await ctx.send("**I win :robot:**")	

	@commands.command(name='wumpus')		
	async def _wumpus(self, ctx):
		"""Play Wumpus game"""
		await wumpus.play(bot, ctx)

	@commands.command(name='hangman')
	async def hangman(self, ctx):
		"""Play Hangman"""
		await hangman.play(bot, ctx)

bot = commands.Bot(command_prefix=commands.when_mentioned_or("~"),
					description='Relatively simply awesome bot.',
					case_insensitive=True)

bot.remove_command('help')

@bot.event
async def on_ready():
	print('Logged in as {0} ({0.id})'.format(bot.user))
	print('Bot.....Activated')
	await bot.change_presence(status=discord.Status.idle, activity=discord.Game(name="Nothing"))

@bot.command(name='help', aliases=['h'])
async def help(ctx):
	"""Display help"""
	embed = discord.Embed(title="Relatively simply awesome bot.", colour=discord.Colour(0x7f20a0), description="For more info you can visit [GitHub repo](https://github.com/1Prototype1/HexBot)")

	embed.set_thumbnail(url="https://i.ibb.co/yqgDwNh/hexbot.jpg")
	embed.set_author(name="HexBot Help", url="https://discord.com/oauth2/authorize?client_id=747461870629290035&scope=bot&permissions=24576", icon_url="https://i.ibb.co/yqgDwNh/hexbot.jpg")
	embed.set_footer(text="HexBot by [Prototype]#7731✨")

	embed.add_field(name=":musical_note: Music Commands:", value="```join|connect  - Joins a voice channel\nlyrics        - Get lyrics of current song\nnp            - Displays now playing song\npause         - Pauses the current song\nplay|p <song> - Plays specified song\nqueue|q       - Displays current queue\nresume        - Resumes the paused song\nsave|star     - Save song to your DM\nskip          - Skips current song\nstop|dis      - Stops and disconnects bot\nvolume        - Changes the player's volume```", inline=False)
	embed.add_field(name=":joystick: Game Commands:", value="```8ball         - Magic 8Ball!\n\t<question>\nfortune|quote - Fortune Cookie!\n\t<category>[factoid|fortune|people]\nhangman       - Play Hangman\nmeme|maymay   - Get MayMays\npoll          - Create a quick poll\n\t<question> <choices>\nquiz|trivia   - Start a quiz game\nrps           - Play Rock, Paper, Scissors\ntally         - Tally the created poll\nteams         - Makes random teams(def. 2)\ntoss|flip     - Flips a Coin\nttt           - Play Tic-Tac-Toe!\nwumpus        - Play Wumpus game\nxkcd|comic    - Get random xkcd comics```", inline=False)
	embed.add_field(name=":tools: Misc Commands:", value="```convert       - Currency Converter\n\t<val><from><to>\nclear|cls     - Delete the messages\nhelp          - Display this message\nlist          - Displays the list of\n\t\t\t\tvoice connected users\nping|latency  - Pong!\nsupport       - Contact Bot owner\ntrace <ip>    - Locate IP address\nuser @user    - Get user info\nweather <loc> - Get weather of location```", inline=False)

	try:
		await ctx.send(embed=embed)
	except Exception:
		await ctx.send("I don't have permission to send embeds here :disappointed_relieved:")


bot.add_cog(Music(bot))
bot.add_cog(Games(bot))
bot.add_cog(Misc(bot))
userinfo.setup(bot)
bot.run(os.environ['BOT_Token'])