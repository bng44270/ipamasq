from lib.sqlitedef import SqliteDefGroup

svr = SqliteDefGroup('ipamasq.db')
svr.CreateTable("ip_subnet",{"id":"PrimaryKeyType","network":"StringType","mask":"NumberType","static":"BooleanType"})
svr.CreateTable("dhcp_range",{"id":"PrimaryKeyType","subnet":"ForeignKeyType","tag":"StringType","REF_subnet":"ip_subnet.id"})
svr.CreateTable("ip_address",{"id":"PrimaryKeyType","address":"StringType","subnet":"ForeignKeyType","REF_subnet":"ip_subnet.id"})
svr.CreateTable("ip_hostname",{"id":"PrimaryKeyType","name":"StringType","address":"ForeignKeyType","REF_address":"ip_address.id"})
svr.CreateTable("ip_meta_field",{"id":"PrimaryKeyType","name":"StringType"})
svr.CreateTable("ip_subnet_meta_field",{"subnet":"ForeignKeyType","field":"ForeignKeyType","val":"StringType","REF_subnet":"subnet.id","REF_field":"ip_meta_field.id"})
svr.CreateJoinView("dhcp_hostname","ip_hostname",{"ip_hostname.name":"hostname","ip_address.address":"ip_address"},{"ip_address":[("ip_hostname.address","EQ","ip_address.id")],"ip_subnet":[("ip_address.subnet","EQ","ip_subnet.id")]},[("ip_subnet.static","EQ",0)])
svr.CreateJoinView("static_hostname","ip_hostname",{"ip_hostname.name":"hostname","ip_address.address":"ip_address"},{"ip_address":[("ip_hostname.address","EQ","ip_address.id")],"ip_subnet":[("ip_address.subnet","EQ","ip_subnet.id")]},[("ip_subnet.static","EQ",1)])
svr.CreateJoinView("ip_subnet_metadata","ip_subnet",{"ip_subnet.network":"network_id","ip_meta_field.name":"field_name","ip_subnet_meta_field.val":"field_value"},{"ip_subnet_meta_field":[("ip_subnet_meta_field.subnet","EQ","ip_subnet.id")],"ip_meta_field":[("ip_subnet_meta_field.field","EQ","ip_meta_field.id")]})
