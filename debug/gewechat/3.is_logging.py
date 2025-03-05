import http.client
import json

conn = http.client.HTTPConnection("192.168.31.235", 2531)
payload = json.dumps({
   "appId": "wx_VzTqgHBeCxViPUHpEqbnT",
   "uuid": "gf5vWG8ufiBJerpfUKi4"
})
headers = {
   'X-GEWE-TOKEN': '77454c4c65a94089919faffcc5d58749',
   'Content-Type': 'application/json'
}
conn.request("POST", "/v2/api/login/checkLogin", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))

"""
{"ret":200,"msg":"操作成功","data":{"uuid":"Ic4c-iHg55K-r9jvui-w","headImgUrl":"http://wx.qlogo.cn/mmhead/ver_1/O8DWgfFUJpPW9vQPZOsQAVkcianTpDa5j9YrSZBia806BE9xwmkicwOegvUMzCxFUxmRsUgNFbLl3TkMKNSDicwlXibkrDyEGGHaBy3O2IObtGwQCz2mTIibndia1OUlDVIlQok/0","nickName":"何颂生","expiredTime":18,"status":2,"loginInfo":{"uin":173600672,"wxid":"wxid_7im0hocoravz22","nickName":"何颂生","mobile":"132****0200","alias":"frontagain"}}}
"""