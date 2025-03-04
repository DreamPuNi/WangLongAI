安装指定版本企业微信

[WeCom_4.0.8.6027.exe官方下载链接](https://dldir1.qq.com/wework/work_weixin/WeCom_4.0.8.6027.exe)

[WeCom_4.0.8.6027.exe阿里云盘备份](https://www.alipan.com/s/UxQHrZ5WoxS)

[WeCom_4.0.8.6027.exe夸克网盘备份](https://pan.quark.cn/s/1d06b91b40af)

安装ntwork依赖

由于ntwork的安装源不是很稳定，可以下载对应的whl文件，使用whl文件离线安装ntwork

首先需要查看你的python版本，在命令行中输入python查看版本信息，然后在[ntwork-whl](https://github.com/hanfangyuan4396/ntwork-bin-backup/tree/main/ntwork-whl)目录下找到对应的whl文件，运行 `pip install xx.whl` 安装ntwork依赖，注意"xx.whl"更换为whl文件的实际路径。

例如我的python版本信息为

"Python 3.8.5 (default, Sep 3 2020, 21:29:08) [MSC v.1916 64 bit (AMD64)]"

可以看到python版本是3.8.5，并且是AMD64，所以对应的whl文件为ntwork-0.1.3-cp38-cp38-win_amd64.whl，需要执行如下命令安装
```
pip install your-path/ntwork-0.1.3-cp38-cp38-win_amd64.whl
```
填写配置文件

我们在项目根目录创建名为config.json的文件，文件内容如下，请根据教程参考手摸手教你把 Dify 接入微信生态获取dify_api_base、dify_api_key、dify_app_type信息，注意channel_type填写为 wework
```
{ 
  "dify_api_base": "https://api.dify.ai/v1",
  "dify_api_key": "app-xxx",
  "dify_app_type": "chatbot",
  "channel_type": "wework",
  "model": "dify",
  "single_chat_prefix": [""],
  "single_chat_reply_prefix": "",
  "group_chat_prefix": ["@bot"],
  "group_name_white_list": ["ALL_GROUP"]
}
```
登录企业微信
务必提前在电脑扫码登录企业微信