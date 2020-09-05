'''Module for the user info command.'''

import discord
from discord.ext import commands


class Userinfo(commands.Cog):

	def __init__(self, bot):
		self.bot = bot

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
				await ctx.send('Could not find user.')
				return
		else:
			user = ctx.message.author

		if isinstance(user, discord.Member):
			role = user.top_role.name
			if role == "@everyone":
				role = "N/A"
			voice_state = None if not user.voice else user.voice.channel

		em = discord.Embed(colour=0x708DD0)
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

def setup(bot):
	bot.add_cog(Userinfo(bot))