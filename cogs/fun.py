import os
import io
import asyncio
import random
import fortune

import discord
from discord.ext import commands


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = bot.client

    @commands.command(name='ai')
    async def _aichat(self, ctx):
        """Start AI chat mode"""
        def check(m):
            return m.author == ctx.author and not m.content.startswith('~')

        await ctx.send("Let's chat")
        url = os.environ['HexApi'] + 'chatbot'
        while True:
            try:
                params = {'message': 'message'}
                msg = await self.bot.wait_for('message', check=check, timeout=120.0)
            except asyncio.TimeoutError:
                return await ctx.send("Bye :wave:")
            else:
                if 'bye' in msg.content.lower():
                    return await ctx.send("Bye :wave:")

                params['message'] = msg.content
                try:
                    async with ctx.typing():
                        async with self.client.get(url, params=params) as r:
                            response = await r.json()
                            response = response['response']
                except:
                    await ctx.send('Please repeat')
                    continue
                await ctx.send(response)

    @commands.command(name='advice')
    async def advice(self, ctx):
        """Random Advice generator"""
        url = os.environ['HexApi'] + 'advice'
        async with ctx.typing():
            async with self.client.get(url) as r:
                if r.status != 200:
                    return ctx.send('Unable to generate advice :disappointed_relieved')
                data = await r.json()

        await ctx.send(data['slip']['advice'])

    @commands.command(name='ascii')
    async def ascii(self, ctx, image_link: str=""):
        """Ascii art of avatar"""
        if not image_link:
            user = ctx.message.author
            image_link = user.avatar_url_as(size=1024)
        try:
            user = ctx.message.mentions[0]
            image_link = user.avatar_url_as(size=1024)
        except IndexError:
            pass

        url = os.environ['HexApi'] + 'imagetoascii'
        async with self.client.get(url, params={'image': str(image_link)}) as r:
            if r.status != 200:
                return await ctx.send("Failed :x:\nMaybe url is wrong :link:")
            result = await r.text()
            ascii_file = io.StringIO(result.replace('<br>', '\n'))

        em = discord.Embed(color=discord.Color(0xFFFF66))
        em.set_thumbnail(url=image_link)
        await ctx.send(file=discord.File(ascii_file, 'ascii.txt'), embed=em)

    @commands.command(name='bored', aliases=['suggest'])
    async def suggest(self, ctx):
        """Random Suggestions"""
        url = os.environ['HexApi'] + 'activity'
        async with ctx.typing():
            async with self.client.get(url) as r:
                if r.status != 200:
                    return await ctx.send('Unable to get suggestions :disappointed_relieved:')
                data = await r.json()

        desc = []
        desc.append(f"**Type:** `{data['type'].title()}`")
        desc.append(f"**Participants:** `{data['participants']}`")
        desc.append(f"**Price:** `{data['price']}`")
        desc.append(f"**Accessibility:** `{data['accessibility']}`")
        em = discord.Embed(color=discord.Color(0xAAF0D1), description='\n'.join(desc))
        em.set_author(name=data['activity'], url=data['link'])
        em.set_footer(text=f"Suggestion for {ctx.message.author.display_name}", icon_url=ctx.message.author.avatar_url)

        await ctx.send(embed=em)

    @commands.command(name='comic', aliases=['comics', 'comicstrip'])
    async def comic(self, ctx, cid=None):
        """Get comic strip"""
        if not cid:
            return await ctx.send('Please specify comic id\nType `~comic --list` for list.')
        url = os.environ['HexApi'] + 'comic'
        if cid.lower()=='--list':
            params = {'list': 1}
            async with ctx.typing():
                async with self.client.get(url, params=params) as r:
                    if r.status != 200:
                        return await ctx.send('Failed to get comic list :x:')
                    result = await r.json()

            data = [f"**{i}** {comic_name.title()}" for i, comic_name in enumerate(result['comics'], 1) if comic_name in result['featured']]
            em = discord.Embed(color=discord.Color(0xFF5470), title="Comic list:")
            em.description= '**Popular:**\n' + '\n'.join(data)
            em.set_footer(text="Click next for complete list")
            cmsg = await ctx.send(embed=em)

            result = result['comics']
            data = [f"**{i}** {comic_name.title()}" for i, comic_name in enumerate(result, 1)]
            page = 0
            for i in ['⬅', '❌', '➡']:
                await cmsg.add_reaction(i)
            def check(reaction, user):
                return (
                    (user != self.bot.user) 
                    and (str(reaction.emoji) in ['⬅', '➡', '❌']) 
                    and (reaction.message.id == cmsg.id)
                    )
            while True:
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                except asyncio.TimeoutError:
                    await cmsg.clear_reactions()
                    return
                else:
                    if str(reaction.emoji) == '➡':
                        await cmsg.remove_reaction(reaction, user)
                        if page < 0--len(result)//15:
                            page += 1
                    elif str(reaction.emoji) == '⬅':
                        await cmsg.remove_reaction(reaction, user)
                        if page > 1:
                            page -= 1
                    else:
                        await cmsg.delete(delay=0.0)
                        return

                    if page < 1:
                        page = 1
                    start = (page-1) * 15
                    end = start + 15
                    page_data = data[start:end]
                    em.description = '\n'.join(page_data)
                    em.set_footer(text=f"Page {page}/{0--len(result)//15}")
                    await cmsg.edit(embed=em)

        else:
            params = {'id': cid}
            async with ctx.typing():
                async with self.client.get(url, params=params) as r:
                    if r.status != 200:
                        return await ctx.send('Failed to get comic :x:\nMaybe id is invalid\nType `~comic --list` for list.')
                    data = io.BytesIO(await r.read())

            await ctx.send(file=discord.File(data, 'comic.png'))

    @commands.command(name='filter', aliases=['blur', 'invert', 'b&w', 'deepfry', 'sepia', 'pixelate', 'magik', 'jpegify', 'wide', 'snow', 'gay', 'communist'])
    async def filter(self, ctx, arg='', image_link=''):
        """Deepfry avatar"""
        filters = ['blur', 'invert', 'b&w', 'deepfry', 'sepia', 'pixelate', 'magik', 'jpegify', 'wide', 'snow', 'gay', 'communist']
        if arg == '--list':
            return await ctx.send(embed=discord.Embed(title='Filters', description='\n'.join(filters)))
        if arg not in filters:
            return await ctx.send("Invalid filter name\nUse --list for all options")
        
        if not image_link:
            user = ctx.message.author
            image_link = user.avatar_url_as(format='png', size=1024)
        try:
            user = ctx.message.mentions[0]
            image_link = user.avatar_url_as(format='png', size=1024)
        except IndexError:
            pass

        url = os.environ['HexApi'] + 'filter'
        params = {'name': arg, 'image': str(image_link)}
        async with ctx.typing():
            async with self.client.get(url, params=params) as r:
                if r.status != 200:
                    return await ctx.send("Failed :x:\nMaybe url is wrong :link:")
                data = io.BytesIO(await r.read())

        await ctx.send(file=discord.File(data, 'filter.png'))

    @commands.command(name='fortune', aliases=['cookie', 'quote', 'fact', 'factoid'])
    async def fortune(self, ctx, category='random'):
        """Fortune Cookie! (You can also specify category[factoid,fortune,people])"""
        categories = ['fortune', 'factoid', 'people']
        if category in categories:
            await ctx.send(f"```fix\n{fortune.get_random_fortune(f'fortunes/{category}')}\n```")
        else:
            await ctx.send(f"```fix\n{fortune.get_random_fortune(f'fortunes/{random.choice(categories)}')}\n```")

    @commands.command(name='textart', aliases=['au'])
    async def font_generator(self, ctx, *, text: str=""):
        """Generate cool font"""
        if not text:
            return await ctx.send('Please enter text :pager:')
        
        url=f'https://gdcolon.com/tools/gdfont/img/{text}?font=3&color=00ffff'
        async with self.client.get(url) as r:
            if r.status != 200:
                return await ctx.send('Failed to generate textart :x:')
            data = io.BytesIO(await r.read())
        await ctx.send(file=discord.File(data, 'textart.png'))

    @commands.command(name='uselessweb', aliases=['website'])
    async def uselessweb(self, ctx):
        """Get a random website"""
        url = os.environ['HexApi'] + "uselesssites"
        async with ctx.typing():
            async with self.client.get(url) as r:
                if r.status != 200:
                    return await ctx.send('Failed to get website :x:')
                data = await r.json()
        await ctx.send(data['url'])

    @commands.command(name='wallpaper', aliases=['wall'])
    async def _wallpaper(self, ctx, *query: str):
        """Get wallpaper from Unsplash"""
        headers = {'Authorization': os.environ['Unsplash_Token']}
        params = {'count': 1}
        if query:
            params['query'] = query
        else:
            params['count'] = 3
            params['featured'] = 'yes'
        url = 'https://api.unsplash.com/photos/random'
        async with self.client.get(url, params=params, headers=headers) as r:
            if r.status != 200:
                return await ctx.send('Error getting wallpaper :disappointed_relieved:')
            results = await r.json()
        for r in results:
            em = discord.Embed(color=discord.Color(0xFF355E))
            em.set_image(url=r['urls']['raw'])
            em.set_footer(text=f"{r['user']['name']} on Unsplash", icon_url='https://i.ibb.co/f4Xbgkv/lens.png')
            await ctx.send(embed=em)


def setup(bot):
    bot.add_cog(Fun(bot))
