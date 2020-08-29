import discord
from discord.ext import commands
import asyncio
import itertools
import sys
import traceback
from async_timeout import timeout
from functools import partial
from youtube_dl import YoutubeDL

import os
import random
import fortune
import aiopentdb
import time


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
    async def create_source(cls, ctx, search: str, *, loop, download=False):
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

        to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=False)
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
        self.volume = .1
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
                await ctx.send("You are not connected to a voice channel.")
                # raise InvalidVoiceChannel('No channel to join. Please either specify a valid channel or join one.')

        vc = ctx.voice_client

        if vc:
            if vc.channel.id == channel.id:
                return
            try:
                await vc.move_to(channel)
            except asyncio.TimeoutError:
                await ctx.send(f"I can't join `{ctx.author.voice.channel.name}`:disappointed_relieved:")
                raise VoiceConnectionError(f'Moving to channel: <{channel}> timed out.')
        else:
            try:
                await channel.connect(timeout=5.0)
            except asyncio.TimeoutError:
                await ctx.send(f"I can't join `{ctx.author.voice.channel.name}`:disappointed_relieved:")
                raise VoiceConnectionError(f'Connecting to channel: <{channel}> timed out.')

        await ctx.send(f'Connected to: **{channel}**', delete_after=20)

    @commands.command(name='play', aliases=['sing', 'p'])
    async def play_(self, ctx, *, search: str):
        """Request a song and add it to the queue.
        This command attempts to join a valid voice channel if the bot is not already in one.
        Uses YTDL to automatically search and retrieve a song.
        Parameters
        ------------
        search: str [Required]
            The song to search and retrieve using YTDL. This could be a simple search, an ID or URL.
        """
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
            return await ctx.send('I\'m not currently playing anything!', delete_after=20)
        elif vc.is_paused():
            return

        vc.pause()
        await ctx.message.add_reaction('⏸')

    @commands.command(name='resume')
    async def resume_(self, ctx):
        """Resume the currently paused song."""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('I\'m not currently playing anything!', delete_after=20)
        elif not vc.is_paused():
            return

        vc.resume()
        await ctx.message.add_reaction('▶')

    @commands.command(name='skip', aliases=['next'])
    async def skip_(self, ctx):
        """Skip the song."""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('I\'m not currently playing anything!', delete_after=20)

        if vc.is_paused():
            pass
        elif not vc.is_playing():
            return

        vc.stop()
        await ctx.send(f'**`{ctx.author}`**: Skipped the song!')

    @commands.command(name='queue', aliases=['q', 'playlist'])
    async def queue_info(self, ctx):
        """Retrieve a basic queue of upcoming songs."""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('I\'m not currently connected to voice!', delete_after=20)

        player = self.get_player(ctx)
        if player.queue.empty():
            return await ctx.send('There are currently no more queued songs.')

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
            return await ctx.send('I\'m not currently connected to voice!', delete_after=20)

        player = self.get_player(ctx)
        if not player.current:
            return await ctx.send('I\'m not currently playing anything!')

        try:
            # Remove our previous now_playing message.
            await player.np.delete()
        except discord.HTTPException:
            pass

        embed = discord.Embed(colour=discord.Colour(0x59FFC8), description=f"[{vc.source.title}]({vc.source.web_url})")
        embed.set_thumbnail(url=vc.source.thumbnail)
        embed.set_author(name="Now Playing 🎵", url=f"{vc.source.url}", icon_url="https://i.ibb.co/DGsmTvh/star.gif")
        embed.set_footer(text=f"Requested by: {vc.source.requester}")
        player.np = await ctx.send(embed=embed)

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
            return await ctx.send('I\'m not currently connected to voice!', delete_after=20)

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

	@commands.command(name='clear', aliases=['cls'])
	async def clear(self, ctx, limit=20):
		"""Delete the messages sent in current text-channel"""
		if limit<1 and limit>100: limit = 20
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
		await message.edit(content=f"Pong!  \nPing: `{int(ping)}ms`\nLatency: `{int(bot.latency*1000)}ms`")

	@listusers.before_invoke
	@teams.before_invoke
	async def ensure_author_voice(self, ctx):
		if not ctx.author.voice:
			await ctx.send("You are not connected to a voice channel.")

class QuickPoll(commands.Cog):
    """QuickPoll"""

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
                questions = await client.fetch_questions(
                    amount=1
                    # difficulty=aiopentdb.Difficulty.easy
                )
                question = questions[0]
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

bot = commands.Bot(command_prefix=commands.when_mentioned_or("~"),
                   description='Relatively simply awesome bot.',
                   case_insensitive=True)

bot.remove_command('help')

@bot.event
async def on_ready():
    print('Logged in as {0} ({0.id})'.format(bot.user))
    print('Bot.....Activated')
    await bot.change_presence(status=discord.Status.idle, activity=discord.Game(name="Nothing"))

@bot.command()
async def help(ctx):
	"""Display help"""
	embed = discord.Embed(title="Relatively simply awesome bot.", colour=discord.Colour(0x7f20a0), description="For more info you can visit [GitHub repo](https://github.com/1Prototype1/HexBot)")

	embed.set_thumbnail(url="https://i.ibb.co/yqgDwNh/hexbot.jpg")
	embed.set_author(name="HexBot Help", url="https://discord.com/oauth2/authorize?client_id=747461870629290035&scope=bot", icon_url="https://i.ibb.co/yqgDwNh/hexbot.jpg")
	embed.set_footer(text="HexBot by [Prototype]#7731✨")

	embed.add_field(name=":musical_note: Music Commands:", value="```join|connect  - Joins a voice channel\nnp            - Displays now playing song\npause         - Pauses the current song\nplay|p        - Plays specified song\nqueue|q       - Displays current queue\nresume        - Resumes the paused song\nskip          - Skips current song\nstop|dis      - Stops and disconnects bot\nvolume        - Changes the player's volume```", inline=False)
	embed.add_field(name=":joystick: Game Commands:", value="```poll          - Create a quick poll\n\t<question> <choices>\nquiz|trivia   - Start a quiz game\ntally         - Tally the created poll```", inline=False)
	embed.add_field(name=":jigsaw: Misc Commands:", value="```clear|cls     - Delete the messages\nfortune|quote - Fortune Cookie!\n\t<category>[factoid|fortune|people]\nhelp          - Display this message\nlist          - Displays the list of\n\t\t\t\tvoice connected users\nping|latency  - Pong! \nteams         - Makes random teams(def. 2)\ntoss|flip     - Flips a Coin```", inline=False)

	try:
		await ctx.send(embed=embed)
	except Exception as e:
		await ctx.send("I don't have permission to send embeds here")



bot.add_cog(Music(bot))
bot.add_cog(QuickPoll(bot))
bot.add_cog(Misc(bot))
bot.run(os.environ['BOT_Token'])