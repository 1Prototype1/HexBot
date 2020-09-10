import os
import urllib3
import json

import discord
from discord.ext import commands

class Media(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.header = {'Authorization': os.environ['Unsplash_Token']}
		self.http = urllib3.PoolManager()

	@commands.command(name='wallpaper', aliases=['wall'])
	async def _wallpaper(self, ctx, *query: str):
		"""Get wallpaper from Unsplash"""
		fields = {'count': 1}
		if query:
			fields['query'] = query
		else:
			fields['count'] = 3
		results = self.http.request('GET', 'https://api.unsplash.com/photos/random', headers=self.header, fields=fields)
		results = json.loads(results.data.decode('utf-8'))
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