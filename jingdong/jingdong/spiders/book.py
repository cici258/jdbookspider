# -*- coding: utf-8 -*-
import scrapy
from copy import deepcopy
import json


class BookSpider(scrapy.Spider):
    name = 'book'
    allowed_domains = ['jd.com','p.3.cn']
    start_urls = ['https://book.jd.com/booksort.html']

    def parse(self, response):      # 大分类列表
        dt_list = response.xpath("//div[@class='mc']/dl/dt")
        for dt in dt_list:
            item = {}
            item["b_cate"] = dt.xpath("./a/text()").extract_first()
            em_list = dt.xpath("./following-sibling::dd[1]/em")
            for em in em_list:
                item["s_href"] = em.xpath("./a/@href").extract_first()
                item["s_cate"] = em.xpath("./a/text()").extract_first()
                if item["s_href"]:
                    item["s_href"] = 'https:' + item["s_href"]
                    yield scrapy.Request(
                        item["s_href"],
                        callback=self.parse_book_list,
                        meta={"item": deepcopy(item)}
                    )

    def parse_book_list(self,response):  # 解析图书详情页
        item = response.meta["item"]
        li_list = response.xpath("//ul[@class='gl-warp clearfix']/li")
        for li in li_list:
            item["book_img"] = li.xpath(".//div[@class='p-img']//img/@src").extract_first()

            # 反爬措施  图片链接有两个标签 src和data-lazy-img
            if item["book_img"] is None:
                item["book_img"] = li.xpath(".//div[@class='p-img']//img/@data-lazy-img").extract_first()
            item["book_img"] = 'https:' + item["book_img"] if item["book_img"] is not None else None
            item["book_name"] = li.xpath(".//div[@class='p-name']//em/text()").extract_first().strip() # strip()方法去掉空格
            item["book_author"] = li.xpath(".//span[@class='author_type_1']/a/text()").extract()
            item["book_press"] = li.xpath(".//span[@class='p-bi-store']/a/text()").extract_first()
            item["book_publish_data"] = li.xpath(".//span[@class='p-bi-date']/text()").extract_first().strip()
            item["book_sku"] = li.xpath("./div/@data-sku").extract_first()

            yield scrapy.Request(
                "https://p.3.cn/prices/mgets?skuIds=J_{}".format(item["book_sku"]),
                callback=self.parse_book_price,
                meta={"item":deepcopy(item)}
            )

        # 翻页
        next_url = response.xpath("//a[class='pn-next']/@href").extract_first()
        if next_url is not None:
            next_url = "https://list.jd.com" + str(next_url)
            yield scrapy.Request(
                next_url,
                callback=self.parse_book_list,
                meta={"item":item}
            )

    def parse_book_price(self,response):
        item = response.meta["item"]
        result = json.loads(response.body.decode())
        item["book_price"] = result[0]["op"]

        # 把最终的数据送到pipeline
        yield item