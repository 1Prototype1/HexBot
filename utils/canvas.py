from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import math

import io
import aiohttp

async def member_banner(top='toptxt', bottom='bottomtxt', url='', txtcolor='#00ffff'):

	async with aiohttp.ClientSession() as session:
		async with session.get(url) as resp:
			im = Image.open(io.BytesIO(await resp.read()))

	# create heagon mask
	mask = Image.new('RGBA', im.size)
	d = ImageDraw.Draw(mask)
	xy = [ 
    ((math.cos(th) + 1) * 128, 
     (math.sin(th) + 1) * 128) 
    for th in [i * (2 * math.pi) / 6 for i in range(6)] 
    ]
	d.polygon(xy, fill='#fff')

	profile = Image.new('RGBA', im.size)
	profile.paste(im, (0, 0), mask)
	profile = profile.resize((150, 150))

	# get base image
	base = Image.open("utils/hex_banner.png").convert("RGBA")

	# make a blank image for the text, initialized to transparent text color
	txt = Image.new("RGBA", base.size, (255,255,255,0))

	# get a font
	fnt = ImageFont.truetype("utils/Nunito-Bold.ttf", 40)
	# get a drawing context
	d = ImageDraw.Draw(txt)
	# calculate center widths
	w_top, _ = d.textsize(top, font=fnt)
	w_bottom, _ = d.textsize(bottom, font=fnt)
	# write texts
	d.text(((600-w_top)//2,10), top, font=fnt, fill=txtcolor)
	d.text(((600-w_bottom)//2,240), bottom, font=fnt, fill=txtcolor)

	out = Image.alpha_composite(base, txt)
	out.paste(profile, (225, 75), profile)

	# out.show()
	return out