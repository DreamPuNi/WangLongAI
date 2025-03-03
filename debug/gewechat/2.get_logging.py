import http.client
import json
import base64
from io import BytesIO
from PIL import Image

conn = http.client.HTTPConnection("192.168.31.235", 2531)
payload = json.dumps({
   "appId": "wx_h_wNG48atr8kFFQWkELQ2"
})
headers = {
   'X-GEWE-TOKEN': '934c7ad0b1994c13a52374f5be9f39fb',
   'Content-Type': 'application/json'
}
conn.request("POST", "/v2/api/login/getLoginQrCode", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))

response_json = json.loads(data.decode("utf-8"))

# 解析二维码
qr_data = response_json["data"]["qrImgBase64"]

# 提取 Base64 部分并解码
base64_data = qr_data.split(",")[1]  # 去掉 "data:image/jpg;base64," 头部
image_data = base64.b64decode(base64_data)

# 显示二维码
image = Image.open(BytesIO(image_data))
image.show()
