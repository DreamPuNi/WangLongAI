import http.client
import json

conn = http.client.HTTPConnection("127.0.0.1", 2531)
payload = json.dumps({
   "token": "83efaf2c67124e90af810820cc12efc0",
   "callbackUrl": "http://192.168.31.235:9919/v2/api/callback/collect"
})
headers = {
   'X-GEWE-TOKEN': '83efaf2c67124e90af810820cc12efc0',
   'Content-Type': 'application/json'
}
conn.request("POST", "/v2/api/tools/setCallback", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))