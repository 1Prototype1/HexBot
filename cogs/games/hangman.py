import random 
import asyncio

words = ['rainbow', 'computer', 'science', 'programming',  
		 'python', 'mathematics', 'player', 'condition',  
		 'reverse', 'water', 'board', 'geek']  
  
async def play(bot, ctx):
	def check(m):
		return m.author == ctx.author
	guesses = '' 
	turns = 8
	word = random.choice(words) 
	await ctx.send("Guess the characters:")
	guess_msg = await ctx.send(f"Guesses left: `{turns}`")
	word_msg = await ctx.send(f"`{' _'*len(word)}`")
	while turns > 0: 
		out = ''
		rem_chars = 0
		for char in word:  
			if char in guesses:  
				out += char
			else:  
				out += ' _'
				rem_chars += 1
		await word_msg.edit(content=f'`{out}`')
		
		if rem_chars == 0: 
			await word_msg.edit(content=word)
			return await ctx.send("**You Win :trophy:**")

		try:
			msg = await bot.wait_for('message', check=check, timeout=20.0)
			if msg.content == 'exit':
				await ctx.send("You quit")
				return
		except asyncio.TimeoutError:
			await ctx.send("You took too long :hourglass:")
			await guess_msg.delete()
			await word_msg.delete()
			return

		guess =  msg.content[0]
		guesses += guess  
		await msg.delete()

		if guess not in word: 
			turns -= 1
			await ctx.send("Wrong :x:", delete_after=1.0) 
			await guess_msg.edit(content=f"Guesses left: `{turns}`") 
			if turns == 0:
				return await ctx.send("You Loose :x:")