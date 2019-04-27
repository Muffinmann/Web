# -*- coding: utf-8 -*-

import logging; logging.basicConfig(level=logging.INFO)
import asyncio, os, json, time
from datetime import datetime
from aiohttp import web

def index(request):
	return web.Response(text='first step',content_type='text/html')
	# inherited from StreamResponse
	# accepts body argument for setting
	# the HTTP response BODY

async def init(loop):
	app = web.Application(loop=loop) # Application is a synonym for web-server
	app.router.add_route('GET','/',index)
	#app.add_routes([web.get('/', index)]) # []:=list of Resources, is an entry
										  # in route table

	### !!! Deprecated use of make_handler!!!###
	#srv = await loop.create_server(app.make_handler(),'127.0.0.1',9000)
	runner = web.AppRunner(app)
	await runner.setup()
	srv = await loop.create_server(runner.server,'127.0.0.1',9000)
	# create a TCP server(socket type SOCK_STREAM) listening on port of the host 
	# address
	logging.info('server started at http://127.0.0.1:9000...')	
	return srv

loop = asyncio.get_event_loop()
# get the  current event loop. If there is no current event loop, a new event loop
# will be created and setted as the current one

loop.run_until_complete(init(loop))
# reutrn until the future(instance of Future) has completed.
# ------------------
# A Future represents an eventual result if an asynchronous operation. It is an
# awaitable object.

loop.run_forever()




# Handler: are set up to handle requests by registering them with the add_routes() on
# a particular route(HTTP method and path pair: GET /path HTTP/1.1 ) using helpers like
# get() and post()
# async def handler(request):
#    return web.Response()
##############################
# http request:              #
# method: GET or POST        #
# path: /full/url/path       #
# domain: Host:www.xxx.com   #
# Header1: Value1            #
# Header2: Value2 			 #
#	\r\n					 #
#	\r\n					 #
# boday data...              #
##############################

