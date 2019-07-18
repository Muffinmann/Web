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

import markdown
from aiohttp import web

from coroweb import get, post
from apis import Page, APIError, APIValueError, APIResourceNotFoundError

from models import User, Comment, Blog, next_id
from config import configs


COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

def check_admin(request):
	if request.__user__ is None or not request.__user__.admin:
		raise APIPermissionError()

def get_page_index(page_str):
	p = 1
	try:
		p = int(page_str)
	except ValueError as e:
		pass
	if p < 1:
		p = 1
	return p

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
	if not cookie_str: 
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
		logging.exception(e)
		return None

def text2html(text):
	lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
	return ''.join(lines)
#user interface apis
@get('/')
async def index(request,*, page='1'):
	page_index = get_page_index(page)
	num = await Blog.findNumber('count(id)')
	p = Page(num, page_index)
	if num == 0:
		blogs = []
	else:
		blogs = await Blog.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
	return{
		'__template__': 'blogs.html',
		'page': p,
		'blogs': blogs,
		'__user__': request.__user__
	}

@get('/blog/{id}')
async def get_blog(request, *, id): 
	blog = await Blog.find(id)
	comments = await Comment.findAll('blog_id=?', [id], orderBy='created_at desc')
	for c in comments:
		c.html_content = markdown.markdown(c.content)
	blog.html_content = markdown.markdown(blog.content)
	return{
	'__template__': 'blog.html',
	'blog':blog,
	'comments': comments,
	'__user__': request.__user__
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

#management apis
@get('/manage/')
def manage():
	return 'redirect:/manage/comments'

@get('/manage/comments')
def manage_comments(*, page='1'):
	return{
	'__template__': 'manage_comments.html',
	'page_index': get_page_index(page)
	}

@get('/manage/blogs')
def manage_blogs(*, page='1'):
	return{
		'__template__': 'manage_blogs.html',
		'page_index': get_page_index(page)
	}

@get('/manage/blogs/create')
def manage_create_blog():
	return{
		'__template__':'manage_blog_edit.html',
		'id':'',
		'action':'/api/blogs'
	}

@get('/manage/blogs/edit')
def manage_edit_blog(*, id):
	return{
	'__template__':'manage_blog_edit.html',
	'id': id,
	'action': f'/api/blogs/{id}'
	}

@get('/manage/users')
def manage_users(*, page='1'):
	return{
	'__template__': 'manage_users.html',
	'page_index': get_page_index(page)
	}

#back end apis
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
	#user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image=f'https://www.gravatar.com/avatar/{hashlib.md5(email.encode('utf-8')).hexdigest()}?d=retro&s=120')
	user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
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
	page_index = get_page_index(page)
	num = await User.findNumber('count(id)')
	p = Page(num, page_index)
	if num == 0:
		return dict(page=p, users=())
	users = await User.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
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
				name=name.strip(),
				summary=summary.strip(),
				content=content.strip())
	await blog.save()
	return blog

@post('/api/blogs/{id}')
async def api_update_blog(id, request, *, name, summary, content):
	check_admin(request)
	blog = await Blog.find(id)
	if not name or not name.strip():
		raise APIValueError('name', 'name can not be empty.')
	if not summary or not summary.strip():
		raise APIValueError('summary', 'summary can not be empty.')
	if not content or not content.strip():
		raise APIValueError('content', 'content can not be empty.')
	blog.name = name.strip()
	blog.summary = summary.strip()
	blog.content = content.strip()
	await blog.update()
	return blog

@post('/api/users/{id}/delete')
async def api_delete_users(id, request):
	check_admin(request)
	id_buff = id
	user = await User.find(id)
	if user is None:
		raise APIResourceNotFoundError('Comment')
	await user.remove()
	comments = await Comment.findAll('user_id=?',[id])
	if comments:
		for comment in comments:
			id = comment.id
			c = await Comment.find(id)
			c.user_name = c.user_name + 'the user is not existed anymore'
			await c.update()
	id = id_buff
	return dict(id=id)

@get('/api/comments')
async def api_comments(*, page='1'):
	page_index = get_page_index(page)
	num = await Comment.findNumber('count(id)')
	p = Page(num, page_index)
	if num == 0:
		return dict(page=p, comments=())
	comments = await Comment.findAll(orderBy='created_at desc',limit=(p.offset, p.limit))
	return dict(page=p, comments=comments)

@post('/api/blogs/{id}/comments')
async def api_create_comment(id, request, *, content):
	user = request.__user__
	if user is None:
		raise APIPermissionError('Please singin before comment.')
	if not content or not content.strip():
		raise APIValueError('content')
	blog = await Blog.find(id)
	if blog is None:
		raise APIResourceNotFoundError('Blog')
	comment = Comment(blog_id=blog.id, user_id=user.id, user_name=user.name, user_image=user.image, content=content.strip())
	await comment.save()
	return comment

@get('/api/blogs')
async def api_blogs(*, page='1'):
	page_index = get_page_index(page)
	num = await Blog.findNumber('count(id)')
	p = Page(num, page_index)
	if num == 0:
		return dict(page=p, blogs=())
	blogs = await Blog.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
	return dict(page=p, blogs=blogs)

@get('/api/blogs{id}')
async def api_get_blog(*, id):
	blog = await Blog.find(id)
	return blog
