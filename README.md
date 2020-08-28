![Deploy](https://github.com/1Prototype1/HexBot/workflows/Deploy/badge.svg)
# HexBot
Discord bot with music and other cool features. This bot can be deployed on Heroku using the free dyno.

**[Add HexBot](https://discord.com/oauth2/authorize?client_id=747461870629290035&scope=bot) - Add the bot to your Discord server and use the awesome features! :sparkles:**

Features
---
:musical_note: Music Commands:
```
join          - Joins a voice channel
pause         - Pauses the current song
play|p        - Plays specified song
resume        - Resumes the paused song
stop|dis      - Stops and disconnect the bot
volume        - Changes the player's volume
```
:joystick: Game Commands:
```
poll          - Create a quick poll <question> <choices>
quiz|trivia   - Start a quiz game
tally         - Tally the created poll
```
:jigsaw: Misc Commands:
```
clear|cls     - Delete the messages
fortune|quote - Fortune Cookie! <category>[factoid|fortune|people]
help          - Display this message
list          - Displays the list of
                voice connected users
ping|latency  - Pong! 
teams         - Makes random teams (def. 2)
toss|flip     - Flips a Coin
```
Deploying to Heroku
---
- Add the following buidpacks to your app:
  - heroku/python
  - https<span>://</span>github.com/jonathanong/heroku-buildpack-ffmpeg-latest.git
  - https<span>://</span>github.com/xrisk/heroku-opus.git
- Push to project files to Heroku

References
---
- [Discord.py](https://github.com/Rapptz/discord.py)
- [Documentation](https://discordpy.readthedocs.io/en/latest/index.html)
