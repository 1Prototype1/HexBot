import asyncio

import discord
import youtube_dl
import os
import random
import fortune

from discord.ext import commands

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.1):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')
        self.thumbnail = data.get('thumbnail')
        self.duration = data.get('duration')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins a voice channel"""

        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()

    @commands.command(name='play', aliases=['p'])
    async def play(self, ctx, *, url):
        """Plays specified song title"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send(f'```json\n\"Now playing: {player.title}\"\n```')
        await ctx.send(player.thumbnail)
        # print(player.data)
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=player.title))
        await asyncio.sleep(player.duration)
        await bot.change_presence(status=discord.Status.idle, activity=discord.Game(name="Nothing"))
    
    @commands.command()
    async def stream(self, ctx, *, url):
        """Streams from a url (same as play, but doesn't predownload)"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('Now playing: {}'.format(player.title))

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

        if ctx.voice_client is None:
        	await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send("Changed volume to {}%".format(volume))

    @commands.command(name='stop', aliases=['dis', 'disconnect'])
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""
        if ctx.voice_client is None:
            await ctx.send("Not connected to a voice channel.")
        else:
        	if ctx.voice_client.is_playing():
        		ctx.voice_client.stop()
        	await ctx.voice_client.disconnect()
        	await bot.change_presence(activity=discord.Game(name="Nothing"))

    @commands.command(name='pause')
    async def pause(self, ctx):
        """Pauses the currently playing song."""
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.message.add_reaction('⏸')
        else:
        	await ctx.send("```diff\n- Not playing any Music!\n```")

    @commands.command(name='resume')
    async def resume(self, ctx):
        """Resumes a currently paused song."""
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.message.add_reaction('▶')
        elif ctx.voice_client.is_playing():
        	await ctx.send("```diff\n+ Already Playing Music!\n```")

    @stop.before_invoke
    async def ensure_author_voice(self, ctx):
    	if not ctx.author.voice:
    		await ctx.send("You are not connected to a voice channel.")

    @play.before_invoke
    @stream.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()

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
        embed = discord.Embed(title=question, description=''.join(description), color=5898184)
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

# Development Area
    @commands.command(name='quiz', aliases=['trivia'])
    async def quiz(self, ctx):
        answer = 'three'
        reactions = ['1️⃣', '2️⃣', '3️⃣', '4️⃣']
        question = "This is a Question?"
        options = ['one', 'two', 'three', 'four']
        options = random.sample(options, len(options)) # Shuffle
        answer = options.index(answer) # Find answer index in shuffled list

        description = []
        for x, option in enumerate(options):
            description += '\n {} {}'.format(reactions[x], option)

        embed = discord.Embed(title=question, description=''.join(description), color=5898184)
        quiz_message = await ctx.send(embed=embed)
        for reaction in reactions:
	        await quiz_message.add_reaction(reaction)

        def check(reaction, user):
            return user != bot.user and user == ctx.author and (str(reaction.emoji) == '1️⃣' or '2️⃣' or '3️⃣' or '4️⃣')

        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=10.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("⏱Time's Up!")
        else:
            if str(reaction.emoji) == reactions[answer]:
                await ctx.send("Correct answer✨")
            else:
                await ctx.send("Wrong Answer🚫")

# END

bot = commands.Bot(command_prefix=commands.when_mentioned_or("~"),
                   description='Relatively simple music bot.')

@bot.event
async def on_ready():
    print('Logged in as {0} ({0.id})'.format(bot.user))
    print('Bot.....Activated')
    await bot.change_presence(status=discord.Status.idle, activity=discord.Game(name="Nothing"))

bot.add_cog(Music(bot))
bot.add_cog(QuickPoll(bot))
bot.add_cog(Misc(bot))
bot.run(os.environ['BOT_Token'])