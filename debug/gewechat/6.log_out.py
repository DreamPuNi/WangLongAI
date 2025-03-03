import http.client
import json

conn = http.client.HTTPConnection("127.0.0.1", 2531)
payload = json.dumps({
   "appId": "wx_h_wNG48atr8kFFQWkELQ2"
})
headers = {
   'X-GEWE-TOKEN': '934c7ad0b1994c13a52374f5be9f39fb',
   'Content-Type': 'application/json'
}
conn.request("POST", "/v2/api/login/logout", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))