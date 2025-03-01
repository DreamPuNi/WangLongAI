import http.client
import json

conn = http.client.HTTPConnection("127.0.0.1", 2531)
payload = json.dumps({
    "appId": "wx_UGdj81O5nGHctzupxq8AV",
    "toWxid": "wxid_j9m9a65vqqvc22",
    "title": "澳门这一夜",
    "desc": "39岁郭碧婷用珠圆玉润的身材，狠狠打脸了白幼瘦女星",
    "linkUrl": "https://mbd.baidu.com/newspage/data/landingsuper?context=%7B%22nid%22%3A%22news_8864265500294006781%22%7D&n_type=-1&p_from=-1",
    "thumbUrl": "https://pics3.baidu.com/feed/0824ab18972bd407a9403f336648d15c0db30943.jpeg@f_auto?token=d26f7f142871542956aaa13799ba1946"
})
headers = {
   'X-GEWE-TOKEN': '2848539b92e44bd2aabc0e9831b4426d',
   'Content-Type': 'application/json'
}
conn.request("POST", "/v2/api/message/postLink", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))