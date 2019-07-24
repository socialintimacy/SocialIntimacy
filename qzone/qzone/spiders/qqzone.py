# -*- coding: utf-8 -*-
import json
import logging
import time
import re
import pymysql
import asyncio
import pyppeteer
from logging import getLogger

from pyppeteer.errors import PageError
from urllib.parse import quote_plus
from PIL import Image
from scrapy import Request, Spider
from qzone.items import *
from qzone.settings import *


class QqzoneSpider(Spider):
    name = 'qqzone'
    allowed_domains = ['qq.com']
    friend_url = 'https://user.qzone.qq.com/proxy/domain/r.qzone.qq.com/cgi-bin/tfriend/friend_ship_manager.cgi?' \
                 'uin={uin}&do=1&g_tk={g_tk}'
    taotao_url = 'https://user.qzone.qq.com/proxy/domain/taotao.qq.com/cgi-bin/emotion_cgi_msglist_v6?' \
                 'num=20&replynum=100&callback=_preloadCallback&format=jsonp&outCharset=utf-8&inCharset=utf-8' \
                 '&g_tk={g_tk}&uin={uin}&pos={pos}&qzonetoken={q_tk}'
    msgb_url = 'https://user.qzone.qq.com/proxy/domain/m.qzone.qq.com/cgi-bin/new/get_msgb?' \
               'hostUin={uin}&format=jsonp&num=20&start={start_num}&g_tk={g_tk}'
    likes_url = 'https://user.qzone.qq.com/proxy/domain/users.qzone.qq.com/cgi-bin/likes/get_like_list_app?' \
                'uin={uin}&unikey={unikey}&query_count=60&if_first_page=1&g_tk={g_tk}'
    user_url = 'https://h5.qzone.qq.com/proxy/domain/base.qzone.qq.com/cgi-bin/user/cgi_userinfo_get_all?' \
               'uin={uin}&g_tk={g_tk}'

    def py_login(self):
        """
        模拟登录
        """
        screen_shot = str(time.time()).replace('.', '')
        screen_shot = f'{screen_shot}.png'
        pyppeteer_level = logging.WARNING
        logging.getLogger('websockets.protocol').setLevel(pyppeteer_level)
        logging.getLogger('pyppeteer').setLevel(pyppeteer_level)
        logger = getLogger(__name__)
        loop = asyncio.get_event_loop()
        # 非无头模式调试时可注释其余参数,避免多开卡死
        browser = loop.run_until_complete(pyppeteer.launch(headless=True,
                                                           dupio=True,
                                                           args=[
                                                                '--no-sandbox',
                                                                ]))

        async def async_render(screen_shot):
            page = await browser.newPage()
            await page.setUserAgent(
                'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.67 Safari/537.36')
            try:
                # basic render
                await page.goto(
                    'https://i.qq.com',
                    {'timeout': 20000, "waitUntil": 'networkidle2'})
                # Login
                await page.screenshot({'path': screen_shot})
                im = Image.open(screen_shot)
                im.show()
                # 多次登录后, 登录跳转到主页但长时间等待与某网址通信, 造成程序超时.
                # 延长超时时间
                await asyncio.gather(page.waitForNavigation({'timeout': 90000}))

                try:
                    # Get cookies
                    cookies = await get_cookie(page)
                    g_tk = await get_g_tk(cookies)
                    html = await page.content()
                    xpat = r'window\.g_qzonetoken = \(function\(\)\{ try\{return "(.*?)";\} catch\(e\)'
                    q_tk = re.findall(xpat, html)[0]
                    re_uin = 'g_iUin=(.*),'
                    uin = re.findall(re_uin, html)[0]

                    return uin, cookies, g_tk, q_tk
                except PageError:
                    logger.log('连接失败')

            except PageError:
                logger.log('连接失败')

            finally:
                await page.close()
                await browser.close()

        async def get_cookie(page):
            cookies_list = await page.cookies()
            cookies = {}
            for cookie in cookies_list:
                cookies[cookie['name']] = cookie['value']
            return cookies

        async def get_g_tk(cookies):
            hashes = 5381
            for letter in cookies['p_skey']:
                hashes += (hashes << 5) + ord(letter)
            return hashes & 0x7fffffff

        uin, cookies, g_tk, q_tk = loop.run_until_complete(async_render(screen_shot))

        return uin, cookies, g_tk, q_tk

    def create_tables(self):
        """建表"""
        params = dict(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            db=MYSQL_DB,
            user=MYSQL_USER,
            passwd=MYSQL_PASSWORD,
            charset=MYSQL_CHARSET,
            cursorclass=pymysql.cursors.DictCursor,
            use_unicode=True,
        )
        con = pymysql.connect(**params)

        with con.cursor() as cur:
            sql_msq = 'CREATE TABLE IF NOT EXISTS Msg(id VARCHAR(50) PRIMARY KEY,uin CHAR(10),m_uin CHAR(10),created_time INT,content VARCHAR(255))'
            sql_account = 'CREATE TABLE IF NOT EXISTS Account(uin CHAR(10) PRIMARY KEY,age INT,birthday CHAR(15),birthyear CHAR(10),sex INT,nickname VARCHAR(50),score INT)'
            sql_taotao = 'CREATE TABLE IF NOT EXISTS Taotao(id VARCHAR(50) PRIMARY KEY,uin CHAR(10),source CHAR(15),created_time INT,content VARCHAR(255))'
            sql_likes = 'CREATE TABLE IF NOT EXISTS Likes(id CHAR(21) PRIMARY KEY,uin CHAR(10),f_uin CHAR(10),created_time INT,counts INT)'

            cur.execute(sql_msq)
            cur.execute(sql_account)
            cur.execute(sql_taotao)
            cur.execute(sql_likes)

        con.commit()
        con.close()

    def loads_jsonp(self, _jsonp):
        """
        解析jsonp数据格式为json
        """
        try:
            return json.loads(re.match(".*?({.*}).*", _jsonp, re.S).group(1))
        except ValueError:
            raise ValueError('Invalid Input')

    def start_requests(self):
        """
        建表,模拟登录,获取本人相关信息,获取好友列表
        """
        # 若已建表,可注释下一行
        # self.create_tables()
        uin, cookies, g_tk, q_tk = self.py_login()
        pos = 0
        start_num = 0
        yield Request(url=self.user_url.format(uin=uin, g_tk=g_tk), cookies=cookies,
                      callback=self.account_parse)
        yield Request(url=self.friend_url.format(uin=uin, g_tk=g_tk), cookies=cookies,
                      callback=self.uin_parse,
                      meta={'cookies': cookies, 'g_tk': g_tk, 'q_tk': q_tk, 'o_uin': uin})
        yield Request(url=self.taotao_url.format(uin=uin, pos=pos, g_tk=g_tk, q_tk=q_tk), cookies=cookies,
                      callback=self.taotao_parse,
                      meta={'cookies': cookies, 'pos': pos, 'g_tk': g_tk, 'uin': uin, 'q_tk': q_tk})
        yield Request(url=self.msgb_url.format(uin=uin, start_num=start_num, g_tk=g_tk), cookies=cookies,
                      callback=self.msgb_parse,
                      meta={'cookies': cookies, 'start_num': start_num, 'g_tk': g_tk, 'uin': uin})

    def uin_parse(self, response):
        """
        获取好友列表,获取uin和score(亲密度),遍历uin,请求相关信息
        """
        result = self.loads_jsonp(response.text)
        if result.get('data'):
            g_tk = response.meta['g_tk']
            q_tk = response.meta['q_tk']
            cookies = response.meta['cookies']
            o_uin = response.meta['o_uin']
            start_num = 0
            pos = 0
            for i in result['data']['items_list']:
                uin = i['uin']
                score = i['score']
                yield Request(url=self.user_url.format(uin=uin, g_tk=g_tk), cookies=cookies,
                              callback=self.account_parse,
                              meta={'score': score})
                yield Request(url=self.taotao_url.format(uin=uin, g_tk=g_tk, pos=pos, q_tk=q_tk), cookies=cookies,
                              callback=self.taotao_parse,
                              meta={'cookies': cookies, 'pos': pos, 'g_tk': g_tk, 'uin': uin, 'q_tk': q_tk, 'o_uin': o_uin})
                yield Request(url=self.msgb_url.format(uin=uin, g_tk=g_tk, start_num=start_num), cookies=cookies,
                              callback=self.msgb_parse,
                              meta={'cookies': cookies, 'g_tk': g_tk, 'start_num': start_num, 'uin': uin})

    def taotao_parse(self, response):
        """
        获取说说
        """
        result = self.loads_jsonp(response.text)
        if result.get('msglist'):
            cookies = response.meta['cookies']
            g_tk = response.meta['g_tk']
            q_tk = response.meta['q_tk']
            pos = response.meta['pos']
            uin = response.meta['uin']
            o_uin = response.meta['o_uin']
            total = result['total']
            for i in result['msglist']:
                item = Taotaoitem()
                tid = i['tid']
                item['id'] = tid
                item['uin'] = uin
                item['content'] = i.get('content')
                item['created_time'] = i['created_time']
                item['source'] = i.get('source_name')
                yield item

                # 如果是转载说说,mood为原说说id
                if i.get('rt_tid'):
                    mood = i['rt_tid']
                else:
                    mood = tid
                unikey = quote_plus(f'http://user.qzone.qq.com/{uin}/mood/{mood}')
                # 请求点赞信息
                yield Request(url=self.likes_url.format(uin=o_uin, unikey=unikey, g_tk=g_tk), cookies=cookies,
                              callback=self.likes_parse,
                              meta={'uin': uin})

                # 若有留言,存入留言表
                if i.get('conmentlist'):
                    for j in i['commentlist']:
                        msg_item = MsgItem()
                        msg_item['uin'] = i['uin']
                        m_uin = j['uin']
                        msg_item['m_uin'] = m_uin
                        msg_item['created_time'] = j['created_time']
                        # id容易重复,加上说说id
                        id = f'{tid}_{j["tid"]}'
                        msg_item['id'] = id
                        msg_item['content'] = j['content']
                        yield msg_item

                        # 若有回复,存入留言表
                        if j.get('list_3'):
                            for k in j['list_3']:
                                rep_item = MsgItem()
                                rep_item['uin'] = m_uin
                                rep_item['m_uin'] = k['uin']
                                rep_item['created_time'] = k['create_time']
                                # id容易重复,加上留言id
                                r_id = f'{id}_{k["tid"]}'
                                rep_item['id'] = r_id
                                rep_item['content'] = k['content']
                                yield rep_item

            # 检查是否爬完所有说说
            pos += 20
            if pos < total:
                yield Request(url=self.taotao_url.format(uin=uin, pos=pos, g_tk=g_tk, q_tk=q_tk), cookies=cookies,
                              callback=self.taotao_parse,
                              meta={'cookies': cookies, 'pos': pos, 'g_tk': g_tk, 'uin': uin, 'q_tk': q_tk})

    def msgb_parse(self, response):
        """
        获取留言板留言
        """
        result = self.loads_jsonp(response.text)
        uin = response.meta['uin']
        start_num = response.meta['start_num']
        if result.get('data'):
            total = result['data']['total']
            if result['data'].get('commentList'):
                for i in result['data']['commentList']:
                    # 若留言可见,存入留言表
                    if i.get('ubbContent'):
                        item = MsgItem()
                        item['content'] = i['ubbContent']
                        m_uin = i['uin']
                        item['m_uin'] = m_uin
                        item['uin'] = uin
                        item['created_time'] = i['pubtime']
                        # 留言id容易重复,加上uin
                        id = f'{uin}_{i["id"]}'
                        item['id'] = id
                        yield item

                        # 若留言有回复,存入留言表
                        if i.get('replyList'):
                            for j in i['replyList']:
                                rep_item = MsgItem()
                                rep_item['content'] = j['content']
                                time = j['time']
                                rep_item['created_time'] = time
                                # 若作者为用户本人,则uin为回复用户
                                if j['uin'] == uin:
                                    rep_item['m_uin'] = uin
                                    rep_item['uin'] = m_uin
                                else:
                                    rep_item['m_uin'] = m_uin
                                    rep_item['uin'] = uin
                                # 回复无id,由留言id和回复时间拼接
                                rep_item['id'] = f'{id}_{time}'
                                yield rep_item

                # 一次最多获取20条留言
                start_num += 20
                # 检查是否爬取完所有留言
                if start_num < total:
                    cookies = response.meta['cookies']
                    g_tk = response.meta['g_tk']
                    yield Request(url=self.msgb_url.format(uin=uin, g_tk=g_tk, start_num=start_num), cookies=cookies,
                                  callback=self.msgb_parse,
                                  meta={'cookies': cookies, 'g_tk': g_tk, 'start_num': start_num, 'uin': uin})

    def account_parse(self, response):
        """
        解析用户信息, score为亲密度
        """
        result = self.loads_jsonp(response.text)
        if result.get('uin'):
            data = result
            item = AccountItem()
            uin = data['uin']
            item['uin'] = uin
            item['nickname'] = data['nickname']
            item['sex'] = data.get('sex')
            item['birthday'] = data.get('birthday')
            item['birthyear'] = data.get('birthyear')
            if response.meta.get('score'):
                item['score'] = response.meta['score']
            yield item

    def likes_parse(self, response):
        """
        解析点赞用户
        """
        result = self.loads_jsonp(response.text)
        if result.get('data'):
            uin = response.meta['uin']
            for i in result['data']['like_uin_info']:
                item = LikesItem()
                item['uin'] = uin
                f_uin = i['fuin']
                item['f_uin'] = f_uin
                item['id'] = f'{uin}_{f_uin}'
                item['counts'] = 1
                yield item
