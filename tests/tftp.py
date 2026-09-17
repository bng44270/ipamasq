from lib.dnsmasq import DnsMasqTFTP
import time

svr = DnsMasqTFTP(interface="lo")
svr.StartDnsMasq()
time.sleep(1)
input("Press 'enter' to stop server")
svr.StopDnsMasq()