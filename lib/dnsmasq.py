import os
import re
import signal
import subprocess
from lib.settings import DnsMasqBinPath

typeof = lambda v : type(v).__name__

class DnsMasqBase:
  def __init__(self,config="dnsmasq.conf",pidfile="dnsmasq.pid",logfile="dnsmasq.log"):
    self.SWITCHES = []
    self.CONF = {}
    self.CONFIG_FILE = config
    self.PID_FILE = pidfile
    self.LOG_file = logfile

  def StartDnsMasq(self,args=True):
    runar = [DnsMasqBinPath,"--no-daemon"]
    if args:
      runar.extend(self.GetArguments())
    else:
      self.WriteConfig()
      runar.extend(["-C",self.CONFIG_FILE])
    proc = subprocess.Popen(runar,stderr=subprocess.STDOUT,stdout=open(self.LOG_file,"a"))
    with open(self.PID_FILE,"w") as f:
      f.write(f"{proc.pid}")
  
  def StopDnsMasq(self):
    if os.path.exists(self.PID_FILE):
      with open(self.PID_FILE,"r") as f:
        usepid = int(f.readline())
      
      os.kill(usepid,signal.SIGTERM)
      os.remove(self.PID_FILE)
  
  def GetArguments(self):
    args = []

    for sw in self.SWITCHES:
      args.append(f"--{sw}")

    for c in self.CONF.keys():
      for conf_entry in self.CONF[c]:
        args.append(f"--{c}={conf_entry}")

    return args
  
  def WriteConfig(self):
    with open(self.CONFIG_FILE,"w") as conf:
      for sw in self.SWITCHES:
        conf.write(f"{sw}\n")

      for c in self.CONF.keys():
        for conf_entry in self.CONF[c]:
          conf.write(f"{c}={conf_entry}\n")
  
  def Set(self,k,v=""):
    if v:
      if not self.__validate_conf(k):
        raise Exception(f"Invalid configuration parameter ({k})")
      
      if not k in self.CONF.keys():
        self.CONF[k] = []
      
      if not v in self.CONF[k]:
        self.CONF[k].append(str(v))
    else:
      if not self.__validate_switch(k):
        raise Exception(f"Invalid switch ({k})")
      
      if not k in self.SWITCHES:
        self.SWITCHES.append(k)
  
  def Get(self,k):
    if k in self.SWITCHES:
      return True
    elif k in self.CONF.keys():
      return self.CONF[k]
    else:
      return False
  
  def __validate_switch(self,s):
    return s in ["bogus-priv","dnssec","dnssec-check-unsigned","filterwin2k","strict-order","no-resolv","no-poll","bind-interfaces","no-hosts","expand-hosts","enable-ra","read-ethers","enable-tftp","tftp-no-fail","tftp-secure","tftp-no-blocksize","dhcp-authoritative","dhcp-rapid-commit","no-negcache","localmx","selfmx","log-queries","log-dhcp"]

  def __validate_conf(self,c):
    return c in ["interface", "addn-hosts","address","alias","bogus-nxdomain","cache-size","cname","conf-dir","conf-file","dhcp-boot","dhcp-host","dhcp-ignore","dhcp-ignore-names","dhcp-lease-max","dhcp-leasefile","dhcp-mac","dhcp-match","dhcp-name-match","dhcp-option","dhcp-option-force","dhcp-range","dhcp-script","dhcp-userclass","dhcp-vendorclass","domain","except-interface","group","ipset","listen-address","local","local-ttl","mx-host","mx-target","nftset","no-dhcp-interface","port","ptr-record","pxe-prompt","pxe-service","resolv-file","server","srv-host","tftp-root","txt-record","user"]

class DnsMasqDHCP(DnsMasqBase):
  def __init__(self,interface="eth0",config="dnsmasq_dhcp.conf",pidfile="dnsmasq_dhcp.pid",logfile="dnsmasq_dhcp.log"):
    super().__init__(config=config,pidfile=pidfile,logfile=logfile)

    self.CONFIG_FILE = config
    self.Set("interface",interface)
  
  def AddRange(self,s,e,m="",lease=12,tag=""):
    if self.__validate_ip(s) and self.__validate_ip(e) and self.__validate_mask(m) and typeof(lease) == 'int':
      self.Set("dhcp-range",f"{f"tag:{tag}," if tag else ""}{s},{e},{f"{m}," if m else ""}{lease}h")
  
  def AddStaticLease(self,m,a,h="",lease=0):
    if (len(h) == 0 or self.__validate_hostname(h)) and self.__validate_ip(a) and self.__validate_mac(m):
      self.Set("dhcp-host",f"{m},{f"{h}," if h else ""}{a},{f"{lease}h" if lease > 0 else "infinite"}")
  
  def ExcludeMac(self,m):
    if self.__validate_mac(m):
      self.Set("dhcp-host",f"{m},ignore")

  def AddDhcpGateway(self,r):
    if self.__validate_ip(r):
      self.__add_dhcp_option("option:router",r)

  def AddDhcpNtpServer(self,*n):
    valid = True
    for this_n in n:
      if not self.__validate_ip(this_n):
        valid = False
        break
    
    if valid:
      self.__add_dhcp_option("option:ntp-server",",".join(n))
  
  def AddDhcpDnsServer(self,*d):
    valid = True
    for this_d in d:
      if not self.__validate_ip(this_d):
        valid = False
        break

    if valid:
      self.__add_dhcp_option("option:dns-server",",".join(d))

  def AddDhcpNetmask(self,s):
    if self.__validate_mask(s):
      self.__add_dhcp_option("option:netmask",s)

  def AddDhcpDomainName(self,d):
    if self.__validate_hostname(d):
      self.__add_dhcp_option("domain-name",d)
  
  def __add_dhcp_option(self,o,v):
    if typeof(o) == int and o > 0 and typeof(v) == 'str':
      self.__remove_dhcp_option(o)
      self.Set("dhcp-option",f"{str(o)},{v}")
  
  def __remove_dhcp_option(self,o):
    if len([a for a in self.CONF if a.startswith(f"dhcp-option={str(o)}")]) > 0:
      self.CONF = [a for a in self.CONF if not a.startswith(f"dhcp-option={str(o)}")]
  
  def __validate_ip(self,addr):
      oct = [int(a) for a in addr.split('.')]
      return len(oct) == 4 and 255 >= oct[0] >= 1 and 255 >= oct[1] >= 1 and 255 >= oct[2] >= 1 and 255 >= oct[3] >= 1

  def __validate_mac(self,m):
    oct = [int(a) for a in m.split(":")]
    return len(oct) == 6 and 255 >= oct[0] >= 0 and 255 >= oct[1] >= 0 and 255 >= oct[2] >= 0 and 255 >= oct[3] >= 0 and 255 >= oct[4] >= 0 and 255 >= oct[5] >= 0
  
  def __validate_hostname(self,h):
      hostval = r'^[a-z0-9-]+$'
      return bool(re.match(hostval,h))
  
  def __validate_mask(self,a):
    oct = [int(a) for a in a.split('.')]
    validbin = r'^0b1*0*$'
    return len(oct) == 4 and re.match(validbin,bin(oct[0])) and re.match(validbin,bin(oct[1])) and re.match(validbin,bin(oct[2])) and re.match(validbin,bin(oct[3]))    

class DnsMasqTFTP(DnsMasqBase):
  def __init__(self,tftppath="/var/ftpd",secure=True,interface="eth0",config="dnsmasq_tftp.conf",pidfile="dnsmasq_tftp.pid",logfile="dnsmasq_tftp.log"):
    super().__init__(interface=interface,config=config,logfile=logfile,pidfile=pidfile)

    self.Set("port",0)
    self.Set("enable-tftp")
    self.Set("tftp-root",tftppath)
    self.Set("tftp-no-fail")
    if secure:
      self.Set("tftp-secure")

class DnsMasqPXE(DnsMasqDHCP):
  def __init__(self,tftppath="/var/ftpd",secure=True,config="dnsmasq_pxe.conf",interface="eth0",pidfile="dnsmasq_pxe.pid",logfile="dnsmasq_pxe.log"):
    super().__init__(interface=interface,config=config,pidfile=pidfile,logfile=logfile)

    self.Set("enable-tftp")
    self.Set("tftp-root",tftppath)
    self.Set("tftp-no-fail")
    if secure:
      self.Set("tftp-secure")

    self.Set("dhcp-boot","pxelinux.0")

class DnsMasqDNS(DnsMasqBase):
  def __init__(self,interface="eth0",port=53,config="dnsmasq_dns.conf",pidfile="dnsmasq_dns.pid",logfile="dnsmasq_dns.log"):
    super().__init__(config=config,pidfile=pidfile,logfile=logfile)

    self.Set("port",port)
    self.CONFIG_FILE = config
    self.managed_hosts = {}
    self.dns_conf = {"local_domains":[],"servers":[]}

  def GetDns(self,h,t):
    if h in self.managed_hosts.keys() and t in self.managed_hosts[h].keys():
      return self.managed_hosts[h][t]
  
  def AddAddress(self,h,a,skip=False):
    if self.__validate_ip(a) and self.__validate_hostname(h):
      self.Set("address",f"/{h}/{a}")
      if not skip:
        self.__add_host(h)
        self.managed_hosts[h]["A"].append(a)
  
  def AddCName(self,fh,th,skip=False):
    if self.__validate_hostname(fh) and self.__validate_hostname(th):
      self.Set("cname",f"{th},{fh}")
      if not skip:
        self.__add_host(fh)
        self.managed_hosts[fh]["CNAME"] = th
  
  def AddMX(self,d,h,p=1,skip=False):
    if self.__validate_hostname(d) and (self.__validate_hostname(h) or self.__validate_ip(h)):
      self.Set("mx-host",f"{d},{h},{str(p)}")
      if not skip:
        self.__add_host(d)
        self.managed_hosts[d]["MX"].append({"host":h,"priority":p})
  
  def AddSRV(self,host,svr,port,priority=0,weight=0,skip=False):
    service_match = r'^_(?P<service>[^\.]+)\._(?P<protocol>[^\.]+)\.(?P<host>.*)$'
    g = re.match(service_match,host)
    if self.__validate_service(g['service']) and g['protocol'] in ['tcp','udp'] and self.__validate_hostname(g['host']) and self.__validate_hostname(host,True) and self.__validate_hostname(svr) and typeof(port) == 'int' and typeof(priority) == 'int' and typeof(weight) == 'int':
      self.Set("srv-host",f"{host},{svr},{port},{str(priority)},{str(weight)}")
      if not skip:
        self.__add_host(host)
        self.managed_hosts[host]["SRV"].append({"server":svr,"port":port,"priority":priority,"weight":weight})
  
  def AddTXT(self,d,t,skip=False):
    if self.__validate_hostname(d) and typeof(t) == 'str':
      self.Set("txt-record",f"{d},\"{t}\"")
      if not skip:
        self.__add_host(d)
        self.managed_hosts[d]["TXT"].append(t)
  
  def AddLocalDomain(self,d,skip=False):
    if not d in self.dns_conf['local_domains']:
      self.Set("local",d)
      if not skip:
        self.dns_conf['local_domains'].append(d)    
  
  def AddServer(self,svr,suffix="",skip=False):
    value = f"/{suffix}/{svr}" if suffix else svr
    if not value in self.dns_conf['resolvers']:
      self.Set("server",value)
      if not skip:
        self.dns_conf['servers'].append(value)
    
  def __validate_ip(self,a):
    oct = [int(a) for a in a.split('.')]
    return len(oct) == 4 and 255 >= oct[0] >= 1 and 255 >= oct[1] >= 1 and 255 >= oct[2] >= 1 and 254 >= oct[3] >= 1
  
  def __validate_hostname(self,h,srv=False):
    hostval = r'^[a-z0-9-_\.]+$' if srv else r'^[a-z0-9-\.]+$'
    return bool(re.match(hostval,h))
  
  def __validate_service(self,s):
    with open("/etc/services","r") as f:
      services = f.readlines()
    
    return s in  [re.sub(r'^([^ \t]+).*$','\\1',l) for l in services if not re.match(r'^#',l) and not re.match(r'^[ \t]*$',l)]

  def __add_host(self,h):
    if not h in self.managed_hosts.keys():
      self.managed_hosts[h] = {"A":[],"CNAME":"","MX":[],"SRV":[],"TXT":[]}

  def __build_dnsmasq_conf(self):
    for h in self.managed_hosts.keys():
      for arec in self.managed_hosts[h]["A"]:
        self.AddAddress(h,arec,skip=True)

      if len(self.managed_hosts[h]["CNAME"]) > 0:
        self.AddCName(h,self.managed_hosts[h]["CNAME"],skip=True)

      for mxrec in self.managed_hosts[h]["MX"]:
        self.AddMX(h,mxrec['host'],mxrec['priority'],skip=True)
      
      for srvrec in self.managed_hosts[h]["SRV"]:
        har = h.split(".")
        self.AddSRV(har[0],har[1],har[2],srvrec["server"],srvrec["port"],srvrec["priority"],srvrec["weight"],skip=True)

      for txtrec in self.managed_hosts[h]["TXT"]:
        self.AddTXT(h,txtrec,skip=True)

    for s in self.dns_conf['servers']:
      self.AddServer(s,skip=True)

    for d in self.dns_conf['local_domains']:
      self.AddLocalDomain(d,skip=True)
