import asyncio

import discord
import youtube_dl
import keys
import random

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
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=player.title))

    
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

    @commands.command(name='toss')
    async def toss(self, ctx):
    	"""Flips a Coin"""
    	coin = ['+ heads', '- tails']
    	await ctx.send(f"```diff\n{random.choice(coin)}\n```")

    @listusers.before_invoke
    @teams.before_invoke
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

bot = commands.Bot(command_prefix=commands.when_mentioned_or("~"),
                   description='Relatively simple music bot.')

@bot.event
async def on_ready():
    print('Logged in as {0} ({0.id})'.format(bot.user))
    print('Bot.....Activated')
    await bot.change_presence(activity=discord.Game(name="Nothing"))

bot.add_cog(Music(bot))
bot.run(keys.token)