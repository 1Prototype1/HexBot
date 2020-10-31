import inspect
import io
import textwrap
import traceback
from contextlib import redirect_stdout
import datetime
from speedtest import Speedtest
from psutil import virtual_memory, cpu_percent, cpu_freq
from subprocess import run, DEVNULL

import discord
from discord.ext import commands

class Debug(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(error.original)

    async def cog_before_invoke(self, ctx):
        """ Check for bot owner """
        isOwner = await self.bot.is_owner(ctx.author)
        if not isOwner:
            raise commands.CommandInvokeError('Only bot owner is permitted to use this command :man_technologist_tone1:')
        return isOwner

    @commands.command(name='speedtest')
    async def speed_test(self, ctx):        
        """Speedtest"""
        async with ctx.typing():
            s = Speedtest()
            s.get_best_server()
            s.download()
            s.upload()
            s = s.results.dict()
            
            await ctx.send(f"Ping: `{s['ping']}ms`\nDownload: `{round(s['download']/10**6, 3)} Mbits/s`\nUpload: `{round(s['upload']/10**6, 3)} Mbits/s`\nServer: `{s['server']['sponsor']}, {s['server']['name']}, {s['server']['country']}`\nBot: `{s['client']['isp']}({s['client']['ip']}) {s['client']['country']} {s['client']['isprating']}`")

    @commands.command(name='botinfo' , aliases=['botstats', 'status'])
    async def stats(self, ctx):
        """Bot stats."""
        # Uptime
        uptime = (datetime.datetime.now() - self.bot.uptime)
        hours, rem = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(rem, 60)
        days, hours = divmod(hours, 24)
        if days:
            time = '%s days, %s hours, %s minutes, and %s seconds' % (days, hours, minutes, seconds)
        else:
            time = '%s hours, %s minutes, and %s seconds' % (hours, minutes, seconds)
        
        # Embed
        em = discord.Embed(color=0x4FFCFA)
        em.set_author(name=f'{self.bot.user} Stats:', icon_url=self.bot.user.avatar_url, url='https://discord.com/oauth2/authorize?client_id=747461870629290035&scope=bot&permissions=24576')
        em.add_field(name=':clock3: Uptime', value=f'`{time}`', inline=False)
        em.add_field(name=':outbox_tray: Msgs sent', value=f'`{self.bot.messages_out:,}`')
        em.add_field(name=':inbox_tray: Msgs received', value=f'`{self.bot.messages_in:,}`')
        em.add_field(name=':crossed_swords: Servers', value=f'`{len(self.bot.guilds)}`')
        em.add_field(name=':satellite_orbital: Server Region', value=f'`{self.bot.region}`')

        mem = virtual_memory()
        mem_usage = f"{mem.percent} % {mem.used / 1024 ** 2:.2f} MiB"
        em.add_field(name=u':floppy_disk: Memory usage', value=f'`{mem_usage}`')
        cpu_usage = f"{cpu_percent(1)} % {cpu_freq().current / 1000:.2f} Ghz"
        em.add_field(name=':desktop: CPU usage', value=f'`{cpu_usage}`')
        
        try:
            await ctx.send(embed=em)
        except Exception:
            await ctx.send("I don't have permission to send embeds here :disappointed_relieved:")

    @commands.command(name='eval', aliases=['py'])
    async def _eval(self, ctx, *, body):
        """Evaluates python code"""
        env = {
            'ctx': ctx,
            'bot': self.bot,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            'source': inspect.getsource
        }

        def cleanup_code(content):
            """Automatically removes code blocks from the code."""
            # remove ```py\n```
            if content.startswith('```') and content.endswith('```'):
                return '\n'.join(content.split('\n')[1:-1])

            # remove `foo`
            return content.strip('` \n')

        env.update(globals())

        body = cleanup_code(body)
        stdout = io.StringIO()
        err = out = None

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        def paginate(text: str):
            '''Simple generator that paginates text.'''
            last = 0
            pages = []
            for curr in range(0, len(text)):
                if curr % 1980 == 0:
                    pages.append(text[last:curr])
                    last = curr
                    appd_index = curr
            if appd_index != len(text)-1:
                pages.append(text[last:curr])
            return list(filter(lambda a: a != '', pages))
        
        try:
            exec(to_compile, env)
        except Exception as e:
            err = await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')
            return await ctx.message.add_reaction('\u2049')

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            err = await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            if ret is None:
                if value:
                    try:
                        
                        out = await ctx.send(f'```py\n{value}\n```')
                    except:
                        paginated_text = paginate(value)
                        for page in paginated_text:
                            if page == paginated_text[-1]:
                                out = await ctx.send(f'```py\n{page}\n```')
                                break
                            await ctx.send(f'```py\n{page}\n```')
            else:
                try:
                    out = await ctx.send(f'```py\n{value}{ret}\n```')
                except:
                    paginated_text = paginate(f"{value}{ret}")
                    for page in paginated_text:
                        if page == paginated_text[-1]:
                            out = await ctx.send(f'```py\n{page}\n```')
                            break
                        await ctx.send(f'```py\n{page}\n```')

        if out:
            await ctx.message.add_reaction('✅')  # tick
        elif err:
            await ctx.message.add_reaction('❌')  # x
        else:
            await ctx.message.add_reaction('✅')

    @commands.command(name='reload')
    async def reload_module(self, ctx, arg=None):
        """Reload module"""
        modules = ['music', 'fun', 'utility', 'meme', 'game', 'misc', 'debug']
        if not arg:
            return await ctx.send(embed=discord.Embed(title='Modules', description='\n'.join(modules)))
        if arg.lower() == 'all':
            for module in modules:
                msg = await ctx.send(f":arrows_counterclockwise: Reloading `{module}`...")
                try:
                    self.bot.unload_extension('cogs.' + module)
                    self.bot.load_extension('cogs.' + module)
                except:
                    await msg.edit(content=f":x: Reloading `{module}` Failed!")
                else:
                    await msg.edit(content=f":white_check_mark: Reloaded `{module}`")
        elif arg.lower() == 'code':
            msg = await ctx.send('<:octocat:766423121946345512> Code Updating...')
            run(['git', 'pull', '--no-rebase'], stdout=DEVNULL)
            await msg.edit(content='<:octocat:766423121946345512> Code Updated')
        elif arg.lower() in modules:
            msg = await ctx.send(f":arrows_counterclockwise: Reloading `{arg.lower()}`...")
            try:
                self.bot.unload_extension('cogs.' + arg.lower())
                self.bot.load_extension('cogs.' + arg.lower())
            except:
                await msg.edit(content=f":x: Reloading `{arg.lower()}` Failed!")
            else:
                await msg.edit(content=f":white_check_mark: Reloaded `{arg.lower()}`")


def setup(bot):
    bot.add_cog(Debug(bot))
