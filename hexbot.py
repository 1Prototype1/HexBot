import asyncio

import discord
import youtube_dl
import os
import random
import fortune
import aiopentdb
import time

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
        self.yt_link = data.get('webpage_url')

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

        try:
            await channel.connect(timeout=5.0)
        except asyncio.TimeoutError:
            await ctx.send(f"I can't join `{channel.name}`:disappointed_relieved:")

    @commands.command(name='play', aliases=['p'])
    async def play(self, ctx, *, url):
        """Plays specified song title"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        embed = discord.Embed(colour=discord.Colour(0x59FFC8), description=f"[{player.title}]({player.yt_link})")
        embed.set_thumbnail(url=player.thumbnail)
        embed.set_author(name="Now Playing 🎵", url=f"{player.url}", icon_url="https://i.ibb.co/DGsmTvh/star.gif")

        await ctx.send(embed=embed)
        # print(player.data)
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=player.title))
        await asyncio.sleep(player.duration)
        await bot.change_presence(status=discord.Status.idle, activity=discord.Game(name="Nothing"))

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
        	await bot.change_presence(status=discord.Status.idle, activity=discord.Game(name="Nothing"))

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
        else:
        	await ctx.send("```diff\n+ Not Playing any Music!\n```")

    @stop.before_invoke
    async def ensure_author_voice(self, ctx):
    	if not ctx.author.voice:
    		await ctx.send("You are not connected to a voice channel.")

    @play.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                try:
                    await ctx.author.voice.channel.connect(timeout=5.0)
                except asyncio.TimeoutError:
                    await ctx.send(f"I can't join `{ctx.author.voice.channel.name}`:disappointed_relieved:")
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

	embed.add_field(name=":musical_note: Music Commands:", value="```join          - Joins a voice channel\npause         - Pauses the current song\nplay|p        - Plays specified song\nresume        - Resumes the paused song\nstop|dis      - Stops and disconnects the bot\nvolume        - Changes the player's volume```", inline=False)
	embed.add_field(name=":joystick: Game Commands:", value="```poll          - Create a quick poll\n\t<question> <choices>\nquiz|trivia   - Start a quiz game\ntally         - Tally the created poll```", inline=False)
	embed.add_field(name=":jigsaw: Misc Commands:", value="```clear|cls     - Delete the messages\nfortune|quote - Fortune Cookie!\n\t<category>[factoid|fortune|people]\nhelp          - Display this message\nlist          - Displays the list of\n\t\t\t\tvoice connected users\nping|latency  - Pong! \nteams         - Makes random teams (def. 2)\ntoss|flip     - Flips a Coin```", inline=False)

	await ctx.send(embed=embed)


bot.add_cog(Music(bot))
bot.add_cog(QuickPoll(bot))
bot.add_cog(Misc(bot))
bot.run(os.environ['BOT_Token'])