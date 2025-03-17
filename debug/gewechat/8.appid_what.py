import http.client
import json

conn = http.client.HTTPSConnection("192.168.31.235", 2531)
payload = json.dumps({})
headers = {
   'X-GEWE-TOKEN': '83efaf2c67124e90af810820cc12efc0',
   'Content-Type': 'application/json'
}
conn.request("POST", "/login/deviceList", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))