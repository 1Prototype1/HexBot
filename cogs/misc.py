import json

import discord
from discord.ext import commands

class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='clear', aliases=['cls'])
    async def clear(self, ctx, limit=20):
        """Delete the messages sent in current text-channel"""
        if 1>limit>100:
            limit = 20
        try:
            await ctx.message.channel.purge(limit=limit)
        except discord.Forbidden:
            await ctx.send("I don't have permission to `Manage Messages`:disappointed_relieved:")

    @commands.command(name='help', aliases=['h'])
    async def help(self, ctx, arg: str=''):
        """Display help"""
        embed = discord.Embed(title="Relatively simply awesome bot.", colour=discord.Colour(0x7f20a0))

        avatar_url = str(self.bot.user.avatar_url)
        embed.set_thumbnail(url=avatar_url)
        embed.set_author(name="HexBot Help", url="https://discord.com/oauth2/authorize?client_id=747461870629290035&scope=bot&permissions=57344", icon_url=avatar_url)
        embed.set_footer(text="HexBot by [Prototype]#7731✨")

        if arg.strip().lower() == '-a':
            # Full version
            embed.description = 'My prefix is `~`'
            with open('help.json', 'r') as help_file:
                data = json.load(help_file)
            data = data['full']
            for key in data:
                value = '\n'.join(x for x in data[key])
                embed.add_field(name=key, value=f"```{value}```", inline=False)
        else:
            # Short version
            embed.description = 'My prefix is `~`\nType `~help -a` for detailed help.'
            with open('help.json', 'r') as help_file:
                data = json.load(help_file)
            data = data['short']
            for key in data:
                embed.add_field(name=key, value=data[key])
        try:
            await ctx.send(embed=embed)
        except Exception:
            await ctx.send("I don't have permission to send embeds here :disappointed_relieved:")

    @commands.command(name='invite')
    async def invite(self, ctx):
        """My invite link"""
        await ctx.send("To invite **Hexbot** to your server, visit: **_http://hexcode.ml_**")

    @commands.command(name='ping', aliases=['latency'])
    async def ping(self, ctx):
        """ Pong! """
        message = await ctx.send(":ping_pong: Pong!")
        ping = (message.created_at.timestamp() - ctx.message.created_at.timestamp()) * 1000
        await message.edit(content=f":ping_pong: Pong!\nTook `{int(ping)}ms`\nLatency: `{int(self.bot.latency*1000)}ms`")

    @commands.command(name='owner', aliases=['support', 'contact'])
    async def support(self, ctx, *, msg: str = ""):
        """Contact bot owner"""
        if msg == "":
            return await ctx.send("Please enter a message to send towards Bot Owner", delete_after=5.0)

        embed = discord.Embed(colour=discord.Colour(0x5dadec), description=msg)
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        embed.set_footer(text=f"{ctx.guild} : {ctx.guild.id}", icon_url=ctx.guild.icon_url)

        info = await self.bot.application_info()
        await info.owner.send(embed=embed)
        await ctx.send("Bot owner notified!")

    @commands.command(name='tts')
    async def _tts(self, ctx, *, text=''):
        """Send tts message"""
        if not text:
            return await ctx.send('Specify message to send')
        await ctx.send(content=text, tts=True)


def setup(bot):
    bot.add_cog(Misc(bot))
