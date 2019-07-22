# -*- coding: utf-8 -*-

from scrapy import Item, Field


class MsgItem(Item):
    # 留言id, 主键
    id = Field()
    # 留言对象账号
    uin = Field()
    # 留言作者账号
    m_uin = Field()
    # 留言时间, 格式为标准时间
    created_time = Field()
    content = Field()

    def save_mysql(self, cursor, item):
        # 忽略已存在的数据
        uin = self['uin']
        id = self['id']
        m_uin = self['m_uin']
        created_time = self['created_time']
        content = self['content']
        sql = f"INSERT IGNORE INTO Msg(uin, id, m_uin, created_time, content) VALUES ('{uin}','{id}','{m_uin}','{created_time}','{content}')"
        cursor.execute(sql)


class AccountItem(Item):
    # 好友账号, 主键
    uin = Field()
    age = Field()
    birthday = Field()
    birthyear = Field()
    sex = Field()
    nickname = Field()
    # 与本人的亲密度
    score = Field()

    def save_mysql(self, cursor, item):
        # 忽略已存在的数据
        uin = self['uin']
        age = self.get('age')
        birthday = self.get('birthday')
        birthyear = self.get('birthyear')
        sex = self.get('sex')
        nickname = self['nickname']
        score = self.get('score')
        sql = f"INSERT IGNORE INTO Account(uin, age, birthday, birthyear, sex, nickname, score) VALUES ('{uin}','{age}','{birthday}','{birthyear}','{sex}','{nickname}','{score}')"
        cursor.execute(sql)


class Taotaoitem(Item):
    # 说说作者
    uin = Field()
    content = Field()
    # 说说来源(手机型号, 平板型号等)
    source = Field()
    # 说说发布时间, 格式为标准时间
    created_time = Field()
    # 说说id, 主键
    id = Field()

    def save_mysql(self, cursor, item):
        # 忽略已存在的数据
        uin = self['uin']
        content = self.get('content')
        source = self.get('source')
        created_time = self['created_time']
        id = self['id']
        sql = f"INSERT IGNORE INTO Taotao(uin, content, source, created_time, id) VALUES ('{uin}','{content}','{source}','{created_time}','{id}')"
        cursor.execute(sql)


class LikesItem(Item):
    # 无法获取所有点赞的人(可能不能获取的是不可访问的,未深究)
    # 点赞id, 主键
    id = Field()
    # 点赞对象账号
    uin = Field()
    # 点赞行为人账号
    f_uin = Field()
    # 点赞次数
    counts = Field()

    def save_mysql(self, cursor, item):
        # 已存在的counts+1
        id = self['id']
        uin = self['uin']
        f_uin = self['f_uin']
        counts = self['counts']
        sql = f"INSERT INTO Likes(uin, f_uin, id, counts) VALUES ('{uin}','{f_uin}','{id}','{counts}') ON duplicate KEY UPDATE counts = counts + 1"
        cursor.execute(sql)
