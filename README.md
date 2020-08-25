# HexBot
Discord bot with music and other cool features. This bot can be deployed on Heroku using the free dyno.

Features
---
```diff
+ Play Music [play/pause/resume/stop/volume]
+ List members in your channel
+ Make random teams from members in voice channel
+ Toss a coin
```

Deploying to Heroku
---
- Add the followin buidpacks to your app:
  - heroku/python
  - https<span>://</span>github.com/jonathanong/heroku-buildpack-ffmpeg-latest.git
  - https<span>://</span>github.com/xrisk/heroku-opus.git
- Push to project files heroku

References
---
- [Discord.py](https://github.com/Rapptz/discord.py)
- [Documentation](https://discordpy.readthedocs.io/en/latest/index.html)
