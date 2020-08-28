![Deploy](https://github.com/1Prototype1/HexBot/workflows/Deploy/badge.svg)
# HexBot
Discord bot with music and other cool features. This bot can be deployed on Heroku using the free dyno.

**[Add HexBot](https://discord.com/oauth2/authorize?client_id=747461870629290035&scope=bot) - Add the bot to your Discord server and use the awesome features! :sparkles:**

Features
---
```diff
+ Play Music [play/pause/resume/stop/volume/download]
+ List members in your channel
+ Make random teams from members in voice channel
+ Toss a coin
+ Fortune (Factoids, quotes, etc.)
+ Quick Poll
+ Quiz
+ Clear chat (*Requires Manage Messages permission)
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
