![Deploy](https://github.com/1Prototype1/HexBot/workflows/Deploy/badge.svg) ![Run](https://github.com/1Prototype1/HexBot/workflows/Run/badge.svg) ![Python](https://img.shields.io/badge/python-v3.7-blue?logo=python) ![License](https://img.shields.io/github/license/1Prototype1/HexBot) ![Servers](https://img.shields.io/badge/servers-4-FF355E?style=social&logo=discord)
# HexBot
Discord bot with music and other cool features. This bot can be deployed on Heroku using the free dyno.

**[Add HexBot](https://discord.com/oauth2/authorize?client_id=747461870629290035&scope=bot&permissions=24576) - Add the bot to your Discord server and use the awesome features! :sparkles:**

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
poll          - Create a quick poll
    <question> <choices>
quiz|trivia   - Start a quiz game
tally         - Tally the created poll
teams         - Makes random teams(def. 2)
toss|flip     - Flips a Coin
ttt           - Play Tic-Tac-Toe!
xkcd|comic    - Get random xkcd comics
```
🛠 Misc Commands:
```
clear|cls     - Delete the messages
help          - Display this message
list          - Displays the list of
                voice connected users
ping|latency  - Pong!
weather <loc> - Get weather of location
```
Deploying to Heroku
---
- Add the following buidpacks to your app:
  - heroku/python
  - https<span>://</span>github.com/jonathanong/heroku-buildpack-ffmpeg-latest.git
  - https<span>://</span>github.com/xrisk/heroku-opus.git
- Add your bot's access token in Config vars as BOT_Token
- Push the project files to Heroku

References
---
- [Discord.py](https://github.com/Rapptz/discord.py)
- [Documentation](https://discordpy.readthedocs.io/en/latest/index.html)
