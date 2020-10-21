import os
import io
import ksoftapi
from googletrans import Translator, LANGUAGES
from textwrap import TextWrapper

import discord
from discord.ext import commands

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = bot.client
        self.kclient = bot.kclient
        self.trans = Translator()

    @commands.command(name='convert', aliases=['currency'])
    async def currency(self, ctx, value: str="", _from: str="", to: str=""):
        """Currency conversion"""
        if value=="" or _from=="" or to=="":
            return await ctx.send("Please enter values in proper format\n`~convert [value] [from] [to]`\neg: `~convert 16 usd inr`")

        try:
            async with ctx.typing():
                c = await self.kclient.kumo.currency_conversion(_from, to, value)
        except (ksoftapi.NoResults, ksoftapi.errors.APIError):
            await ctx.send('Conversion Failed :x:')
        else:
            await ctx.send(f":currency_exchange: Conversion:\n`{value} {_from.upper()}` = `{c.pretty}`")

    @commands.command(name='encode', aliases=['encrypt', 'style'])
    async def _encode(self, ctx, *, text: str=""):
        """Encode given text"""
        if not text:
            return await ctx.send('Please provide text :pager:')

        async with ctx.typing():
            try:
                url = os.environ['HexApi'] + 'encode'
                async with self.client.get(url, params={'text': text}) as r:
                    result = await r.json()
            except:
                return await ctx.send('Failed to encode :x:')

        description = []
        for r in result:
            if r in ['ciphers', 'styles']:
                for i in result[r]:
                    if i == 'upside-down':
                        description.append(f"{i.title()}: `{result[r][i][::-1]}`")
                    else:
                        description.append(f"{i.title()}: `{result[r][i]}`")
            else:
                description.append(f"{r.title()}: `{result[r]}`")

        em = discord.Embed(title=text, color=discord.Color(0xFF007C), description='\n'.join(description))
        await ctx.send(embed=em)

    @commands.command(name='list')
    async def listusers(self, ctx):
        """Displays the list of connected users"""
        members = ctx.author.voice.channel.members
        memnames = []
        for member in members:
            memnames.append(member.name)
        await ctx.send(f"Members in {ctx.author.voice.channel.name}:\n```\n" + "\n".join(memnames) +"\n```")

    @commands.command(name='palette', aliases=['color', 'colour'])
    async def palette(self, ctx, hexcode: str=''):
        """Get palette from HEX"""
        if not hexcode:
            return await ctx.send('Enter hexcode of color :paintbrush:')

        if hexcode.startswith('#'):
            hexcode = hexcode[1:]
        url = os.environ['HexApi'] + 'color?hexcode=' + hexcode
        async with ctx.typing():
            async with self.client.get(url) as r:
                if r.status != 200:
                    return await ctx.send('Invalid hexcode :x:')
                data = await r.json()
            em = discord.Embed(color=discord.Color(int(hexcode, 16)))
            em.set_thumbnail(url=data['image'])
            em.add_field(name='Name', value=data['name'])
            em.add_field(name='Brightness', value=data['brightness'])
            em.add_field(name='B or W', value=data['blackorwhite_text'])
            em.add_field(name='Hex', value=data['hex'])
            em.add_field(name='RGB', value=data['rgb'])
            em.add_field(name='Int', value=data['int'])
            em.set_image(url=data['image_gradient'])
        await ctx.send(embed=em)

    @commands.command(name='pokemon', aliases=['pokedex'])
    async def _pokemon(self, ctx, *, name=''):
        """Get pokemon """
        if not name:
            return await ctx.send('Please specify pokemon name <:pokeball:754218915613376542>')
        url = os.environ['HexApi'] + 'pokedex'
        try:
            params = {'id': int(name)}
        except ValueError:
            params = {'pokemon': name}
        try:
            async with ctx.typing():
                async with self.client.get(url, params=params) as r:
                    data = await r.json()
        except Exception:
            return await ctx.send('Pokemon not found :x:')
        else:
            if 'error' in data:
                return await ctx.send('Pokemon not found :x:')

        desc = f"Height: `{data['height']}`\nWeight: `{data['weight']}`\nBase Experience: `{data['base_experience']}`"
        em = discord.Embed(color=discord.Color(0xFF355E), title=f"{data['name'].title()} #{int(data['id'])}", description=desc)
        em.set_author(name='Pokédex', icon_url='https://i.ibb.co/L9xKJWz/pokedex.png')
        em.set_thumbnail(url=data['sprites']['animated'])
        
        fields = []
        for stat in data['stats']:
            fields.append(f"{stat.title()}: `{data['stats'][stat]}`")
        em.add_field(name='Stats:', value='\n'.join(fields), inline=False)
        
        em.add_field(name='Abilities:', value='\n'.join([f'`{x}`' for x in data['abilities']]))

        em.add_field(name='Type:', value='\n'.join([f'`{x}`' for x in data['type']]))
        em.add_field(name='Evolution:', value=f"`{' -> '.join(list(dict.fromkeys(data['family']['evolutionLine'])))}`", inline=False)
        desc = '\n'.join(TextWrapper(width=60).wrap(data['description']))
        em.set_footer(text=desc)

        await ctx.send(embed=em)

    @commands.command(name='analyze', aliases=['predict'])
    async def predict(self, ctx, *, text=None):
        """Analyze message for inappropriate content"""
        if not text:
            return await ctx.send('Please specify the message to analyze :pager:')
        
        url = os.environ['Predict_API']
        text = text.strip('|')
        payload = {
            'comment': {'text': text},
            'languages': ['en'],
            'requestedAttributes': {'TOXICITY': {}, 'IDENTITY_ATTACK': {}, 'INSULT': {}, 'PROFANITY': {}, 'THREAT': {}, 
                                'SEXUALLY_EXPLICIT': {}, 'FLIRTATION': {}, 'SPAM': {}, 'OBSCENE': {}, 'INCOHERENT': {}, 'INFLAMMATORY': {}}
            }
        async with self.client.post(url, json=payload) as r:
            if r.status != 200:
                print(r)
                return print('Error')
            data = await r.json()
        data = data['attributeScores']
        result = []
        for i in data:
            result.append([i, data[i]['summaryScore']['value']])
        result.sort(key=lambda x: x[1], reverse=True)
        data = []
        for i in result:
            if i[1] > 0.5:
                data.append(f"+ {i[0].title()} {' '*(20-len(i[0]))}{i[1]:.2%}")
            else:
                data.append(f"- {i[0].title()} {' '*(20-len(i[0]))}{i[1]:.2%}")
        data = '\n'.join(data)
        
        em = discord.Embed(color=discord.Color(0xCCFF00), description=f"||{text}||")
        em.set_author(name=ctx.author.name, icon_url=str(ctx.author.avatar_url_as(size=64)))
        em.add_field(name="Prediction:", value=f"```diff\n{data}\n```")

        await ctx.send(embed=em)

    @commands.command(name='qr')
    async def qrcode(self, ctx, *, data=None):
        """Generate QR code"""
        if not data:
            return await ctx.send('Please specify data :link:')

        url = os.environ['HexApi'] + 'qrcode?data=' + data
        async with self.client.get(url) as r:
            if r.status != 200:
                return await ctx.send('Failed to generate QR code :x:')
            data = io.BytesIO(await r.read())

        await ctx.send(file=discord.File(data, 'qr.png'))

    @commands.command(name='rhyme')
    async def rhyme(self, ctx, word=""):
        if not word:
            return await ctx.send("Specify a word :thought_balloon:")

        url = os.environ['HexApi'] + 'rhyme?word=' + word.strip()
        async with ctx.typing():
            async with self.client.get(url) as r:
                if r.status != 200:
                    return ctx.send('Failed to get rhymes :x:')
                data = await r.json()
            result = []
            for i in data[:30]:
                result.append(i['word'])
        await ctx.send(f'Word that rhyme with **{word}**\n' + f"`{', '.join(result)}`")

    @commands.command(name='trace', aliases=['ip'])
    async def trace(self, ctx, ip: str=""):
        """Trace ip"""
        if ip=="":
            return await ctx.send("Please enter an `IP` address :satellite:")

        try:
            async with ctx.typing():
                info = await self.kclient.kumo.trace_ip(ip)
        except (ksoftapi.NoResults, ksoftapi.errors.APIError):
            await ctx.send('Unable to locate :x:\nEnter valid IP')
        else:
            details = [['City', 'city'], ['Continent code', 'continent_code'], ['Continent name', 'continent_name'], ['Country code', 'country_code'], ['Country_name', 'country_name'], ['DMA code', 'dma_code'], ['Latitude', 'latitude'], ['Longitude', 'longitude'], ['Postal code', 'postal_code'], ['Region', 'region'], ['Timezone', 'time_zone']]
            description = []
            for i in details:
                description.append(f'{i[0]}: `{getattr(info, i[1])}`')
            description.append(f':map:Map: [GoogleMaps]({info.gmap})')

            embed = discord.Embed(title=":satellite_orbital: IP information:", colour=discord.Colour(0xff00cc), description="\n".join(description))
            embed.set_footer(text=ip, icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)

    @commands.command(name='translate')
    async def translate(self, ctx, *args):
        """Translator"""
        if len(args)>0:
            if args[0]=='--list':
                lang = ''
                for l in LANGUAGES:
                    lang = lang+str(l)+' ('+str(LANGUAGES[l]).title()+')\n'
                embed = discord.Embed(title='List of supported languages', description=str(lang), color=discord.Color(0x5DADEC))
                await ctx.send(embed=embed)
            elif len(args)>1:
                destination = args[0]
                try:
                    toTrans = ' '.join(args[1:len(args)])
                except IndexError:
                    await ctx.send('No text to translate :x:')
                try:
                    async with ctx.typing():
                        translation = self.trans.translate(toTrans, dest=destination)
                    embed = discord.Embed(description=translation.text, color=discord.Color(0x5DADEC))
                    embed.set_footer(text=f'Translated {LANGUAGES[translation.src]} to {LANGUAGES[translation.dest]}.', icon_url='https://i.ibb.co/1np1s8P/translate.png')
                    await ctx.send(embed=embed)
                except Exception as e:
                    return await ctx.send('Unable to translate :x:\nMaybe language id was wrong')
            else:
                await ctx.send(content='Please add a language id\nType `~translate --list` for the list')
        else:
            await ctx.send(content='Please add translations\neg.`~translate en Hola`\nType `~translate --list` for supported languages.')

    @commands.command(name='sinfo', aliases=['server'])
    async def serverinfo(self, ctx, *, name:str = ""):
        """Get server info"""
        if name:
            server = None
            try:
                server = self.bot.get_guild(int(name))
                if not server:
                    return await ctx.send('Server not found :satellite_orbital:')
            except:
                for i in self.bot.guilds:
                    if i.name.lower() == name.lower():
                        server = i
                        break
                if not server:
                    return await ctx.send("Server not found :satellite_orbital: or maybe I'm not in it")
        else:
            server = ctx.guild
        # Count online members
        online = 0
        for i in server.members:
            if str(i.status) == 'online' or str(i.status) == 'idle' or str(i.status) == 'dnd':
                online += 1
        # Count channels
        tchannel_count = len([x for x in server.channels if type(x) == discord.channel.TextChannel])
        vchannel_count = len([x for x in server.channels if type(x) == discord.channel.VoiceChannel])
        # Count roles
        role_count = len(server.roles)

        # Create embed
        em = discord.Embed(color=0x00CC99)
        em.set_author(name='Server Info:', icon_url=server.owner.avatar_url)
        em.add_field(name='Name', value=f'`{server.name}`')
        em.add_field(name='Owner', value=f'`{server.owner}`', inline=False)
        em.add_field(name='Members', value=f'`{server.member_count}`')
        em.add_field(name='Online', value=f'`{online}`')
        em.add_field(name='Region', value=f'`{str(server.region).title()}`')
        em.add_field(name='Text Channels', value=f'`{tchannel_count}`')
        em.add_field(name='Voice Channels', value=f'`{vchannel_count}`')
        em.add_field(name='Verification Level', value=f'`{str(server.verification_level).title()}`')
        em.add_field(name='Number of roles', value=f'`{role_count}`')
        em.add_field(name='Highest role', value=f'`{server.roles[-1]}`')
        em.add_field(name='Created At', value=f"`{server.created_at.__format__('%A, %d. %B %Y @ %H:%M:%S')}`", inline=False)
        em.set_thumbnail(url=server.icon_url)
        em.set_footer(text='Server ID: %s' % server.id)

        try:
            await ctx.send(embed=em)
        except Exception:
            await ctx.send("I don't have permission to send embeds here :disappointed_relieved:")

    @commands.command(name='url', aliases=['shorten'])
    async def url_shorten(self, ctx, *, url):
        if not url:
            return await ctx.send('Please specify the url :link:')
        if not url.startswith('http'):
            url = 'http://' + url
        try:
            async with ctx.typing():
                async with self.client.post('https://rel.ink/api/links/', data={'url': url}) as r:
                    data = await r.json()
            if data.get('hashid'):
                return await ctx.send(f"Url: `{data['url']}`\nShort: https://rel.ink/{data['hashid']}")
        except:
            await ctx.send('Failed to shorten url :x:')

    @commands.command(name = 'userinfo', aliases=['user', 'uinfo', 'ui'])
    async def userinfo(self, ctx, *, name=""):
        """Get user info. Ex: ~user @user"""
        if name:
            try:
                user = ctx.message.mentions[0]
            except IndexError:
                user = ctx.guild.get_member_named(name)
            try:
                if not user:
                    user = ctx.guild.get_member(int(name))
                if not user:
                    user = self.bot.get_user(int(name))
            except ValueError:
                pass
            if not user:
                await ctx.send('User not found :man_frowning_tone1:')
                return
        else:
            user = ctx.message.author

        if isinstance(user, discord.Member):
            role = user.top_role.name
            if role == "@everyone":
                role = "N/A"
            voice_state = None if not user.voice else user.voice.channel

        em = discord.Embed(colour=0x00CC99)
        em.add_field(name='User ID', value=f'`{user.id}`')
        if isinstance(user, discord.Member):
            if isinstance(user.activity, discord.Spotify):
                activity = "Listening " + user.activity.title
            elif user.activity is not None: 
                activity = str(user.activity.type)[13:].title() + ' ' + user.activity.name
            else:
                activity = None

            em.add_field(name='Nick', value=f'`{user.nick}`')
            em.add_field(name='Status', value=f'`{user.status}`')
            em.add_field(name='In Voice', value=f'`{voice_state}`')
            em.add_field(name='Activity', value=f'`{activity}`')
            em.add_field(name='Highest Role', value=f'`{role}`')
        em.add_field(name='Account Created', value=f"`{user.created_at.__format__('%A, %d %B %Y @ %H:%M:%S')}`", inline=False)
        if isinstance(user, discord.Member):
            em.add_field(name='Join Date', value=f"`{user.joined_at.__format__('%A, %d %B %Y @ %H:%M:%S')}`", inline=False)
        em.set_thumbnail(url=user.avatar_url)
        em.set_author(name=user, icon_url=user.avatar_url)
        
        try:
            await ctx.send(embed=em)
        except Exception:
            await ctx.send("I don't have permission to send embeds here :disappointed_relieved:")

    @commands.command(name='weather')
    async def weather(self, ctx, *, location: str = ""):
        """Get weather"""
        if location == "":
            return await ctx.send('Please provide location :map:')

        try:
            async with ctx.typing():
                w = await self.kclient.kumo.basic_weather(location, icon_pack='color')
        except ksoftapi.NoResults:
            await ctx.send('Unable to locate :mag_right:')
        else:
            infos = [['Apparent Temperature', 'apparent_temperature', 1, ' °C'], ['Precipitation Intensity', 'precip_intensity', 1, ' mm/h'], ['Precipitation Probability', 'precip_probability', 100, ' %'], ['Dew Point', 'dew_point', 1, ' °C'], ['Humidity', 'humidity', 100, ' %'], ['Pressure', 'pressure', 1, ' mbar'], ['Wind Speed', 'wind_speed', 1, ' km/h'], ['Cloud Cover', 'cloud_cover', 100, ' %'], ['Visibility', 'visibility', 1, ' km'], ['UV Index', 'uv_index', 1, ''], ['Ozone', 'ozone', 1, '']]
            gmap = f"[🗺](https://www.google.com/maps/search/?api=1&query='{w.location.address}')"
            gmap = gmap.replace("'", "%22");gmap = gmap.replace(" ", "%20")

            info = [f'{gmap} **{w.location.address}**\n']
            for i in infos:
                info.append(f'{i[0]}: `{getattr(w, i[1])*i[2]}{i[3]}`')

            embed = discord.Embed(title=f"{w.summary} {w.temperature}°C", colour=discord.Colour(0xffff66), description='\n'.join(info))
            embed.set_thumbnail(url=w.icon_url)
            embed.set_author(name='Weather:', icon_url=w.icon_url)
            await ctx.send(embed=embed)

    @commands.command(name='wordinfo', aliases=['pronunciation', 'pron', 'word'])
    async def wordinfo(self, ctx, word=""):
        if not word:
            return await ctx.send("Specify a word :thought_balloon:")

        url = os.environ['HexApi'] + 'wordinfo?word=' + word.strip()
        async with ctx.typing():
            async with self.client.get(url) as r:
                if r.status != 200:
                    return ctx.send('Failed to get info :x:')
                data = await r.json()
            result = [f"**Word:** {data['word']}"]
            result.append(f"**Pronunciation:** {data['ipa']}")
            result.append(f"**Frequency:** {data['freq']}")
            if 'a' in data['flags']:
                result.append("**Offensive:** Yes")
            else:
                result.append("**Offensive:** No")
        await ctx.send('\n'.join(result))


def setup(bot):
    bot.add_cog(Fun(bot))
