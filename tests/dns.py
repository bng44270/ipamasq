from lib.dnsmasq import DnsMasqDNS
import time
import json

svr = DnsMasqDNS(interface="lo",port=5353)
svr.AddAddress('bob.local','1.2.3.4')
svr.AddAddress('mail.test.com','5.3.3.6')
svr.AddMX('bob.local','mail.test.com',100)
svr.AddCName('www.bob.local','bob.local1')
svr.StartDnsMasq()
time.sleep(1)
input("Press 'enter' to stop server")
svr.StopDnsMasq()