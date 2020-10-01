import math
import re
import lavalink
import ksoftapi
import discord

from discord.ext import commands

time_rx = re.compile('[0-9]+')
def mstomin(input):
	return f"{((input /1000) / 60):.2f}"


class Music(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

		if not hasattr(bot, 'lavalink'):
			bot.lavalink = lavalink.Client(bot.user.id)
			bot.lavalink.add_node('localhost', 1616, 'proto', 'us', 'default-node')  # Host, Port, Password, Region, Name
			bot.add_listener(bot.lavalink.voice_update_handler, 'on_socket_response')

		lavalink.add_event_hook(self.track_hook)

	def cog_unload(self):
		""" Cog unload handler. This removes any event hooks that were registered. """
		self.bot.lavalink._event_hooks.clear()

	async def cog_command_error(self, ctx, error):
		if isinstance(error, commands.CommandInvokeError):
			await ctx.send(error.original)

	async def track_hook(self, event):
		if isinstance(event, lavalink.events.QueueEndEvent):
			guild_id = int(event.player.guild_id)
			await self.connect_to(guild_id, None)
			await self.bot.change_presence(status=discord.Status.idle, activity=discord.Game(name="Nothing"))

	async def cog_before_invoke(self, ctx):
		""" Command before-invoke handler. """
		guild_check = ctx.guild is not None

		if guild_check:
			await self.ensure_voice(ctx)
			#  Ensure that the bot and command author share a mutual voicechannel.

		return guild_check

	async def ensure_voice(self, ctx):
		""" This check ensures that the bot and command author are in the same voicechannel. """
		player = self.bot.lavalink.player_manager.create(ctx.guild.id, endpoint=str(ctx.guild.region))
		should_connect = ctx.command.name in ('play',)

		if not ctx.author.voice or not ctx.author.voice.channel:
			raise commands.CommandInvokeError('Join a voicechannel first :warning:')

		if not player.is_connected:
			if not should_connect:
				raise commands.CommandInvokeError('Not connected.')

			permissions = ctx.author.voice.channel.permissions_for(ctx.me)

			if not permissions.connect or not permissions.speak:  # Check user limit too?
				raise commands.CommandInvokeError('I need the `CONNECT` and `SPEAK` permissions. :disappointed_relieved:')

			player.store('channel', ctx.channel.id)
			await self.connect_to(ctx.guild.id, str(ctx.author.voice.channel.id))
		else:
			if int(player.channel_id) != ctx.author.voice.channel.id:
				raise commands.CommandInvokeError('You need to be in my voicechannel.')

	async def connect_to(self, guild_id: int, channel_id: str):
		""" Connects to the given voicechannel ID. A channel_id of `None` means disconnect. """
		ws = self.bot._connection._get_websocket(guild_id)
		await ws.voice_state(str(guild_id), channel_id)

	@commands.command(name='play', aliases=['p', 'sing'])
	async def play(self, ctx, *, query):
		player = self.bot.lavalink.player_manager.get(ctx.guild.id)

		query = query.strip('<>')

		if not query.startswith('http'):
			query = f'ytsearch:{query}'

		results = await player.node.get_tracks(query)

		if not results or not results['tracks']:
			return await ctx.send('Song not found :mag_right:')

		em = discord.Embed(colour=discord.Colour(0x59FFC8))        

		if results['loadType'] == 'PLAYLIST_LOADED':
			tracks = results['tracks']

			for track in tracks:
				# Add all of the tracks from the playlist to the queue.
				player.add(requester=ctx.author.id, track=track)

			em.title = 'Playlist Enqueued!'
			em.description = f'{results["playlistInfo"]["name"]} - {len(tracks)} tracks'
		else:
			track = results['tracks'][0]
			em.title = 'Track Enqueued'
			em.description = f'[{track["info"]["title"]}]({track["info"]["uri"]})'

			track = lavalink.models.AudioTrack(track, ctx.author.id, recommended=True)
			player.add(requester=ctx.author.id, track=track)

		await ctx.send(embed=em)

		if not player.is_playing:
			await player.play()
			player.ctx = ctx
			await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=player.current.title))
			await self.now(ctx)

	@commands.command(name='seek')
	async def seek(self, ctx, time):
		player = self.bot.lavalink.player_manager.get(ctx.guild.id)

		if not player.is_playing:
			return await ctx.send('Not playing.')

		pos = '+'
		if time.startswith('-'):
			pos = '-'

		seconds = time_rx.search(time)

		if not seconds:
			return await ctx.send('You need to specify the amount of seconds to skip!')

		seconds = int(seconds.group()) * 1000

		if pos == '-':
			seconds = seconds * -1

		track_time = player.position + seconds

		await player.seek(track_time)

		await ctx.send(f'Moved track to **{lavalink.format_time(track_time)}**')

	@commands.command(name='skip', aliases=['forceskip', 'fs', 'next'])
	async def skip(self, ctx):
		player = self.bot.lavalink.player_manager.get(ctx.guild.id)

		if not player.is_playing:
			return await ctx.send('Not playing.')

		await ctx.send('⏭ | Skipped.')
		await player.skip()

	# @commands.command()
	# async def stop(self, ctx):
	# 	player = self.bot.lavalink.player_manager.get(ctx.guild.id)

	# 	if not player.is_playing:
	# 		return await ctx.send('Not playing.')

	# 	player.queue.clear()
	# 	await player.stop()
	# 	await ctx.send('⏹ | Stopped.')
	# 	await self.bot.change_presence(status=discord.Status.idle, activity=discord.Game(name="Nothing"))

	@commands.command(name='now', aliases=['current', 'currentsong', 'playing', 'np'])
	async def now(self, ctx):
		player = self.bot.lavalink.player_manager.get(ctx.guild.id)
		song = 'Nothing'

		if player.current:
			pos = lavalink.format_time(player.position)
			if player.current.stream:
				dur = 'LIVE'
			else:
				dur = lavalink.format_time(player.current.duration)
			song = f'[{player.current.title}]({player.current.uri})\n`{pos}/{dur}`'

		em = discord.Embed(colour=discord.Colour(0x59FFC8), description=song)
		em.set_author(name="Now Playing 🎵", icon_url="https://i.ibb.co/DGsmTvh/star.gif")
		em.set_thumbnail(url=f"http://i.ytimg.com/vi/{player.current.identifier}/hqdefault.jpg")
		requester = ctx.guild.get_member(player.current.requester)
		em.set_footer(text=f"Requested by: {requester}", icon_url=requester.avatar_url)

		await ctx.send(embed=em)
		await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=player.current.title))

	@commands.command(name='queue', aliases=['q', 'playlist'])
	async def queue(self, ctx, page: int=1):
		player = self.bot.lavalink.player_manager.get(ctx.guild.id)

		if not player.queue:
			return await ctx.send('There\'s nothing in the queue! Why not queue something?')

		items_per_page = 10
		pages = math.ceil(len(player.queue) / items_per_page)

		start = (page - 1) * items_per_page
		end = start + items_per_page

		queue_list = ''

		for i, track in enumerate(player.queue[start:end], start=start):
			queue_list += f'`{i + 1}.` [**{track.title}**]({track.uri})\n'

		embed = discord.Embed(colour=ctx.guild.me.top_role.colour,
							  description=f'**{len(player.queue)} tracks**\n\n{queue_list}')
		embed.set_footer(text=f'Viewing page {page}/{pages}')
		await ctx.send(embed=embed)

	@commands.command(name='pause', aliases=['resume'])
	async def pause(self, ctx):
		player = self.bot.lavalink.player_manager.get(ctx.guild.id)

		if not player.is_playing:
			return await ctx.send('Not playing.')

		if player.paused:
			await player.set_pause(False)
			await ctx.message.add_reaction('▶')
		else:
			await player.set_pause(True)
			await ctx.message.add_reaction('⏸')

	@commands.command(name='volume', aliases=['vol'])
	async def volume(self, ctx, volume: int=None):
		player = self.bot.lavalink.player_manager.get(ctx.guild.id)

		if not volume:
			return await ctx.send(f'🔈 | {player.volume}%')

		await player.set_volume(volume)
		await ctx.send(f'🔈 | Set to {player.volume}%')

	@commands.command(name='shuffle')
	async def shuffle(self, ctx):
		player = self.bot.lavalink.player_manager.get(ctx.guild.id)

		if not player.is_playing:
			return await ctx.send('Nothing playing.')

		player.shuffle = not player.shuffle

		await ctx.send('🔀 | Shuffle ' + ('enabled' if player.shuffle else 'disabled'))

	@commands.command(name='repeat')
	async def repeat(self, ctx):
		player = self.bot.lavalink.player_manager.get(ctx.guild.id)

		if not player.is_playing:
			return await ctx.send('Nothing playing.')

		player.repeat = not player.repeat

		await ctx.send('🔁 | Repeat ' + ('enabled' if player.repeat else 'disabled'))

	@commands.command(name='remove', aliases=['dequeue', 'pop'])
	async def remove(self, ctx, index: int):
		player = self.bot.lavalink.player_manager.get(ctx.guild.id)

		if not player.queue:
			return await ctx.send('Nothing queued.')

		if index > len(player.queue) or index < 1:
			return await ctx.send('Index has to be >=1 and <=queue size')

		index = index - 1
		removed = player.queue.pop(index)

		await ctx.send('Removed **' + removed.title + '** from the queue.')

	@commands.command(name='disconnect', aliases=['dis', 'stop', 'leave'])
	async def disconnect(self, ctx):
		player = self.bot.lavalink.player_manager.get(ctx.guild.id)

		if not ctx.author.voice or (player.is_connected and ctx.author.voice.channel.id != int(player.channel_id)):
			return await ctx.send('You\'re not in my voicechannel!')

		if not player.is_connected:
			return await ctx.send('Not connected.')

		player.queue.clear()
		# Stop the current track so Lavalink consumes less resources.
		await player.stop()
		# Disconnect from the voice channel.
		await self.connect_to(ctx.guild.id, None)
		await ctx.send('Disconnected :mute:')
		await self.bot.change_presence(status=discord.Status.idle, activity=discord.Game(name="Nothing"))


def setup(bot):
	bot.add_cog(Music(bot))
