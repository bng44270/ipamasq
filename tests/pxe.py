from lib.dnsmasq import DnsMasqPXE
import time

svr = DnsMasqPXE(interface="lo")
svr.AddRange('172.16.100.50','172.16.100.100','255.255.255.0')
svr.AddDhcpGateway("172.16.100.1")
svr.AddDhcpDnsServer("172.16.100.1")
svr.StartDnsMasq()
time.sleep(1)
input("Press 'enter' to stop server")
svr.StopDnsMasq()