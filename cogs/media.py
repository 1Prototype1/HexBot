import os
import requests
import json
import asyncio

import discord
from discord.ext import commands

class Media(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.header = {'Authorization': os.environ['Unsplash_Token']}

	def fetchJSON(self, url, params={}, headers={}):
		return requests.get(url, params=params, headers=headers).json()

	@commands.command(name='wallpaper', aliases=['wall'])
	async def _wallpaper(self, ctx, *query: str):
		"""Get wallpaper from Unsplash"""
		params = {'count': 1}
		if query:
			params['query'] = query
		else:
			params['count'] = 3
			params['featured'] = 'yes'

		results = self.fetchJSON('https://api.unsplash.com/photos/random', params=params, headers=self.header)
		try:
			for r in results:
				em = discord.Embed(colour=discord.Colour(0xFF355E))
				em.set_image(url=r['urls']['raw'])
				em.set_footer(text=f"{r['user']['name']} on Unsplash", icon_url='https://i.ibb.co/f4Xbgkv/lens.png')
				await ctx.send(embed=em)
		except Exception as e:
			print(e)
			await ctx.send('Error getting wallpaper :disappointed_relieved:')

	@commands.command(name='trigger')
	async def trigger(self, ctx):
		"""Trigger a user"""
		try:
			user = ctx.message.mentions[0]
		except IndexError:
			return await ctx.send("Mention the person you want to trigger")

		em = discord.Embed(color=discord.Colour(0xFF355E))
		em.set_image(url=f"https://useless-api--vierofernando.repl.co/triggered?image={user.avatar_url_as(size=1024)}")
		await ctx.send(embed=em)

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
		try:
			result = requests.get(f'https://useless-api--vierofernando.repl.co/imagetoascii?image={image_link}').text.replace('<br>','\n')
		except:
			return await ctx.send("Failed :x:\nMaybe url is wrong :link:")

		ascii_file = open("ascii.txt", "w")
		n = ascii_file.write(result)
		ascii_file.close()

		file = discord.File('ascii.txt')
		em = discord.Embed(color=discord.Colour(0xFFFF66))
		em.set_thumbnail(url=image_link)
		await ctx.send(file=file, embed=em)

	@commands.command(name='encode', aliases=['encrypt', 'style'])
	async def _encode(self, ctx, *, text: str):
		"""Encode given text"""
		if not text:
			return await ctx.send('Please provide text :pager:')

		async with ctx.typing():
			try:
				result = self.fetchJSON('https://useless-api--vierofernando.repl.co/encode', params={'text': text})
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
		"""Get pokemon card"""
		if not name:
			return await ctx.send(f'Please specify pokemon name <:pokeball:754218915613376542>')

		url = 'https://api.pokemontcg.io/v1/cards'
		params = {
					# 'setCode': 'xyp|smp|base1',
					'text': 'x',
					'name': name
				}
		try:
			async with ctx.typing():
				result = self.fetchJSON(url, params)
			result = result['cards'][0]
		except Exception as e:
			return await ctx.send('No pokemon card found :x:')
		em = discord.Embed(color=discord.Color(0xCCFF00), title=result['name'], url=result['imageUrlHiRes'])
		em.set_image(url=result['imageUrlHiRes'])
		await ctx.send(embed=em)


	@commands.command(name='ai')
	async def _aichat(self, ctx):
		"""Start AI chat mode"""
		def check(m):
			return m.author == ctx.author and not m.content.startswith('~')

		await ctx.send("Let's chat")
		while True:
			try:
				params = {'message': 'message'}
				msg = await self.bot.wait_for('message', check=check, timeout=10.0)
			except asyncio.TimeoutError:
				return await ctx.send("Bye :wave:")
			else:
				if 'bye' in msg.content:
					return await ctx.send("Bye :wave:")
				else:
					params['message'] = msg.content
					async with ctx.typing():
						response = self.fetchJSON('https://some-random-api.ml/chatbot', params=params)['response']
					await ctx.send(response)


def setup(bot):
	bot.add_cog(Media(bot))
