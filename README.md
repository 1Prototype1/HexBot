![Deploy Status](https://img.shields.io/github/workflow/status/1Prototype1/HexBot/Deploy?label=Deploy&logo=heroku) ![Run Status](https://img.shields.io/github/workflow/status/1Prototype1/HexBot/Run?label=Run&logo=heroku) ![Python](https://img.shields.io/badge/python-v3.7.9-blue?logo=python&logoColor=ffe873) ![License](https://img.shields.io/github/license/1Prototype1/HexBot) [![Servers](https://img.shields.io/badge/servers-19-FF355E?style=social&logo=discord)](https://discord.com/oauth2/authorize?client_id=747461870629290035&scope=bot&permissions=57344)
# HexBot
A Relatively Simply Awesome Discord bot with Music, Games, Comics, Memes and other cool features. <br>
This bot is made in Python 3.7 using [discord.py](https://github.com/Rapptz/discord.py).<br>
This bot can be deployed on Heroku using the free dyno.

[![Add HexBot](https://img.shields.io/badge/-Add%20Bot-141B2E?style=for-the-badge&logo=discord)](https://discord.com/oauth2/authorize?client_id=747461870629290035&scope=bot&permissions=57344) <br>
**Add the bot to your Discord server and use these awesome features! :sparkles:**

Features
---
:musical_note: Music Commands:
```
join|connect  - Joins a voice channel
lyrics <song> - Get lyrics of the song
np            - Displays now playing song
pause         - Pauses the current song
play|p <song> - Plays specified song
queue|q       - Displays current queue
resume        - Resumes the paused song
save|star     - Save song to your DM
skip          - Skips current song
stop|dis      - Stops and disconnects bot
volume        - Changes the player's volume
```
:joystick: Fun Commands:
```
8ball         - Magic 8Ball!
    <question>
ai            - Start AI chat
drake <a, b>  - Generate Drake meme
filter        - Apply filters to image
fml           - Generate FML
fortune|quote - Fortune Cookie!
    <category>[factoid|fortune|people]
hangman       - Play Hangman
joke          - Get a random joke
                [pun|dark|riddle|geek]
meme|maymay   - Get MayMays
pokedex       - Get Pokémon info
poll          - Create a quick poll
    <question> <choices>
quiz|trivia   - Start a quiz game
roast @user   - Roasts the mentioned user
rps           - Play Rock, Paper, Scissors
tally         - Tally the created poll
tinder @u1@u2 - Get Tinder image
teams         - Makes random teams(def. 2)
toss|flip     - Flips a Coin
trigger @user - Trigger an user
ttt           - Play Tic-Tac-Toe!
wumpus        - Play Wumpus game
xkcd|comic    - Get random xkcd comics
```
🛠 Misc Commands:
```
ascii <link>  - Get ascii art of user/img
convert       - Currency Converter
    <val><from><to>
clear|cls     - Delete the messages
encode <txt>  - Encode and style the text
help          - Display this message
list          - Displays the list of
                voice connected users
palette <hex> - Get color palette
ping|latency  - Pong!
server <serv> - Get server info
shorten|url   - Shorten an URL
support       - Contact Bot owner
textart       - Generate text art
trace <ip>    - Locate IP address
translate     - Translate the text
    <id><txt>
user @user    - Get user info
wallpaper     - Get wallpaper
weather <loc> - Get weather of location
```
Deploying to Heroku
---
- Add the following buidpacks to your app:
  - heroku/python
  - https<span>://</span>github.com/jonathanong/heroku-buildpack-ffmpeg-latest.git
  - https<span>://</span>github.com/xrisk/heroku-opus.git
- Add your Bot's access token and KSoft.Si's api token in Config vars
- Push the project files to Heroku

References
---
- [Discord.py](https://github.com/Rapptz/discord.py)
- [Documentation](https://discordpy.readthedocs.io/en/latest/index.html)
