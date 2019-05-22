import orm, asyncio
from models import User, Blog, Comment
print(User.__mappings__)
print(Blog.__mappings__)
'''
async def test(loop):
        await orm.create_pool(user='conner',password='_Zhang5850_',db='WebBlog',loop=loop,autocommit=True)
        u = User(name='test',email='test@email.com',passwd='123test456',image='about:blank')
        print(User.__mappings__)
        print(u.__mappings__)
        print(u.__insert__)
        # insert into `users` (`email`,`admin`,`name`,`image`,`created_at`, `id`) values (?,?,?,?,?,?)
        await u.save()
        

loop = asyncio.get_event_loop()


loop.run_until_complete(test(loop))
'''
