import http.client
import json

conn = http.client.HTTPConnection("192.168.31.235", 2531)
payload = json.dumps({
   "appId": "wx_NGQW5r8ByAR4LLE95m7Ks"
})
headers = {
   'X-GEWE-TOKEN': '83efaf2c67124e90af810820cc12efc0',
   'Content-Type': 'application/json'
}
conn.request("POST", "/v2/api/login/logout", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))