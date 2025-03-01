import http.client
import json

conn = http.client.HTTPConnection("127.0.0.1", 2531)
payload = json.dumps({
   "appId": "wx_UGdj81O5nGHctzupxq8AV"
})
headers = {
   'X-GEWE-TOKEN': '2848539b92e44bd2aabc0e9831b4426d',
   'Content-Type': 'application/json'
}
conn.request("POST", "/v2/api/login/logout", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))