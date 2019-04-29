#  Notes for web dev
---
## HTTP processes flow
1. HTTP request:
	1. METHODS: *GET* or *POST*; *GET* method just requests for resource while *POST* method is attached with user data
	2. PATH: */full/url/path*
	3. DOMAIN: *HOST: www.xxx.com*
	4. related HEADERs
	5. in case of *POST* request, user data will be included in ***Body***

	> FORMAT:  
	GET /path HTTP/1.1
	Header1: Value1
	Header2: Value2
	Header3: Value3
	\r\n\r\n
	***Body data*** (only for *POST* method)

2. HTTP response:
	1. RESPONSE CODE: *200* means successful response; *3xx* means redirect; *4xx* means erro occured in ***Client***; *5xx* means error occured in ***Server***
	2. RESPONSE TYPE: defined by *Content-Type*
	3. related HEADERS
	4. usually the response of a server has a ***Body***

	>FORMAT:
	200 OK
	Header1: Value1
	Header2: Value2
	Header3: Value3
	\r\n\r\n
	***Body data***

3. If Broser requests for other resources, repeat step 1&2

### aiohttp 
	[LINK](https://demos.aiohttp.org/en/latest/tutorial.html)

---
## ORM
1. connct to data base
2. create Model(= table)
3. alter SQL operations(CRUD) into Object Methods
4. Relation type: 1-1, 1-n, n-n; for n-n type an extra middle-table will be needed 




