import os
import io
import xkcd
import ksoftapi

import discord
from discord.ext import commands

class Meme(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = bot.client
        self.kclient = bot.kclient

    @commands.command(name='bill')
    async def _bill(self, ctx, name=''):
        """Bill meme generator"""
        url = os.environ['HexApi'] + 'bill'
        params = {'default': 1}
        try:
            name = ctx.message.mentions[0].display_name
        except IndexError:
            pass
        if name:
            params['name'] = name

        async with ctx.typing():
            async with self.client.get(url, params=params) as r:
                if r.status != 200:
                    return ctx.send('Unable to generate bill :disappointed_relieved')
                data = io.BytesIO(await r.read())

        await ctx.send(file=discord.File(data, 'bill.png'))

    @commands.command(name='joke', aliases=['pun', 'riddle', 'dark', 'geek'])
    async def _joke(self, ctx):
        """Tell a joke"""
        url = os.environ['HexApi'] + 'joke'
        params = {'category': 'Any'}
        if ctx.message.content.strip()[1:5] in ['pun', 'dark', 'geek']:
            if ctx.message.content.strip()[1:5].lower() == 'geek':
                params['category'] = 'Programming'
            else:
                params['category'] = ctx.message.content.strip()[1:5]
        elif 'riddle' in ctx.message.content:
            params['type'] = 'twopart'

        async with ctx.typing():
            async with self.client.get(url, params=params) as r:
                if r.status != 200:
                    return await ctx.send("Could not get joke for you :disappointed_relieved:")
                joke = await r.json()

        if joke["type"] == "single":
            await ctx.send(joke['joke'])
        else:
            await ctx.send(f"{joke['setup']}\n{joke['delivery']}")

    @commands.command(name='drake')
    async def drake(self, ctx, *, text: str=''):
        """Drake meme generator"""
        text = text.split(',')
        if len(text) != 2:
            return await ctx.send('Please specify `,` separated two sentences :page_facing_up:')
        url = os.environ['HexApi'] + 'drake'
        params = {'top': text[0], 'bottom': text[1]}
        async with ctx.typing():
            async with self.client.get(url, params=params) as r:
                if r.status != 200:
                    return await ctx.send('Failed to generate meme :disappointed_relieved:')
                data = io.BytesIO(await r.read())
        await ctx.send(file=discord.File(data, 'drake.png'))

    @commands.command(name='fml')
    async def fml(self, ctx):
        """FML generators"""
        url = os.environ['HexApi'] + 'fml'
        async with ctx.typing():
            async with self.client.get(url) as r:
                if r.status != 200:
                    return await ctx.send('Failed to get FML :disappointed_relieved:')
                data = await r.json()
        await ctx.send(f"{data['text']} :person_facepalming_tone1:")

    @commands.command(name='meme', aliases=['maymay'])
    async def meme(self, ctx):
        """Get MayMay"""
        try:
            async with ctx.typing():
                maymay = await self.kclient.images.random_meme()
        except ksoftapi.NoResults:
            await ctx.send('Error getting maymay :cry:')
        else:
            embed = discord.Embed(title=maymay.title)
            embed.set_image(url=maymay.image_url)
            await ctx.send(embed=embed)

    @commands.command(name='insult', aliases=['roast'])
    async def insult(self, ctx):
        """Insult generator"""
        url = os.environ['HexApi'] + 'insult'
        try:
            user = ctx.message.mentions[0]
        except IndexError:
            return await ctx.send("Mention the person you want to insult")
        async with ctx.typing():
            async with self.client.get(url) as r:
                if r.status != 200:
                    return await ctx.send('Failed to insult :disappointed_relieved:')
                data = await r.json()

        insult_text = '. '.join(map(lambda s: s.strip().capitalize(), data['insult'].split('.')))
        await ctx.send(f"{user.mention} {insult_text}")

    @commands.command(name='tinder', aliases=['match'])
    async def tinder(self, ctx):
        """Tinder: It's a Match!"""
        try:
            user1 = ctx.message.mentions[0].avatar_url_as(size=1024)
            user2 = ctx.message.mentions[1].avatar_url_as(size=1024)
        except IndexError:
            return await ctx.send('Mention two users to match :heart:')

        url = os.environ['HexApi'] + f"tinder?image1={user1}&image2={user2}"
        async with ctx.typing():
            async with self.client.get(url) as r:
                if r.status != 200:
                    return await ctx.send('Failed to match :broken_heart:')
                data = io.BytesIO(await r.read())
        await ctx.send(file=discord.File(data, 'tinder.png'))

    @commands.command(name='trigger')
    async def trigger(self, ctx):
        """Trigger a user"""
        try:
            user = ctx.message.mentions[0]
        except IndexError:
            return await ctx.send("Mention the person you want to trigger")

        url = os.environ['HexApi'] + f"trigger?image={user.avatar_url_as(size=1024)}"
        async with ctx.typing():
            async with self.client.get(url) as r:
                if r.status != 200:
                    return await ctx.send('Failed to trigger :x:')
                data = io.BytesIO(await r.read())
        await ctx.send(file=discord.File(data, 'trigger.gif'))

    @commands.command(name='xkcd')
    async def _xkcd(self, ctx):
        """xkcd Comics"""
        async with ctx.typing():
            c = xkcd.getRandomComic()
        embed = discord.Embed(title=c.getTitle())
        embed.set_image(url=c.getImageLink())
        embed.set_footer(text =c.getAltText())
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Meme(bot))
