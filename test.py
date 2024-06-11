import asyncio
import aiohttp


async def post(url, data=None, headers=None, params=None):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers, params=params) as response:
            if response.status == 200:
                content_type = response.headers.get('Content-Type', '').lower()
                if 'application/json' in content_type:
                    return await response.json()
                elif 'text/html' in content_type:
                    return await response.text()
                else:
                    return await response.read()
            raise Exception(f"Failed to post to {url}: Status code {response.status}")


if __name__ == '__main__':

    urls = ['https://maps.app.goo.gl/2pESDWwG8kqeDM2i8', 'https://goo.gl/maps/hAtDDEUiozVVUWQd6']
    for url in urls:
        asyncio.run(redis.push({'request_id': request_id, 'url': url, 'retry': 0}))

    exists = asyncio.run(redis.exists(request_id))
    if not exists:
        asyncio.run(redis.set(request_id, len(urls)))
