import math
import lavalink
import ksoftapi
import discord

from discord.ext import commands

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.kclient = bot.kclient

        if not hasattr(bot, 'lavalink'):
            bot.lavalink = lavalink.Client(bot.user.id)
            bot.lavalink.add_node('localhost', 1616, 'proto', 'in', 'default-node')  # Host, Port, Password, Region, Name
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
            raise commands.CommandInvokeError('Join a voice channel first :loud_sound:')

        if not player.is_connected:
            if not should_connect:
                raise commands.CommandInvokeError('Not connected :mute:')

            permissions = ctx.author.voice.channel.permissions_for(ctx.me)

            if not permissions.connect or not permissions.speak:  # Check user limit too?
                raise commands.CommandInvokeError('I need the `CONNECT` and `SPEAK` permissions. :disappointed_relieved:')

            player.store('channel', ctx.channel.id)
            await self.connect_to(ctx.guild.id, str(ctx.author.voice.channel.id))
        else:
            if int(player.channel_id) != ctx.author.voice.channel.id:
                raise commands.CommandInvokeError('You need to be in my voice channel :loud_sound:')

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
            return await ctx.send('Song not found :x: Please try again :mag_right:')

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
            em.set_thumbnail(url=f"http://i.ytimg.com/vi/{track['info']['identifier']}/hqdefault.jpg")

            em.add_field(name='Channel', value=track['info']['author'])
            if track['info']['isStream']:
                duration = 'Live'
            else:
                duration = lavalink.format_time(track['info']['length']).lstrip('00:')
            em.add_field(name='Duration', value=duration)

            track = lavalink.models.AudioTrack(track, ctx.author.id, recommended=True)
            player.add(requester=ctx.author.id, track=track)

        msg = await ctx.send(embed=em)

        if not player.is_playing:
            await player.play()
            await player.reset_equalizer()
            await msg.delete(delay=1)
            await self.now(ctx)
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=player.current.title))

    @commands.command(name='seek')
    async def seek(self, ctx, seconds=None):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        if not player.is_playing:
            return await ctx.send('Not playing anything :mute:')

        if not seconds:
            return await ctx.send('You need to specify the amount of seconds to seek :fast_forward:')
        try:
            track_time = player.position + int(seconds) * 1000
            await player.seek(track_time)
        except ValueError:
            return await ctx.send('Specify valid amount of seconds :clock3:')

        await ctx.send(f'Moved track to **{lavalink.format_time(track_time)}**')

    @commands.command(name='skip', aliases=['forceskip', 'fs', 'next'])
    async def skip(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        if not player.is_playing:
            return await ctx.send('Not playing anything :mute:')

        await ctx.send('⏭ | Skipped.')
        await player.skip()

    @commands.command(name='now', aliases=['current', 'currentsong', 'playing', 'np'])
    async def now(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        song = 'Nothing'

        if player.current:
            if player.current.stream:
                dur = 'LIVE'
                pos = ''
                count = total = 1
            else:
                count = player.position
                pos = lavalink.format_time(count)
                total = player.current.duration
                dur = lavalink.format_time(total)
                if pos == dur: # When called immediatly after enqueue
                    count = 0
                    pos = '00:00:00'
                dur = dur.lstrip('00:')
                pos = pos[-len(dur):]
            bar_len = 30 # bar length
            filled_len = int(bar_len * count // float(total))
            bar = '═' * filled_len + '◈' + '─' * (bar_len - filled_len)
            song = f'[{player.current.title}]({player.current.uri})\n`{pos} {bar} {dur}`'

            em = discord.Embed(colour=discord.Colour(0x59FFC8), description=song)
            em.set_author(name="Now Playing 🎵", icon_url="https://i.ibb.co/DGsmTvh/star.gif")
            em.set_thumbnail(url=f"http://i.ytimg.com/vi/{player.current.identifier}/hqdefault.jpg")
            requester = ctx.guild.get_member(player.current.requester)
            em.set_footer(text=f"Requested by: {requester}", icon_url=requester.avatar_url)

            await ctx.send(embed=em)
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=player.current.title))
        else:
            await ctx.send('Not playing anything :mute:')

    @commands.command(name='save', aliases=['star'])
    async def savetodm(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if player.current:
            if player.current.stream:
                dur = 'Live'
            else:
                dur = lavalink.format_time(player.current.duration).lstrip('00:')
            song = f'[{player.current.title}]({player.current.uri})'
            em = discord.Embed(colour=discord.Colour(0x59FFC8), description=song)
            em.set_author(name="Now Playing 🎵", icon_url="https://i.ibb.co/DGsmTvh/star.gif")
            em.set_thumbnail(url=f"http://i.ytimg.com/vi/{player.current.identifier}/hqdefault.jpg")
            em.add_field(name='Channel', value=player.current.author)
            em.add_field(name='Duration', value=dur)

            user = ctx.author
            await user.send(embed=em)
            await ctx.send(f"Current song has been sent to you {ctx.author.mention} :floppy_disk:")
        else:
            await ctx.send('Not playing anything :mute:')


    @commands.command(name='queue', aliases=['q', 'playlist'])
    async def queue(self, ctx, page: int=1):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        if not player.queue:
            return await ctx.send('Queue empty! Why not queue something? :cd:')

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
            return await ctx.send('Not playing anything :mute:')

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
            return await ctx.send('Not playing anything :mute:')

        player.shuffle = not player.shuffle

        await ctx.send('🔀 | Shuffle ' + ('enabled' if player.shuffle else 'disabled'))

    @commands.command(name='repeat')
    async def repeat(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        if not player.is_playing:
            return await ctx.send('Not playing anything :mute:')

        player.repeat = not player.repeat

        await ctx.send('🔁 | Repeat ' + ('enabled' if player.repeat else 'disabled'))

    @commands.command(name='remove', aliases=['dequeue', 'pop'])
    async def remove(self, ctx, index: int):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        if not player.queue:
            return await ctx.send('Nothing queued :cd:')

        if index > len(player.queue) or index < 1:
            return await ctx.send('Index has to be >=1 and <=queue size')

        index = index - 1
        removed = player.queue.pop(index)

        await ctx.send('Removed **' + removed.title + '** from the queue.')

    @commands.command(name='disconnect', aliases=['dis', 'stop', 'leave'])
    async def disconnect(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        if not ctx.author.voice or (player.is_connected and ctx.author.voice.channel.id != int(player.channel_id)):
            return await ctx.send('You\'re not in my voice channel :loud_sound:')

        if not player.is_connected:
            return await ctx.send('Not connected :mute:')

        player.queue.clear()
        # Stop the current track so Lavalink consumes less resources.
        await player.stop()
        # Disconnect from the voice channel.
        await self.connect_to(ctx.guild.id, None)
        await ctx.send('Disconnected :mute:')
        await self.bot.change_presence(status=discord.Status.idle, activity=discord.Game(name="Nothing"))

    @commands.command(name='lyrics', aliases=['ly'])
    async def get_lyrics(self, ctx, *, query: str=""):
        """Get lyrics of current song"""
        if not query:
            player = self.bot.lavalink.player_manager.get(ctx.guild.id)

            if not player.is_playing:
                return await ctx.send('I\'m not currently playing anything :warning:')
            query = player.current.title

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

    @commands.command(name='equalizer', aliases=['eq'])
    async def equalizer(self, ctx, *args):
        """Equalizer"""
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        if len(args) == 0:
            await ctx.send('Specify `band gain` or `preset` to change frequencies :control_knobs:')
        elif len(args) == 1:
            presets ={
                        'reset': 'Default',
                        'bassboost': [0.08, 0.12, 0.2, 0.18, 0.15, 0.1, 0.05, 0.0, 0.02, -0.04, -0.06, -0.08, -0.10, -0.12, -0.14], 
                        'jazz': [-0.13, -0.11, -0.1, -0.1, 0.14, 0.2, -0.18, 0.0, 0.24, 0.22, 0.2, 0.0, 0.0, 0.0, 0.0], 
                        'pop': [-0.02, -0.01, 0.08, 0.1, 0.15, 0.1, 0.03, -0.02, -0.035, -0.05, -0.05, -0.05, -0.05, -0.05, -0.05], 
                        'treble': [-0.1, -0.12, -0.12, -0.12, -0.08, -0.04, 0.0, 0.3, 0.34, 0.4, 0.35, 0.3, 0.3, 0.3, 0.3]
                    }

            preset = args[0].lower()
            if preset in ['reset', 'default']:
                await player.reset_equalizer()
            elif preset in presets:
                gain_list = enumerate(presets[preset])
                await player.set_gains(*gain_list)
            
            elif preset == '--list':
                em = discord.Embed(title=':control_knobs: EQ presets:', color=discord.Color(0xFF6EFF), description='\n'.join(presets.keys()))
                return await ctx.send(embed=em)
            else:
                return await ctx.send('Invalid preset specified :control_knobs:\nType `~eq --list` for all presets')
        elif len(args) == 2:
            try:
                band = int(args[0])
                gain = float(args[1])
                await player.set_gain(band, gain)
            except ValueError:
                return await ctx.send('Specify valid `band gain` values :control_knobs:')
        else:
            return await ctx.send('Specify `band gain` or `preset` :control_knobs:')
        # Print final EQ settings
        eq_frequencies = [f"`{gain}`" for gain in player.equalizer]
        await ctx.send(":level_slider: Current Values:\n" + ' '.join(eq_frequencies))


def setup(bot):
    bot.add_cog(Music(bot))