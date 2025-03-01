import http.client

conn = http.client.HTTPConnection("192.168.31.235", 2531)
payload = ''
headers = {}
conn.request("POST", "/v2/api/tools/getTokenId", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
