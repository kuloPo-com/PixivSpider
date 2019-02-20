# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# hd8ttps://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class PixivItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    rankingtime = scrapy.Field()
    rank = scrapy.Field()
    ID = scrapy.Field()
    title = scrapy.Field()
    author = scrapy.Field()
    creationtime = scrapy.Field()
    byte = scrapy.Field()
    imgtype = scrapy.Field()