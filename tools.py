import os
from itertools import cycle
from random import shuffle

from proxies import proxies




proxy_gen = cycle(proxies)


processed_proxies = []
for proxy in proxies:
    
    if not proxy.get('all://'):
        continue
    temp = proxy.get('all://').replace("http://", "").split("@")
    z = [x for x in temp[0].split(":")] + [x for x in temp[1].split(":")]
    processed_proxies.append({"username": z[0], "password": z[1], "host": z[2], "port": z[3]})


playwright_proxies = []
for proxy in processed_proxies:
    playwright_proxies.append({
        "server" : "http://" + proxy["host"] + ":" + proxy["port"],
        "username" : proxy["username"],
        "password" : proxy["password"]}
        )

shuffle(playwright_proxies)     
playwright_proxy_gen = cycle(playwright_proxies)