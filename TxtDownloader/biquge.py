import wx
import asyncio
import aiohttp
import aiofiles
from lxml import etree
import os
import shutil
import urllib.parse
import winreg


class DownloadNovel:

    def __init__(self, save_address, input_name):
        self.save_address = save_address
        self.topic_url = 'https://www.biquxsw.com/'
        self.input_name = input_name

    async def get_all_novel(self):
        async with aiohttp.ClientSession() as session:
            key_word = urllib.parse.quote(self.input_name.encode('gbk'))
            async with session.get(self.topic_url + f'/modules/article/search.php?searchkey={key_word}') as resp:
                text = await resp.text(encoding='gb18030')
                html = etree.HTML(text)
                lis = html.xpath('//*[@id="main"]/div[1]/li')
                all_novel = dict()
                # 有时候不必进行筛选，直接搜索到了目标小说
                if len(lis) == 0:
                    try:
                        all_novel[self.input_name] = self.topic_url + \
                                                     html.xpath('/html/body/div[2]/div[1]/div/a/@href')[0].split('/')[
                                                         -2] + '/'
                    except IndexError:
                        return None
                else:
                    for li in lis:
                        novel_name = li.xpath('./span[2]/a/text()')[0] + '  作者:' + li.xpath('./span[4]/text()')[0]
                        novel_url = li.xpath('./span[2]/a/@href')[0]
                        all_novel[novel_name] = novel_url

                return all_novel

    async def novel_download(self, novel_url):
        async def one_chapter_download(session, novel_name, url, chapter_name, chapter_id):
            async with session.get(url) as resp:
                text = await resp.text(encoding='gb18030')
                html = etree.HTML(text)
                items = html.xpath('//*[@id="content"]/text()')
                novel_text = '\n{}\n\n'.format(chapter_name)
                for item in items:
                    # 调整文字格式，使得手机书城可以识别章节目录
                    novel_text += item.replace('\xa0\xa0\xa0\xa0', '\t') + '\n\n'

            async with aiofiles.open(rf'{self.save_address}\{novel_name}\{chapter_id}', 'w', encoding='utf-8') as fp:
                await fp.write(novel_text)

        async with aiohttp.ClientSession() as session:
            async with session.get(novel_url) as resp:
                text = await resp.text(encoding='gb18030')
                html = etree.HTML(text)
                novel_name = html.xpath('//*[@id="info"]/h1/text()')[0]
                # 正文（dt）后的同级节点（dd）为目标，采用xpath轴选择器即可
                novel_chapters = html.xpath('//*[@id="list"]/dl/dt[2]/following-sibling::* | //*[@id="list"]/dl/center/following-sibling::*')
                # print(novel_chapters)

                # 创建小说文件夹
                os.system(rf'md {self.save_address}\{novel_name}')

                tasks = []
                id = 0
                for chapter in novel_chapters:
                    try:
                        chapter_url = novel_url + chapter.xpath('./a/@href')[0]
                        chapter_name = chapter.xpath('./a/text()')[0]
                        chapter_id = '{:0>5}.txt'.format(id)
                        tasks.append(
                            asyncio.create_task(
                                one_chapter_download(session, novel_name, chapter_url, chapter_name, chapter_id)))
                        id += 1
                    except IndexError:
                        continue

                await asyncio.wait(tasks)

                # 将多个txt文件合成为一个，销毁无用文件夹
                os.system(rf'copy {self.save_address}\{novel_name}\*.txt {self.save_address}\{novel_name}.txt')
                shutil.rmtree(rf'{self.save_address}\{novel_name}')

                return 'over!'


class Frame(wx.Frame):

    def __init__(self):
        wx.Frame.__init__(self, None, title='小说下载器', size=(400, 425), name='frame', style=541072896)
        self.window = wx.Panel(self)
        self.Centre()
        self.bq1 = wx.StaticText(self.window, size=(220, 28), pos=(76, 42), label='这是一个普通的小说下载器.',
                                 name='staticText', style=2321)
        self.an1 = wx.Button(self.window, size=(174, 32), pos=(100, 128), label='设置小说存储地址',
                             name='button')
        self.an1.Bind(wx.EVT_BUTTON, self.set_address)
        self.an2 = wx.Button(self.window, size=(174, 32), pos=(100, 214), label='开始下载小说', name='button')
        self.an2.Bind(wx.EVT_BUTTON, self.download)
        self.an3 = wx.Button(self.window, size=(80, 32), pos=(271, 326), label='退出程序', name='button')
        self.an3.Bind(wx.EVT_BUTTON, self.exit)
        self.bq2 = wx.StaticText(self.window, size=(104, 24), pos=(28, 329), label='author:LJingshuo',
                                 name='staticText', style=2321)

        # 初始化存储地址和小说名称

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders')
        self.desktop_address = winreg.QueryValueEx(key, "Desktop")[0]
        with open('setting.txt','r') as fp:
            self.address = fp.read()
        self.book_name = None

    def set_address(self, event):
        self.window_1 = wx.Dialog(self.window, size=(400, 425), title='设置小说存储地址')
        self.bjk1 = wx.TextCtrl(self.window_1, size=(245, 22), pos=(64, 155), value=self.desktop_address, name='text', style=0)
        self.bq3 = wx.StaticText(self.window_1, size=(220, 28), pos=(76, 78), label=r'输入新的存储地址(默认为桌面路径)',
                                 name='staticText', style=2321)
        self.an4 = wx.Button(self.window_1, size=(174, 32), pos=(106, 267), label='确认更改', name='button')
        self.an4.Bind(wx.EVT_BUTTON, self.modify_address)
        self.window_1.ShowModal()

    def modify_address(self, event):
        self.address = self.bjk1.GetValue()
        with open('setting.txt','w',encoding='utf-8') as fp:
            fp.write(self.address)
        self.window_1.Destroy()

    def download(self, event):
        self.window_2 = wx.Dialog(self.window, size=(400, 425), title='下载小说')
        self.bq4 = wx.StaticText(self.window_2, size=(77, 16), pos=(30, 54), label='输入小说名称', name='staticText',
                                 style=2321)
        self.an5 = wx.Button(self.window_2, size=(82, 32), pos=(170, 98), label='开始', name='button')
        self.an5.Bind(wx.EVT_BUTTON, self.prepare_download)
        self.bjk2 = wx.TextCtrl(self.window_2, size=(184, 22), pos=(124, 50), value='', name='text', style=0)
        self.window_2.ShowModal()

    def prepare_download(self, event):
        self.book_name = self.bjk2.GetValue()

        # 检验address和book_name合法性
        if self.book_name != '' and os.path.exists(self.address):
            # 将address和book_name传入DownloadNovel中开始下载
            self.dn = DownloadNovel(self.address, self.book_name)
            self.all_novel = asyncio.get_event_loop().run_until_complete(self.dn.get_all_novel())
            if self.all_novel == None:
                wx.MessageDialog(None, u"暂时没有这本小说的信息!", u"抱歉!").ShowModal()
            else:
                self.window_2.Destroy()
                self.window_3 = wx.Dialog(self.window, size=(400, 425), title='下载小说')
                self.bq5 = wx.StaticText(self.window_3, size=(266, 24), pos=(68, 33), label='从下列小说中选择一个',
                                         name='staticText',
                                         style=2321)
                self.xzlbk1 = wx.ListBox(self.window_3, size=(256, 271), pos=(71, 66), name='listBox',
                                         choices=list(self.all_novel.keys()),
                                         style=0)
                self.xzlbk1.Bind(wx.EVT_LISTBOX, self.start_download)
                self.window_3.ShowModal()
        else:
            wx.MessageDialog(None, u"请重新正确输入相关信息!(存储地址和小说名称是否合法)", u"错误!").ShowModal()
            self.window_2.Destroy()

    def start_download(self, event):
        book_name = self.xzlbk1.GetStringSelection()
        self.novel_url = self.all_novel[book_name]
        self.an6 = wx.Button(self.window_3, size=(80, 32), pos=(159, 350), label='确认下载', name='button')
        self.an6.Bind(wx.EVT_BUTTON, self.detail_start_download)

    def detail_start_download(self, event):
        result = asyncio.get_event_loop().run_until_complete(self.dn.novel_download(self.novel_url))
        if result == 'over!':
            wx.MessageDialog(None, u"哥们，祝你看的愉快!", u"下载完毕").ShowModal()
            self.window_3.Destroy()
        else:
            wx.MessageDialog(None, u"由于某种原因下载失败!", u"抱歉!").ShowModal()

    def exit(self, event):
        wx.Exit()


class myApp(wx.App):

    def OnInit(self):
        self.frame = Frame()
        self.frame.Show(True)
        return True


if __name__ == '__main__':
    app = myApp()
    app.MainLoop()
