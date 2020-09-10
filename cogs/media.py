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

def setup(bot):
    bot.add_cog(Media(bot))