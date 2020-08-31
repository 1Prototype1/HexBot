![Deploy](https://github.com/1Prototype1/HexBot/workflows/Deploy/badge.svg) ![Python](https://img.shields.io/badge/python-v3.7-blue?logo=python) ![License](https://img.shields.io/github/license/1Prototype1/HexBot) ![Servers](https://img.shields.io/badge/servers-3-FF355E?style=social&logo=discord)
# HexBot
Discord bot with music and other cool features. This bot can be deployed on Heroku using the free dyno.

**[Add HexBot](https://discord.com/oauth2/authorize?client_id=747461870629290035&scope=bot&permissions=24576) - Add the bot to your Discord server and use the awesome features! :sparkles:**

Features
---
:musical_note: Music Commands:
```
join|connect  - Joins a voice channel
np            - Displays now playing song
pause         - Pauses the current song
play|p        - Plays specified song
queue|q       - Displays current queue
resume        - Resumes the paused song
skip          - Skips current song
stop|dis      - Stops and disconnects bot
volume        - Changes the player's volume
```
:joystick: Game Commands:
```
fortune|quote - Fortune Cookie!
    <category>[factoid|fortune|people]
poll          - Create a quick poll
    <question> <choices>
quiz|trivia   - Start a quiz game
tally         - Tally the created poll
teams         - Makes random teams(def. 2)
toss|flip     - Flips a Coin
xkcd|comic    - Get random xkcd comics
```
:jigsaw: Misc Commands:
```
clear|cls     - Delete the messages
help          - Display this message
list          - Displays the list of
                voice connected users
ping|latency  - Pong!
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
