![Deploy Status](https://img.shields.io/github/workflow/status/1Prototype1/HexBot/Run?label=Deploy&logo=heroku) ![Run Status](https://img.shields.io/github/workflow/status/1Prototype1/HexBot/Run?label=Run&logo=heroku) ![Python](https://img.shields.io/badge/python-v3.7.9-blue?logo=python&logoColor=ffe873) ![License](https://img.shields.io/github/license/1Prototype1/HexBot) [![Servers](https://img.shields.io/badge/servers-6-FF355E?style=social&logo=discord)](https://discord.com/oauth2/authorize?client_id=747461870629290035&scope=bot&permissions=24576)
# HexBot
A Relatively Simply Awesome Discord bot with Music, Games, Comics, Memes and other cool features. <br>
This bot is made in Python 3.7 using [discord.py](https://github.com/Rapptz/discord.py).<br>
This bot can be deployed on Heroku using the free dyno.

[![Add HexBot](https://img.shields.io/badge/-Add%20Bot-141B2E?style=for-the-badge&logo=discord)](https://discord.com/oauth2/authorize?client_id=747461870629290035&scope=bot&permissions=24576) <br>
**Add the bot to your Discord server and use these awesome features! :sparkles:**

Features
---
:musical_note: Music Commands:
```
join|connect  - Joins a voice channel
lyrics        - Get lyrics of current song
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
:joystick: Game Commands:
```
8ball         - Magic 8Ball!
    <question>
fortune|quote - Fortune Cookie!
    <category>[factoid|fortune|people]
hangman       - Play Hangman
meme|maymay   - Get MayMays
poll          - Create a quick poll
    <question> <choices>
quiz|trivia   - Start a quiz game
rps           - Play Rock, Paper, Scissors
tally         - Tally the created poll
teams         - Makes random teams(def. 2)
toss|flip     - Flips a Coin
ttt           - Play Tic-Tac-Toe!
wumpus        - Play Wumpus game
xkcd|comic    - Get random xkcd comics
```
🛠 Misc Commands:
```
convert       - Currency Converter
    <val><from><to>
clear|cls     - Delete the messages
help          - Display this message
list          - Displays the list of
                voice connected users
ping|latency  - Pong!
server <serv> - Get server info
support       - Contact Bot owner
trace <ip>    - Locate IP address
user @user    - Get user info
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
