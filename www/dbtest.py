import orm
import asyncio
from models import User, Blog, Comment


async def test(loop):
    await orm.create_pool(loop, user='conner',host='localhost',password='_Zhang5850_',
                          db='WebBlog')
    #u = User(name='test',email='test@email.com',passwd='pwtest',image='about:blank')
    #await u.save()
    
    
    u = await User.find('001556958860000658f886093ef4082b579ae2914b0cee9000')

    
    u.passwd = '123pw456'
    
    args = list(map(u.getValueOrDefault,u.__fields__))
    #pk = u.getValue(u.__primary_key__)
    args.append(u.getValue(u.__primary_key__))
    print(args)
    print(u.__update__)
    await u.update()
    
loop = asyncio.get_event_loop()
loop.run_until_complete(test(loop))
