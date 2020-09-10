import os
import requests
import json

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

def setup(bot):
    bot.add_cog(Media(bot))