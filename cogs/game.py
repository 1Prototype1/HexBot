import random
import asyncio
import aiopentdb

import discord
from discord.ext import commands
from games import tictactoe, wumpus, hangman, minesweeper, twenty

class Game(commands.Cog):
    """Play various Games"""

    def __init__(self, bot):
        self.bot = bot
        self.tclient = aiopentdb.Client()

    @commands.command(name='2048')
    async def twenty(self, ctx):
        """Play 2048 game"""
        await twenty.play(ctx, self.bot)

    @commands.command(name="8ball")
    async def eight_ball(self, ctx, ques=""):
        """Magic 8Ball"""
        if ques=="":
            await ctx.send("Ask me a question first")
        else:
            choices = [
            'It is certain.', 'It is decidedly so.', 'Without a doubt.', 'Yes – definitely.', 'You may rely on it.',
            'As I see it, yes.', 'Most likely.', 'Outlook good.', 'Yes.', 'Signs point to yes.',
            'Reply hazy, try again.', 'Ask again later.', 'Better not tell you now.', 'Cannot predict now.', 'Concentrate and ask again.',
            "Don't count on it.", 'My reply is no.', 'My sources say no.', 'Outlook not so good.', 'Very doubtful.'
            ]
            await ctx.send(f":8ball: says: ||{random.choice(choices)}||")

    @commands.command(name='hangman', aliases=['hang'])
    async def hangman(self, ctx):
        """Play Hangman"""
        await hangman.play(self.bot, ctx)

    @commands.command(name='minesweeper', aliases=['ms'])
    async def minesweeper(self, ctx, columns = None, rows = None, bombs = None):
        """Play Minesweeper"""
        await minesweeper.play(ctx, columns, rows, bombs)

    @commands.command(name='poll')
    async def quickpoll(self, ctx, question, *options: str):
        """Create a quick poll[~poll "question" choices]"""
        if len(options) <= 1:
            await ctx.send('You need more than one option to make a poll!')
            return
        if len(options) > 10:
            await ctx.send('You cannot make a poll for more than 10 things!')
            return

        if len(options) == 2 and options[0] == 'yes' and options[1] == 'no':
            reactions = ['✅', '❌']
        else:
            reactions = ['1⃣', '2⃣', '3⃣', '4⃣', '5⃣', '6⃣', '7⃣', '8⃣', '9⃣', '🔟']

        description = []
        for x, option in enumerate(options):
            description += '\n {} {}'.format(reactions[x], option)
        embed = discord.Embed(title=question, description=''.join(description), color=discord.Colour(0xFF355E))
        react_message = await ctx.send(embed=embed)
        for reaction in reactions[:len(options)]:
            await react_message.add_reaction(reaction)
        embed.set_footer(text='Poll ID: {}'.format(react_message.id))
        await react_message.edit(embed=embed)

    @commands.command(name='rps', aliases=['rockpaperscissors'])
    async def rps(self, ctx):
        """Play Rock, Paper, Scissors game"""
        def check_win(p, b):
            if p=='🌑':
                return False if b=='📄' else True
            if p=='📄':
                return False if b=='✂' else True
            # p=='✂'
            return False if b=='🌑' else True

        async with ctx.typing():
            reactions = ['🌑', '📄', '✂']
            game_message = await ctx.send("**Rock Paper Scissors**\nChoose your shape:", delete_after=15.0)
            for reaction in reactions:
                await game_message.add_reaction(reaction)
            bot_emoji = random.choice(reactions)

        def check(reaction, user):
            return user != self.bot.user and user == ctx.author and (str(reaction.emoji) == '🌑' or '📄' or '✂')
        try:
            reaction, _ = await self.bot.wait_for('reaction_add', timeout=10.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Time's Up! :stopwatch:")
        else:
            await ctx.send(f"**:man_in_tuxedo_tone1:\t{reaction.emoji}\n:robot:\t{bot_emoji}**")
            # if conds
            if str(reaction.emoji) == bot_emoji:
                await ctx.send("**It's a Tie :ribbon:**")
            elif check_win(str(reaction.emoji), bot_emoji):
                await ctx.send("**You win :sparkles:**")
            else:
                await ctx.send("**I win :robot:**")

    @commands.command(name='tally')
    async def tally(self, ctx, pid):
        """Tally the created poll"""
        poll_message = await ctx.message.channel.fetch_message(pid)
        if not poll_message.embeds:
            return
        embed = poll_message.embeds[0]
        if poll_message.author != self.bot.user:
            return
        if not embed.footer.text.startswith('Poll ID:'):
            return
        unformatted_options = [x.strip() for x in embed.description.split('\n')]
        opt_dict = {x[:2]: x[3:] for x in unformatted_options} if unformatted_options[0][0] == '1' \
            else {x[:1]: x[2:] for x in unformatted_options}
        # check if we're using numbers for the poll, or x/checkmark, parse accordingly
        voters = [self.bot.user.id]  # add the bot's ID to the list of voters to exclude it's votes

        tally = {x: 0 for x in opt_dict.keys()}
        for reaction in poll_message.reactions:
            if reaction.emoji in opt_dict.keys():
                reactors = await reaction.users().flatten()
                for reactor in reactors:
                    if reactor.id not in voters:
                        tally[reaction.emoji] += 1
                        voters.append(reactor.id)

        output = 'Results of the poll for "{}":\n'.format(embed.title) + \
                '\n'.join(['{}: {}'.format(opt_dict[key], tally[key]) for key in tally.keys()])
        await ctx.send(output)

    @commands.command(name='teams', aliases=['team'])
    async def teams(self, ctx, num=2):
        """Makes random teams with specified number(def. 2)"""
        if not ctx.author.voice:
            return await ctx.send("You are not connected to a voice channel :mute:")
        members = ctx.author.voice.channel.members
        memnames = []
        for member in members:
            memnames.append(member.name)

        remaining = memnames
        if len(memnames)>=num:
            for i in range(num):
                team = random.sample(remaining,len(memnames)//num)
                remaining = [x for x in remaining if x not in team]
                await ctx.send(f"Team {chr(65+i)}\n" + "```CSS\n" + '\n'.join(team) + "\n```")
        if len(remaining)> 0:
            await ctx.send("Remaining\n```diff\n- " + '\n- '.join(remaining) + "\n```")

    @commands.command(name='toss', aliases=['flip'])
    async def toss(self, ctx):
        """Flips a Coin"""
        coin = ['+ heads', '- tails']
        await ctx.send(f"```diff\n{random.choice(coin)}\n```")

    @commands.command(name='quiz', aliases=['trivia'])
    async def quiz(self, ctx):
        """Start an interactive quiz game"""
        try:
            async with ctx.typing():
                question = await self.tclient.fetch_questions(
                    amount=1
                    # difficulty=aiopentdb.Difficulty.easy
                )
                question = question[0]
                if question.type.value == 'boolean':
                    options = ['True', 'False']
                else:
                    options = [question.correct_answer]
                    options.extend(question.incorrect_answers)
                    options = random.sample(options, len(options)) # Shuffle
                answer = options.index(question.correct_answer)

                if len(options) == 2 and options[0] == 'True' and options[1] == 'False':
                    reactions = ['✅', '❌']
                else:
                    reactions = ['1⃣', '2⃣', '3⃣', '4⃣']

                description = []
                for x, option in enumerate(options):
                    description += '\n {} {}'.format(reactions[x], option)

                embed = discord.Embed(title=question.content, description=''.join(description), color=discord.Colour(0xFF9933))
                embed.set_footer(text='Answer using the reactions below⬇')
                quiz_message = await ctx.send(embed=embed)
                for reaction in reactions:
                    await quiz_message.add_reaction(reaction)

            def check(reaction, user):
                return user != self.bot.user and user == ctx.author and (str(reaction.emoji) == '1️⃣' or '2️⃣' or '3️⃣' or '4️⃣' or '✅' or '❌')

            try:
                reaction, _ = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            except asyncio.TimeoutError:
                await ctx.send(f"Time's Up! :stopwatch:\nAnswer is **{options[answer]}**")
            else:
                if str(reaction.emoji) == reactions[answer]:
                    await ctx.send("Correct answer:sparkles:")
                else:
                    await ctx.send(f"Wrong Answer :no_entry_sign:\nAnswer is **{options[answer]}**")
        except:
            return await ctx.send('Failed to start quiz :x:')

    @commands.command(name='tictactoe', aliases=['ttt'])
    async def ttt(self, ctx):
        """Play Tic-Tac-Toe"""
        await tictactoe.play_game(self.bot, ctx, chance_for_error=0.2) # Win Plausible

    @commands.command(name='wumpus')
    async def _wumpus(self, ctx):
        """Play Wumpus game"""
        await wumpus.play(self.bot, ctx)

def setup(bot):
    bot.add_cog(Game(bot))
