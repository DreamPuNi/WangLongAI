import http.client
import json

conn = http.client.HTTPConnection("127.0.0.1", 2531)
payload = json.dumps({
   "token": "55d143207c5e4ab8ad19e0f729f54ab4",
   "callbackUrl": "http://127.0.0.1:8080/v2/api/callback/collect"
})
headers = {
   'X-GEWE-TOKEN': '934c7ad0b1994c13a52374f5be9f39fb',
   'Content-Type': 'application/json'
}
conn.request("POST", "/v2/api/tools/setCallback", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))