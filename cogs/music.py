import os
import sys
import asyncio
from functools import partial
import itertools
import traceback
import discord
from discord.ext import commands
from async_timeout import timeout
from youtube_dl import YoutubeDL
import ksoftapi

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

			try:
				self._guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
			except discord.errors.ClientException:
				return self.destroy(self._guild)

			embed = discord.Embed(colour=discord.Colour(0x59FFC8), description=f"[{source.title}]({source.web_url})")
			embed.set_thumbnail(url=source.thumbnail)
			embed.set_author(name="Now Playing 🎵", url=f"{source.url}", icon_url="https://i.ibb.co/DGsmTvh/star.gif")
			self.np = await self._channel.send(embed=embed)
			await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=source.title))
			await self.next.wait()

			# Make sure the FFmpeg process is cleaned up.
			source.cleanup()
			self.current = None

			try:
				# We are no longer playing this song...
				await self.np.delete()
				await self.bot.change_presence(status=discord.Status.idle, activity=discord.Game(name="Nothing"))
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
		self.kclient = ksoftapi.Client(os.environ['KSoft_Token'])

	async def cleanup(self, guild):
		try:
			await guild.voice_client.disconnect()
			await self.bot.change_presence(status=discord.Status.idle, activity=discord.Game(name="Nothing"))
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
			return user != self.bot.user and (str(reaction.emoji) == '⏸')
		try:
			reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
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
	async def get_lyrics(self, ctx, *, query: str=""):
		"""Get lyrics of current song"""
		if not query:
			vc = ctx.voice_client
			if not vc or not vc.is_connected():
				return await ctx.send('I\'m not currently connected to voice! :mute:', delete_after=20)
			player = self.get_player(ctx)
			if not player.current:
				return await ctx.send('I\'m not currently playing anything :warning:')
			query = vc.source.title

		try:
			async with ctx.typing():
				results = await self.kclient.music.lyrics(query, limit=1)
		except ksoftapi.NoResults:
			await ctx.send(f'No lyrics found for `{query}`')
		else:
			lyrics = results[0].lyrics
			result = results[0]
			embed = discord.Embed(title=f'{result.name} - {result.artist}', color=discord.Color(0xCCFF00), description=lyrics[:2048])
			embed.set_thumbnail(url=result.album_art)
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

def setup(bot):
	bot.add_cog(Music(bot))