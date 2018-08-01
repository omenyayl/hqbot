import asyncio
from aiohttp import ClientSession
from pyppeteer import launch
from urllib.parse import quote

GOOGLE_DESCRIPTION_SELECTOR = '.s > div'
GOOGLE_URL_SELECTOR = '.r a'


def make_multiple_requests(urls):
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(run(urls))
    res = loop.run_until_complete(future)
    return res


def google_search(query):
    query = quote(query)
    google_search_url = f'https://www.google.com/search?rlz=1C5CHFA_enUS792US792&ei=roAiW_b3NuLs5gKU86PYCA&q=' \
                        f'{query}&oq={query}&gs_l=psy-ab.3..35i39k1j0i20i264k1l2j0i131k1j0l6.5438.6186.0.6269.6.6.0.0' \
                        f'.0.0.67.387.6.6.0....0...1c.1.64.psy-ab..0.6.384...0i67k1j0i20i263k1j0i10k1.0.2RylZe5zapg '
    urls = asyncio.get_event_loop().run_until_complete(make_google_search_request(google_search_url))
    return urls


async def fetch(url, session):
    try:
        async with session.get(url, timeout=1.5) as response:
            print(f'Successfully requested {url}')
            return await response.read()
    except asyncio.TimeoutError:
        return None


async def run(urls):
    tasks = []

    async with ClientSession() as session:
        for url in urls:
            task = asyncio.ensure_future(fetch(url, session))
            tasks.append(task)

        responses = await asyncio.gather(*tasks)
        return responses


async def make_google_search_request(search_url):
    browser = await launch()
    page = await browser.newPage()
    await page.goto(search_url)

    scraped_data = []
    url_elements = await page.querySelectorAll(GOOGLE_URL_SELECTOR)
    desc_elements = await page.querySelectorAll(GOOGLE_DESCRIPTION_SELECTOR)
    for url_element, desc_element in zip(url_elements, desc_elements):
        url = await page.evaluate('(element) => element.getAttribute("href")', url_element)
        des = await page.evaluate('(element) => element.textContent', desc_element)
        scraped_data.append({
            'url': url,
            'description': des
        })
    await browser.close()
    return scraped_data
