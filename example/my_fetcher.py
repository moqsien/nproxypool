import requests
from scrapy import Selector
from urllib.parse import urljoin
from user_agent import generate_user_agent
from nproxypool.base.db import RedisPool
from nproxypool.base.proxy_fetcher import ProxyFetcherBase


class ProxyFetcherIhuan(ProxyFetcherBase):
    def __init__(self, **kwargs):
        super(ProxyFetcherIhuan, self).__init__(**kwargs)
        self._url = 'https://ip.ihuan.me/'
        self._user_agent = generate_user_agent(os='win')

    def run(self):
        headers = {
            'user-agent': self._user_agent
        }
        r = requests.get(self._url, headers=headers)
        s = Selector(text=r.text)
        page_list = s.xpath('//ul[@class="pagination"]//a/@href').extract()
        for _url in page_list:
            url = urljoin(self._url, _url)
            r = requests.get(url, headers=headers)
            s = Selector(text=r.text)
            labels = s.xpath('//div[@class="table-responsive"]//tr')
            for tr in labels:
                ip = tr.xpath('./td[1]/a/text()').get()
                port = tr.xpath('./td[2]/text()').get()
                if ip and port:
                    proxy = f'{ip}:{port}'
                    self._client.insert_one(proxy)


class ProxyFetcherRedis(ProxyFetcherBase):
    def __init__(self, **kwargs):
        super(ProxyFetcherRedis, self).__init__(**kwargs)

    def run(self):
        params = dict(
            host='127.0.0.1',
            port=6379,
            password='xxxx',
            db=0
        )
        r = RedisPool(**params)
        proxies = r.get_all()
        for proxy in proxies:
            self._client.insert_one(proxy)


if __name__ == '__main__':
    p = ProxyFetcherIhuan()
    p.run()
