import http.client
import json

conn = http.client.HTTPSConnection("192.168.31.235", 2531)
payload = json.dumps({})
headers = {
   'X-GEWE-TOKEN': '77454c4c65a94089919faffcc5d58749',
   'Content-Type': 'application/json'
}
conn.request("POST", "/login/deviceList", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))