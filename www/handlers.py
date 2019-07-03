 #!/usr/bin/env python3
# -*- coding:utf-8 -*-
# TODO checke the source of 'index' func in dir(handlers)
import re
import time
import json
import logging
import hashlib
import base64
import asyncio

from aiohttp import web

from coroweb import get, post
from apis import APIValueError, APIResourceNotFoundError

from models import User, Comment, Blog, next_id
from config import configs

COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

def check_admin(request):
	if request.__user__ is None or not request.__user__.admin:
		raise APIPermissionError()

def user2cookie(user, max_age):
	"""
	Generate cookie str by user
	"""
	# build cookie string by: id-expires-sha1
	expires = str(int(time.time()+max_age))
	s = f'{user.id}-{user.passwd}-{expires}-{_COOKIE_KEY}'
	L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
	return '-'.join(L)

async def cookie2user(cookie_str):
	"""
	Parse cookie and load user if cookie is valid
	"""
	if not cookit_str:
		return None
	try:
		L = cookie_str.split('-')
		if len(L) != 3:
			return None
		uid, expires, sha1 = L
		if int(expires) < time.time():
			return None
		user = await User.find(uid)
		if user is None:
			return None
		s = f'{uid}-{user.passwd}-{expires}-{_COOKIE_KEY}'
		if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
			logging.info('invalid sha1')
			return None
		user.passwd = '******'
		return user
	except Exception as e:
		logging,exception(e)
		return None


@get('/')
async def index(request):
	users = await User.findAll()
	summary ='This is a summary of test blogs'
	blogs = [
		Blog(id='1', name='Test Blog', summary=summary, created_at=time.time()-120),
		Blog(id='2', name='Something new', summary=summary, created_at=time.time()-3600),
		Blog(id='3', name='Web dev', summary=summary, created_at=time.time()-7200),
		
	]
	return{
		'__template__': 'blogs.html',
		'blogs': blogs
	}

@get('/register')
def register():
	return{
		'__template__': 'register.html'
	}

@get('/signin')
def signin():
	return{
		'__template__': 'signin.html'
	}

@get('/signout')
def signout(request):
	referer = request.headers.get('Referer')
	r = web.HTTPFound(referer or '/')
	r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
	logging.info('user signed out.')
	return r

@post('/api/authenticate')
async def authenticate(*, email, passwd):
	if not email:
		raise APIValueError('email', 'Invalid email.')
	if not passwd:
		raise APIValueError('passwd', 'Invalid password.')
	users = await User.findAll('email=?',[email])
	if len(users) == 0:
		raise APIValueError('email','Email not exist.')
	user = users[0]
	#check passwd:
	sha1 = hashlib.sha1()
	sha1.update(user.id.encode('utf-8'))
	sha1.update(b':')
	sha1.update(passwd.encode('utf-8'))
	if user.passwd != sha1.hexdigest():
		raise APIValueError('passwd', 'Invalid password.')
	r = web.Response()
	r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
	user.passwd= '******'
	r.conten_type = 'application/json'
	r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r 

@post('/api/users')
async def api_register_user(*, email, name, passwd):
	if not name or not name.strip():
		raise APIValueError('name')
	if not email or not _RE_EMAIL.match(email):
		raise APIValueError('email')
	if not passwd or not _RE_SHA1.match(passwd):
		raise APIValueError('passwd')
	users = await User.findAll('email=?',[email])
	if len(users) > 0:
		raise APIError('register:failed', 'email', 'Email is already in use.')
	uid = next_id()
	sha1_passwd = f'{uid}:{passwd}'
	user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image=f'https://www.gravatar.com/avatar/{hashlib.md5(email.lower()).hexdigest()}?d=retro&s=120' )
	await user.save()
	# make session cookie:
	r = web.Response()
	r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
	user.passwd = '******'
	r.conten_type = 'application/json'
	r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r

@get('/api/users')
async def api_get_users():
	users = await User.findAll(orderBy='created_at desc')
	for u in users:
		u.passwd = '******'
	return dict(users=users)

@post('/api/blogs')
async def api_create_blog(request, *, name, summary, content):
	check_admin(request)
	if not name or not name.strip():
		raise APIValueError('name', 'name can not be empty.')
	if not summary or not summary.strip():
		raise APIValueError('summary', 'summary can not be empty.')
	if not content or not content.strip():
		raise APIValueError('content', 'content can not be empty.')
	blog = Blog(user_id=request.__user__.id,
				user_name=request.__user__.name,
				user_image=request.__user__.image,
				name=name.strp(),
				summary=summary.strip(),
				content=content.strip())
	await blog.save()
	return blog


@get('/manage/blogs/create')
def manage_create_blog():
	return{
		'__template__':'manage_blog_edit.html',
		'id':'',
		'action':'api/blogs'
		#'page_index':get_page_index(page)
	}