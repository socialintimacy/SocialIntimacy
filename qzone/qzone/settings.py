# -*- coding: utf-8 -*-

BOT_NAME = 'qzone'

SPIDER_MODULES = ['qzone.spiders']
NEWSPIDER_MODULE = 'qzone.spiders'

ROBOTSTXT_OBEY = False

# 下载延迟
DOWNLOAD_DELAY = 3

DEFAULT_REQUEST_HEADERS = {
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
  'Accept-Language': 'zh-CN,zh;q=0.9',
  'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.67 Safari/537.36',
}

ITEM_PIPELINES = {
   'qzone.pipelines.MySQLTwistedPipeline': 300,
}

# 默认开启自动限速,未测试不限速是否会被反爬
AUTOTHROTTLE_ENABLED = True

# 配置MySQL
MYSQL_HOST = 'localhost'
MYSQL_DB = 'qzone'
MYSQL_USER = 'user'
MYSQL_PASSWORD = 'password'
MYSQL_PORT = 3306
MYSQL_CHARSET = 'utf8'