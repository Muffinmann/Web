# -*- coding: utf-8 -*-

import logging; logging.basicConfig(level=logging.INFO)
import asyncio, os, json, time
from datetime import datetime
from aiohttp import web

def index(request):
	return web.Response(body=b'<h1>es klappt</h1>',content_type='text/html')


async def init(loop):
	app = web.Application(loop=loop)
	app.router.add_route('GET','/',index)
	srv = await loop.create_server(app.make_handler(),'127.0.0.1',9000)
	logging.info('server started at httl://127.0.0.1:9000...')	
	return srv

loop = asyncio.get_event_loop()
'''
get the  current event loop. If there is no current event loop, a new event loop
will be created and setted as the current one
'''

loop.run_until_complete(init(loop))
'''
reutrn until the future(instance of Future) has completed.
------------------
A Future represents an eventual result if an asynchronous operation. It is an
awaitable object.
'''
loop.run_forever()


