import os
import asyncio
import io
from aiohttp import ClientSession
from textwrap import TextWrapper
from googletrans import Translator, LANGUAGES

import discord
from discord.ext import commands

class Media(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.header = {'Authorization': os.environ['Unsplash_Token']}
		self.trans = Translator()
		self.client = ClientSession()

	@commands.command(name='wallpaper', aliases=['wall'])
	async def _wallpaper(self, ctx, *query: str):
		"""Get wallpaper from Unsplash"""
		params = {'count': 1}
		if query:
			params['query'] = query
		else:
			params['count'] = 3
			params['featured'] = 'yes'
		url = 'https://api.unsplash.com/photos/random'
		async with self.client.get(url, params=params, headers=self.header) as r:
			if r.status != 200:
				return await ctx.send('Error getting wallpaper :disappointed_relieved:')
			else:
				results = await r.json()
		for r in results:
			em = discord.Embed(color=discord.Color(0xFF355E))
			em.set_image(url=r['urls']['raw'])
			em.set_footer(text=f"{r['user']['name']} on Unsplash", icon_url='https://i.ibb.co/f4Xbgkv/lens.png')
			await ctx.send(embed=em)

	@commands.command(name='trigger')
	async def trigger(self, ctx):
		"""Trigger a user"""
		try:
			user = ctx.message.mentions[0]
		except IndexError:
			return await ctx.send("Mention the person you want to trigger")

		url = f"https://useless-api--vierofernando.repl.co/triggered?image={user.avatar_url_as(size=1024)}"
		async with ctx.typing():
			async with self.client.get(url) as r:
				if r.status != 200:
					return await ctx.send('Failed to trigger :x:')
				data = io.BytesIO(await r.read())
		await ctx.send(file=discord.File(data, 'trigger.gif'))				

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

		url = 'https://useless-api--vierofernando.repl.co/imagetoascii'
		async with self.client.get(url, params={'image': str(image_link)}) as r:
			if r.status != 200:
				return await ctx.send("Failed :x:\nMaybe url is wrong :link:")
			else:
				result = await r.text()
				ascii_file = io.StringIO(result.replace('<br>', '\n'))

		em = discord.Embed(color=discord.Color(0xFFFF66))
		em.set_thumbnail(url=image_link)
		await ctx.send(file=discord.File(ascii_file, 'ascii.txt'), embed=em)

	@commands.command(name='encode', aliases=['encrypt', 'style'])
	async def _encode(self, ctx, *, text: str=""):
		"""Encode given text"""
		if not text:
			return await ctx.send('Please provide text :pager:')

		async with ctx.typing():
			try:
				url = 'https://useless-api--vierofernando.repl.co/encode'
				async with self.client.get(url, params={'text': text}) as r:
					result = await r.json()
			except:
				return await ctx.send('Failed to encode :x:')

		description = []
		for r in result:
			if r=='ciphers' or r=='styles':
				for i in result[r]:
					if i == 'upside-down':
						description.append(f"{i.title()}: `{result[r][i][::-1]}`")
					else:
						description.append(f"{i.title()}: `{result[r][i]}`")
			else:
				description.append(f"{r.title()}: `{result[r]}`")

		em = discord.Embed(title=text, color=discord.Color(0xFF007C), description='\n'.join(description))
		await ctx.send(embed=em)

	@commands.command(name='tinder', aliases=['match'])
	async def tinder(self, ctx):
		"""Tinder: It's a Match!"""
		try:
			user1 = ctx.message.mentions[0].avatar_url_as(size=1024)
			user2 = ctx.message.mentions[1].avatar_url_as(size=1024)
		except IndexError:
			return await ctx.send('Mention two users to match :heart:')

		em = discord.Embed(color=discord.Color(0xFF355E))
		em.set_image(url=f'https://useless-api--vierofernando.repl.co/tinder?image1={user1}&image2={user2}')
		await ctx.send(embed=em)

	@commands.command(name='pokemon', aliases=['pokedex'])
	async def _pokemon(self, ctx, *, name=''):
		"""Get pokemon """
		if not name:
			return await ctx.send(f'Please specify pokemon name <:pokeball:754218915613376542>')
		url = 'https://some-random-api.ml/pokedex'
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

	@commands.command(name='ai')
	async def _aichat(self, ctx):
		"""Start AI chat mode"""
		def check(m):
			return m.author == ctx.author and not m.content.startswith('~')

		await ctx.send("Let's chat")
		url = 'https://some-random-api.ml/chatbot'
		while True:
			try:
				params = {'message': 'message'}
				msg = await self.bot.wait_for('message', check=check, timeout=120.0)
			except asyncio.TimeoutError:
				return await ctx.send("Bye :wave:")
			else:
				if 'bye' in msg.content.lower():
					return await ctx.send("Bye :wave:")
				else:
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

	@commands.command(name='translate')
	async def translate(self, ctx, *args):
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


def setup(bot):
	bot.add_cog(Media(bot))
