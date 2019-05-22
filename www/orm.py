# -*- coding: utf-8 -*-

# __author__ = "GL Z"

import logging;logging.basicConfig(level=logging.INFO)
import asyncio, aiomysql

def log(sql, args=()):
	logging.info(f'SQL:{sql}')

async def create_pool(loop, **kw): # offer database connection for http request 
	logging.info('create database connection pool...')
	global __pool
	__pool = await aiomysql.create_pool(
		host = kw.get('host', 'localhost'),# return value of key 'host', if not available, 
										 # get value of default key (localhost)
		port = kw.get('port', 3306),#3306 refers to MySQL database server connections
		user = kw['user'],
		password = kw['password'],
		db = kw['db'],
		charset = kw.get('charset','utf8'),
		autocommit = kw.get('autocommit', True),
		maxsize = kw.get('maxsize', 10),
		minsize = kw.get('minsize', 1),
		loop = loop
		)

async def select(sql, args, size=None):
	log(sql, args)
	global __pool
	async with __pool.acquire() as conn:
		async with conn.cursor(aiomysql.DictCursor) as cur:
			await cur.execute(sql.replace('?','%s'),args or ())
			if size: 
				rs = await cur.fetchmany(size)
			else:
				rs = await cur.fetchall() # list of dicts
			#await cur.close()
			#conn.close()
		logging.info(f'rows returned:{len(rs)}')
		return rs 

async def execute(sql,args,autocommit=True):
	log(sql)
	async with __pool.acquire() as conn:
		if not autocommit:
			await conn.begin()
		try:
			async with conn.cursor(aiomysql.DictCursor) as cur:
				await cur.execute(sql.replace('?', '%s'), args)
				affected = cur.rowcount
			if not autocommit:
				await conn.commit()
				#conn.close()
		except BaseException as e:
			if not autocommit:
				await conn.rollback()
			raise
		return affected

def create_args_string(num):
	L = []
	for n in range(num):
		L.append('?')
	return ','.join(L)

class Field(object):
	def __init__(self, name, column_type, primary_key, default):
		self.name = name
		self.column_type = column_type
		self.primary_key = primary_key
		self.default = default

	def __str__(self):
		return f'<{self.__class__.__name__},{self.column_type}:{self.name}>'

class StringField(Field):
	def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
		super().__init__(name, ddl, primary_key, default)

class BooleanField(Field):
	def __init__(self, name=None, default=False):
		super().__init__(name, 'boolean', False, default)

class IntergerField(Field):
	def __init__(self, name=None, primary_key=False, default=0):
		super().__init__(name, 'bigint', primary_key, default)

class FloatField(Field):
	def __init__(self, name=None, primary_key=False, default=0.0):
		super().__init__(name, 'real', primary_key, default)

class TextField(Field):
	def __init__(self, name=None, default=None):
		super().__init__(name, 'text', False, default)

class ModelMetaclass(type):
	def __new__(cls, name, bases, attrs):
		if name=='Model':
			return type.__new__(cls, name, bases, attrs)
		tableName = attrs.get('__table__',None) or name #if __table__ is none, then get name
		logging.info(f'found model: {name} (table:{tableName})') 
		mappings = dict()
		fields = []
		primaryKey = None
		# find the primary key 
		for k, v in attrs.items():
			if isinstance(v, Field):
				logging.info(f'  found mapping:{k} ==> {v}')
				mappings[k] = v
				if v.primary_key:
					if primaryKey:
						raise Exception(f'duplicate primary key of field:{k}')
					primaryKey = k
				else:
					fields.append(k) 
		if not primaryKey:
			raise StandardError('primary key not found')
		for k in mappings.keys():
			attrs.pop(k) #pop out fields in attributes
		escaped_fields = list(map(lambda f:'`%s`'%f,fields))	
		attrs['__mappings__'] = mappings
		attrs['__table__'] = tableName
		attrs['__primary_key__'] = primaryKey
		attrs['__fields__'] = fields
		attrs['__select__'] = f"select `{primaryKey}`,{','.join(escaped_fields)} from `{tableName}`"
		attrs['__insert__'] = f"insert into `{tableName}` ({','.join(escaped_fields)}, `{primaryKey}`) values ({create_args_string(len(escaped_fields)+1)})"
		attrs['__update__'] = f"update `{tableName}` set {','.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f),fields))} where `{primaryKey}`=?"
		attrs['__delete__'] = f"delete from `{tableName}` where `{primaryKey}`=?"
		return type.__new__(cls, name, bases, attrs)

class Model(dict, metaclass=ModelMetaclass): # Model = Table

	def __init__(self,**kw):
		super(Model, self).__init__(**kw)

	def __getattr__(self, key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(f"'Model' object has no attribute '{key}' ")

	def __setattr__(self, key, value):
		self[key] = value

	def getValue(self, key):
		return getattr(self, key, None)

	def getValueOrDefault(self, key):
		value = getattr(self, key, None)
		if value is None:
			field = self.__mappings__[key]
			if field.default is not None:
				value = field.default() if callable(field.default) else field.default
				logging.debug(f'using default value for {key}: {str(value)}')
				setattr(self, key, value)
		return value

	@classmethod
	async def findAll(cls, where=None, args=None, **kw):
		sql = [cls.__select__]
		if where:
			sql.append('where')
			sql.append(where)
		if args is None:
			args = []
		orderBy = kw.get('orderBy', None)
		if orderBy:
			sql.append('order by')
			sql.append(orderBy)
		limit = kw.get('limit', None)
		if limit is not None:
			sql.append('limit')
			if isinstance(limit, int):
				sql.append('?')
				sql.append(limit)
			elif isinstance(limit, tuple) and len(limit)==2:
				sql.append('?','?')
				args.extend(limit)
			else:
				raise ValueError(f'Invalid limit value:{str(limit)}')
		rs = await select(' '.join(sql),args)
		return [cls(**r)for r in rs]

	@classmethod
	async def findNumber(cls, selectField, where=None, args=None):
		sql = [f'select {selectField} _num_ from {cls.__table__}']
		if where:
			sql.append('where')
			sql.append(where)
		rs = await select(' '.join(sql), args, 1)
		if len(rs) == 0:
			return None
		return rs[0]['_num_']

	@classmethod
	async def find(cls, pk):
		rs = await select(f'{cls.__select__} where `{cls.__primary_key__}`=?',[pk], 1)
		if len(rs) == 0:
			return None
		return cls(**rs[0])

	async def save(self):
		args = list(map(self.getValueOrDefault, self.__fields__))
		args.append(self.getValueOrDefault(self.__primary_key__))
		rows = await execute(self.__insert__, args)
		if rows != 1:
			logging.warn(f'failed to insert record: affected rows: {rows}')

	async def remove(self):
		args = [self.getValue(self.__primary_key__)]
		rows = await execute(self.__delete__, args)
		if rows != 1:
			logging.warn(f'failed to remove primary key: affected rows: {rows}')

	async def update(self):
		args = list(map(self.getValueOrDefault,self.__fields__))
		args.append(self.getValue(self.__primary_key__))
		rows = await execute(self.__update__, args)
		if rows !=1:
			logging.warn(f'failed to update by primary key, affected rows:{rows}')



