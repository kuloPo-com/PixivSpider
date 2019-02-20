import scrapy
import pymysql
import requests
import re
from PIL import Image
from io import BytesIO
from base64 import b64encode

from pixiv.items import PixivItem


class PixivSpider(scrapy.Spider):
	name = "Pixiv"
	allowed_domains = ['www.pixiv.net']
	date = "20150101"
	db = pymysql.connect("127.0.0.1","root","PASSWORD","Pixiv",charset="utf8mb4")
	cursor = db.cursor()
	cursor.execute("CREATE TABLE IF NOT EXISTS Settings(ID VARCHAR(2) NOT NULL, date VARCHAR(8) NOT NULL, PRIMARY KEY(ID)) ENGINE = MyISAM DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;")
	cursor.execute("CREATE TABLE IF NOT EXISTS IndexbyDate(rankingtime VARCHAR(8) NOT NULL, rank VARCHAR(2) NOT NULL, ID VARCHAR(8) NOT NULL, title VARCHAR(32) NOT NULL, author VARCHAR(32) NOT NULL, creationtime VARCHAR(32) NOT NULL) ENGINE = MyISAM DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;")
	cursor.execute("CREATE TABLE IF NOT EXISTS Pic(ID VARCHAR(8) NOT NULL, imgtype VARCHAR(3) NOT NULL, byte MEDIUMTEXT NOT NULL, PRIMARY KEY(ID)) ENGINE = MyISAM DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;")
	if cursor.execute("SELECT * FROM Settings WHERE ID=1;") == 1:
		date = cursor.fetchone()[1]
	else:
		cursor.execute("INSERT INTO Settings(ID,date) VALUES ('%s','%s');" % ("1",date))
	start_urls = ["https://www.pixiv.net/ranking.php?mode=daily&date="+date]

	def DownloadPic(self, imgurl, picinfo):
		downloadhead = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36', 'Accept-Encoding': 'gzip, deflate, sdch, br', 'Referer': 'https://www.pixiv.net/member_illust.php?mode=medium&illust_id='+picinfo["ID"], 'Accept-Language': 'zh-CN,zh;q=0.8', 'Host': 'i.pximg.net', 'Connection': 'keep-alive', 'Accept': 'image/webp,image/*,*/*;q=0.8'} 
		try:
			r = requests.get(imgurl, headers = downloadhead, timeout=60)
		except requests.exceptions.ConnectTimeout:
			print("Timeout")
			DownloadPic(imgurl)
		if r.status_code == 200:#if jpg
			byte = r.content
			r.close()
		elif r.status_code == 404:#if png
			r.close()
			imgurl = imgurl.replace(".jpg",".png")
			try:
				r = requests.get(imgurl, headers = downloadhead, timeout=60)
			except requests.exceptions.ConnectTimeout:
				print("Timeout")
				DownloadPic(imgurl)
			byte = r.content
			r.close()
		else:
			print("Failed with status code:", r.status_code)
			r.close()
		return byte

	def NextDate(self, date):
		MONTH = [0,31,28,31,30,31,30,31,31,30,31,30,31]
		if int(date[6:8]) < MONTH[int(date[4:6])]:
			day = int(date[6:8]) +1
			if day < 10:
				date = date[:-2] + "0" + str(day)
			else:
				date = date[:-2] + str(day)
		elif int(date[4:6]) != 2 and int(date[4:6]) != 12:
			month = int(self.date[4:6]) + 1
			if month < 10:
				date = date[:4] + "0" + str(month) + "01"
			else:
				date = date[:4] + str(month) + "01"
		elif int(date[4:6]) == 12:
			date = str(int(date[:4]) + 1) + "0101"
		elif int(date[4:6]) == 2:
			year = int(date[:4])
			if ((year % 4 ==0 and year % 100 != 0) or year % 400 == 0):
				if int(date[6:8]) == 28:
					date = str(year) + "0229"
				else:
					date = str(year) + "0301"
			else:
				date = str(year) + "0301"
		return date

	def parse(self, response):
		db = pymysql.connect("127.0.0.1","root","PASSWORD","Pixiv",charset="utf8mb4")
		cursor = db.cursor()
		for rank in range(1,11):#Get top 10
			picinfo = {}
			picinfo["rankingtime"] = self.date
			picinfo["rank"] = str(rank)
			url = response.xpath("/html/body/div[@id='wrapper']/div[@class='layout-body']/div[@class='_unit']/div[@class='ranking-items-container']/div[@class='ranking-items adjust']/section[@id='"+str(rank)+"']/div[@class='ranking-image-item']/a/@href").extract() #Get detail url 
			if url != []:#if Pic exist
				picinfo["ID"] = url[0][-8:]
				detail = response.xpath("/html/body/div[@id='wrapper']/div[@class='layout-body']/div[@class='_unit']/div[@class='ranking-items-container']/div[@class='ranking-items adjust']/section[@id="+str(rank)+"]").extract()[0]
				picinfo["rank"] = re.search(r"data-rank=\"(\d+)\"",detail).group(1)
				picinfo["title"] = re.search(r"data-title=[\",\'](.*?)[\",\']",detail).group(1)
				picinfo["author"] = re.search(r"data-user-name=\"(.*?)\"",detail).group(1)
				picinfo["creationtime"] = re.search(r"data-date=\"(.*?)\"",detail).group(1).replace("年","-").replace("月","-").replace("日","")
				if cursor.execute("SELECT * FROM Pic WHERE ID=%s;" % picinfo["ID"]) == 0:#Pic show up first time
					imgurl = response.xpath("/html/body/div[@id='wrapper']/div[@class='layout-body']/div[@class='_unit']/div[@class='ranking-items-container']/div[@class='ranking-items adjust']/section[@id='"+str(rank)+"']/div[@class='ranking-image-item']/a/div[@class='_layout-thumbnail']/img").extract()[0]
					imgurl = re.search(r"data-src=\"(.*?)\"",imgurl).group(1).replace("/c/240x480/img-master","/img-original").replace("p0_master1200","p0")					
					byte = self.DownloadPic(imgurl, picinfo)
					picinfo["byte"] = b64encode(byte).replace(b"/",b"#")
					picinfo["imgtype"] = imgurl[-3:]
				else:
					picinfo["imgtype"] = "dup"
			else:#Pic deleted
				picinfo["ID"] = "ERROR"
				picinfo["title"] = picinfo["author"] = picinfo["creationtime"] = ""
			print(picinfo["rankingtime"],",",picinfo["rank"],",",picinfo["title"],",",picinfo["author"])
			if cursor.execute("SELECT * FROM IndexbyDate WHERE rankingtime=%s AND rank=%s" % (picinfo["rankingtime"],picinfo["rank"])) == 0:
				yield picinfo
		self.date = self.NextDate(self.date)
		cursor.execute("UPDATE Settings SET date='%s' WHERE ID=1;" % self.date)
		next_page = "https://www.pixiv.net/ranking.php?mode=daily&date="+self.date
		yield scrapy.Request(next_page, callback=self.parse)
		