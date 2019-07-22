# -*- coding: utf-8 -*-
import logging
import pymysql
from twisted.enterprise import adbapi


class MySQLTwistedPipeline(object):
    def __init__(self, dbpool):
        self.dbpool = dbpool
        self.logger = logging.getLogger(__name__)

    # 导入设置
    @classmethod
    def from_settings(cls, settings):
        params = dict(
            host=settings['MYSQL_HOST'],
            port=settings['MYSQL_PORT'],
            db=settings['MYSQL_DB'],
            user=settings['MYSQL_USER'],
            passwd=settings['MYSQL_PASSWORD'],
            charset=settings['MYSQL_CHARSET'],
            cursorclass=pymysql.cursors.DictCursor,
            use_unicode=True,
        )
        # 连接数据池
        dbpool = adbapi.ConnectionPool('pymysql', **params)
        return cls(dbpool)

    def handle_error(self, failure, item, spider):
        self.logger.error(failure)

    def process_item(self, item, spider):
        save = self.dbpool.runInteraction(item.save_mysql, item)
        save.addErrback(self.handle_error, item, spider)
        return item
