import random 
import asyncio

words = ['conversation', 'bowtie', 'skateboard', 'penguin', 'hospital', 'player', 'kangaroo', 
		'garbage', 'whisper', 'achievement', 'flamingo', 'calculator', 'offense', 'spring', 
		'performance', 'sunburn', 'reverse', 'round', 'horse', 'nightmare', 'popcorn', 
		'hockey', 'exercise', 'programming', 'platypus', 'blading', 'music', 'opponent', 
		'electricity', 'telephone', 'scissors', 'pressure', 'monkey', 'coconut', 'backbone', 
		'rainbow', 'frequency', 'factory', 'cholesterol', 'lighthouse', 'president', 'palace', 
		'excellent', 'telescope', 'python', 'government', 'pineapple', 'volcano', 'alcohol', 
		'mailman', 'nature', 'dashboard', 'science', 'computer', 'circus', 'earthquake', 'bathroom', 
		'toast', 'football', 'cowboy', 'mattress', 'translate', 'entertainment', 'glasses', 
		'download', 'water', 'violence', 'whistle', 'alligator', 'independence', 'pizza', 
		'permission', 'board', 'pirate', 'battery', 'outside', 'condition', 'shallow', 'baseball', 
		'lightsaber', 'dentist', 'pinwheel', 'snowflake', 'stomach', 'reference', 'password', 'strength', 
		'mushroom', 'student', 'mathematics', 'instruction', 'newspaper', 'gingerbread', 
		'emergency', 'lawnmower', 'industry', 'evidence', 'dominoes', 'lightbulb', 'stingray', 
		'background', 'atmosphere', 'treasure', 'mosquito', 'popsicle', 'aircraft', 'photograph', 
		'imagination', 'landscape', 'digital', 'pepper', 'roller', 'bicycle', 'toothbrush', 'newsletter']  

images =   ['```\n   +---+\n   O   | \n  /|\\  | \n  / \\  | \n      ===```',   
			'```\n   +---+ \n   O   | \n  /|\\  | \n  /    | \n      ===```', 
			'```\n   +---+ \n   O   | \n  /|\\  | \n       | \n      ===```', 
			'```\n   +---+ \n   O   | \n  /|   | \n       | \n      ===```', 
			'```\n   +---+ \n   O   | \n   |   | \n       | \n      ===```', 
			'```\n   +---+ \n   O   | \n       | \n       | \n      ===```', 
			'```\n  +---+ \n      | \n      | \n      | \n     ===```']
async def play(bot, ctx):
	def check(m):
		return m.author == ctx.author
	guesses = '' 
	turns = 6
	word = random.choice(words) 
	await ctx.send("Guess the characters:")
	guess_msg = await ctx.send(images[turns])
	word_msg = await ctx.send(f"`{' '.join('_'*len(word))}`")
	while turns > 0: 
		out = ''
		rem_chars = 0
		for char in word:  
			if char in guesses:  
				out += char
			else:  
				out += '_'
				rem_chars += 1
		await word_msg.edit(content=f"`{' '.join(out)}`")
		
		if rem_chars == 0: 
			await word_msg.edit(content=f'**{word}**')
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
			await guess_msg.edit(content=images[turns])
			if turns == 0:
				await word_msg.edit(content=f'**{word}**')
				return await ctx.send("You Loose :x:")