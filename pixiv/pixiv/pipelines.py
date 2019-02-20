# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html
from twisted.enterprise import adbapi
import pymysql
import pymysql.cursors

from pixiv.spiders.PixivSpider import PixivSpider

class PixivPipeline(object):
	def __init__(self):
		self.dbpool = adbapi.ConnectionPool("pymysql",
			db = 'Pixiv',
			user = 'root',
			passwd = 'PASSWORD',
			charset = 'utf8mb4',
			cursorclass = pymysql.cursors.DictCursor,
			use_unicode = True,
		)


	
	def process_item(self, item, spider):
		query = self.dbpool.runInteraction(self.insert_into_table,item)
		return item
	
	def insert_into_table(self,conn,item):
		conn.execute("insert into IndexbyDate(rankingtime,rank,ID,title,author,creationtime) values('%s','%s','%s','%s','%s','%s');" % (item['rankingtime'],item['rank'],item['ID'],item['title'],item['author'],item['creationtime']))
		if item['ID'] != "ERROR" and item['imgtype'] != "dup":
			conn.execute('insert into Pic(ID,imgtype,byte) values("%s","%s","%s");' % (item['ID'],item['imgtype'],item['byte']))