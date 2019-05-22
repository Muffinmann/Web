# -*- coding: utf-8 -*-

import logging; logging.basicConfig(level=logging.INFO)
import asyncio
import os
import json
import time
from datetime import datetime
from aiohttp import web
from jinja2 import Environment, FileSystemLoader
import orm
from coroweb import add_routes, add_static

def init_jinja2(app, **kw):
	logging.info('initionalize jinja2...')
	options = dict(
		autoescape = kw.get('autoescape', True),
		block_start_string = kw.get('block_start_string', '{%'),
		block_end_string = kw.get('block_end_string', '%}'),
		variable_start_string = kw.get('variable_start_string', '{{'),
		variable_end_string = kw.get('variable_end_string','}}'),
		auto_reload = kw.get('auto_reload', True)
		)
	path = kw.get('path', None)
	if path is None:
		path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'templates')
	logging.info(f'set jinja2 template path:{path}')
	env = Environment(loader=FileSystemLoader, **options)
	filters = kw.get('filters', None)
	if filters is not None:
		for name, f in filters.items():
			env.filters[name] = f
	app['__templating__'] = env

async def logger_factory(app, handler):
	async def loggerr(request):
		logging.info(f'Request: {request.method} {request.path}')
		return await handler(request)
	return logger 

async def data_factory(app, handler):
	async def parse_data(request):
		if request.method == 'POST':
			if request.content_type.startswith('application/json'):
				request.__data__ = await request.json()
				logging.info(f'request json: {str(request.__data__)}')
			elif request.content_type.startswith('application/x-www-form-urlencoded'):
				request.__data__ = await request.post()
				logging.info(f'request form: {str(request.__data__)}')
			return await handler(request)
	return parse_data

async def response_factory(app, handler):
	async def response(request):
		logging.info('Response handler...')
		r = await handler(request)
		if isinstance(r, web.StreamResponse):
			return r
		if isinstance(r, bytes):
			resp = web.Response(body=r)
			resp.content_type = 'application/octet-strea'
			return resp
		if isinstance(r, str):
			if r.startswith('redirect:'):
				return web.HTTPFound(r[9:])
			resp = web.Response(body=r.encode('utf-8'))
			resp.content_type = 'text/html;charset=utf-8'
			return resp
		if isinstance(r, dict):
			template = r.get('__template__')
			if template is None:
				resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'))
				resp.content_type = 'application/json;charset=utf-8'
				return resp
			else:
				resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
				resp.content_type = 'text/html;charset=utf-8'
				return resp
		if isinstance(r, int) and r >= 100 and r < 600: # status code, int type
			return web.Response(r)
		if isinstance(r, tuple) and len(r) == 2:
			t, m = r
			if isinstance(t, int) and t >= 100 and t < 600:
				return web.Response(t, str(m))
		#default
		resp = web.Response(body=str(r).encode('utf-8'))
		resp.content_type = 'text/plain;charset=utf-8'
		return resp
	return response

def datetime_filter(t):
	delta = int(time.time()-t)
	if delta < 60:
		return '1 minute ago'
	if delta < 3600:
		return f'{delta//60} minutes ago'
	if delta < 86400:
		return f'{delta//3600} hours ago'
	if delta < 604800:
		return f'{delta//86400} days ago'
	dt = datetime.fromtimestamp(t)
	return f'{dt.day},{dt.month},{dt.year}'

async def init(loop):
	await orm.create_pool(loop=loop, host='localhost', user='conner', password='_Zhang5850_', db='WebBlog')
	app = web.Application(loop=loop, middlewares=[logger_factory, response_factory])
	init_jinja2(app, filters=dict(datetime=datetime_filter))
	add_routes(app, 'handlers')
	add_static(app)
	runner = web.AppRunner(app)
	await runner.setup()
	srv = await loop.create_server(runner.server, '127.0.0.1', 9000)
	logging.info(f'server started at http://127.0.0.1:9000...')
	return srv

