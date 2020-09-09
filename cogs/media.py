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
		fields = {}
		if query:
			fields = {'query': query}
		r = self.http.request('GET', 'https://api.unsplash.com/photos/random', headers=self.header, fields=fields)
		r = json.loads(r.data.decode('utf-8'))
		if not r.get('errors', None):
			em = discord.Embed()
			em.set_image(url=r['urls']['raw'])
			em.set_footer(text=f"©{r['user']['name']} from Unsplash")
			await ctx.send(embed=em)
		else:
			await ctx.send('Error getting wallpaper :disappointed_relieved:')

def setup(bot):
    bot.add_cog(Media(bot))