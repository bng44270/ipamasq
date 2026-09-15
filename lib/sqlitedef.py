import os
import glob
import os.path
import re
import string
import sqlite3
import gzip

typeof = lambda v : type(v).__name__
is_datadef = lambda x : "DataDef" in [a.__name__ for a in x.__class__().__class__.__mro__]
is_sqlite = lambda x : "SqliteDef" in [a.__name__ for a in x.__class__().__class__.__mro__]
is_sqlite_middleware = lambda x : "SqliteMiddleware" in [a.__name__ for a in x.__class__().__class__.__mro__]

def SqiteJoinType(self,right=False,left=False,outer=False,inner=False,full=False):
  j = []
  
  if right:
    j.append("RIGHT")
  elif left:
    j.append("LEFT")
  elif full:
    j.append("FULL")
  
  if inner:
    j.append("INNER")
  elif outer:
    j.append("OUTER")
  
  if "INNER" in j and len(j) == 2:
    j.remove("INNER")
  
  return " ".join(j)

class DataDef(list):
  """
    DataDef (extends Python List object)

    DataTypes:

      StringType - string data
      NumberType - numeric data (int or float)
      BooleanType - boolean data
    
    Usage:

      d = DataDef({"name":"StringType","age":"NumberType","retired":"BooleanType"})
      
  """
  def __init__(self,fields,data=[],skipfieldval=False):
    self.TYPES = {}
    self.TYPES["StringType"] = "string"
    self.TYPES["NumberType"] = "number"
    self.TYPES["BooleanType"] = "boolean"
    
    self.TYPEMAP = {}
    self.TYPEMAP["float"] = ["number"]
    self.TYPEMAP["int"] = ["number"]
    self.TYPEMAP["str"] = ["string"]
    self.TYPEMAP["bool"] = ["boolean"]
    
    if not skipfieldval:
      if not self._validatefields(fields):
        raise Exception(f"Invalid schema definition ({str(fields)})")
    
    self.FIELDS = fields
    
    self.__addqueryopts()
    
    if len(data) > 0:
      for row in data:
        self.Insert(row)
  
  def AddField(self,fname,ftype):
    """
      # Extend schema by adding type
      d.AddField("town","StringType")
    """
    if not self._validatefields({fname:ftype}):
      raise Exception(f"Invalid schema update ({fname}:{ftype})")
    
    self.FIELDS[fname] = ftype
    for row in self:
      row[fname] = None
  
  def Delete(self,q):
    """
      # Delete records where age is 70-79
      d.Delete([("age","GE",70),("age","LE",79)])

      # Delete records where age is 19
      d.Delete([("age","EQ",19)])

      # Delete records where age is 30 and name starts with "Jan"
      d.Delete([("age","EQ",30),("name","ST","Jan")])
    
      Available operators:
        EQ => Equal
        NE => Not Equal
        GT => Greater Than
        LT => Less Than
        GE => Greater Than or Equal
        LE => Less Thank or Equal
        ST => Starts With
        EN => Ends with
        CN => Contains
    """
    r = [i for (i,v) in enumerate(self) if len([a for a in q if self.CONDS[a[1]](a[0],a[2])]) == len(q)]
    
    for thisidx in r:
      del self[thisidx]
  
  def Update(self,q,updates=[]):
    """
      # Set retired to True where age is 67-69
      d.Update([("age","GE",67),("age","LE"69)],[("retired",True)])
    """
    r = [i for (i,v) in enumerate(self) if len([a for a in q if self.CONDS[a[1]](a[0],a[2])]) == len(q)]
    
    for thisidx in r:
      for thisupdate in updates:
        self.__validateupdate(thisupdate)
        
        self[thisidx][thisupdate[0]] = thisupdate[1]          
  
  def Query(self,q):
    """
      # Query for records where age is between 40 and 59
      result = d.Query([("age","GE",40),("age","LE"59)])
    """
    if not self.__validatequery(q):
      raise Exception(f"Invalid query ({str(q)})")
    
    result = []
    
    r = [i for (i,v) in enumerate(self) if len([a for a in q if self.CONDS[a[1]](a[0],a[2])]) == len(q)]
    
    for thisidx in r:
      result.append(self[thisidx])
    
    return result
  
  def Insert(self,row):
    """
      # Valid Inserts
      d.insert({"name":"Bob","age":43,"retired":False})
      d.insert({"name":"Jim","age":30,"retired":False})
      d.insert({"name":"Dave","age":71,"retired":True})
      d.insert({"name":"Joe","age":19})

      # Invalid insert will raise an exception (age must be a number)
      d.insert({"name":"Zeke","age":"43","retired":False})
    """
    self.__validaterow(row)
    
    self.append(row)
  
  def __validatequery(self,q):
    for thisquery in q:
      if not len(thisquery) == 2:
        return False
      
      if not thisquery[0] in self.FIELDS:
        return False
    
    return True
  
  def __validateupdate(self,fieldupdate):
    if not len(fieldupdate) == 2:
      raise Exception("Error:  Must profile field and value in update")
    
    self.__validaterow({fieldupdate[0]:fieldupdate[1]})
    
  def __validaterow(self,row):
    for thisfield in row.keys():
      if not thisfield in self.FIELDS.keys():
        raise Exception(f"{thisfield} not defined in schema")
      
      if not self.TYPES[self.FIELDS[thisfield]] in self.TYPEMAP[typeof(row[thisfield])]:
        raise Exception(f"data type '{self.TYPEMAP[typeof(row[thisfield])]}' does not match schema type '{self.TYPES[self.FIELDS[thisfield]]}' for field {thisfield}")
  
  def _validatefields(self,fields):
    validfields = [a for a in fields.values() if a in self.TYPES.keys()]
    
    return True if len(validfields) == len(fields) else False
  
  def __addqueryopts(self):
    self.CONDS = {}
    self.CONDS["EQ"] = self.__q_equals
    self.CONDS["NE"] = self.__q_notequal
    self.CONDS["GT"] = self.__q_greaterthan
    self.CONDS["GE"] = self.__q_greaterthanorequal
    self.CONDS["LT"] = self.__q_lessthan
    self.CONDS["LE"] = self.__q_lessthanorequal
    self.CONDS["ST"] = self.__q_startswith
    self.CONDS["EN"] = self.__q_endswith
    self.CONDS["CN"] = self.__q_contains
  
  def __q_equals(self,v1,v2):
    return v1 == v2
  
  def __q_notequal(self,v1,v2):
    return not v1 == v2
  
  def __q_greaterthan(self,v1,v2):
    return v1 > v2
  
  def __q_lessthan(self,v1,v2):
    return v1 < v2
  
  def __q_greaterthanorequal(self,v1,v2):
    return v1 >= v2
  
  def __q_lessthanorequal(self,v1,v2):
    return v1 <= v2
  
  def __q_startswith(self,v1,v2):
    return str(v1).startswith(v2)
  
  def __q_endswith(self,v1,v2):
    return str(v1).endswith(v2)
  
  def __q_contains(self,v1,v2):
    return str(v2) in str(v1)

class pkey(int):
  def __new__(c,v):
    return super().__new__(c,v)

class fkey(int):
  def __new__(c,v):
    return super().__new__(c,v)

class SqliteDef(DataDef):
  """
    SqliteDef (extends above DataDef object)

    Usage:
    
      # Initialize dataset from JSON file
      # NOTE:  DataCache requiring identical fields on each record to accurately detect schema
      mydata = SqliteDef({"name":"StringType","age":"NumberType","retired":"BooleanType"},'/path/to/file.db')
      
      # After first initializing data cache with schema, the schema is cached also.
      # For subsequent executions, the schema can be omitted as follows:
      mydata = DataCache(file='/path/to/people.json')

      # Caching may also be configured to reoccur after a specified number of seconds
      # In this example caching occurs every 30 seconds:
      mydata = DataCache(file='/path/to/people.json',cachetime=30)
  """
  
  def __init__(self,fields=None,dbfile="",table="",uselog=False):
    self.USE_LOG = uselog
    
    if self.USE_LOG:
      self.LOG_BUFFER = []
    
    self.FieldTypeMap = {}
    self.FieldTypeMap["StringType"] = "TEXT"
    self.FieldTypeMap["NumberType"] = "REAL"
    self.FieldTypeMap["BooleanType"] = "INTEGER CHECK (<F> >=0 and <F> <=1) DEFAULT 0"
    self.FieldTypeMap["PrimaryKeyType"] = "INTEGER PRIMARY KEY AUTOINCREMENT"
    self.FieldTypeMap["ForeignKeyType"] = "INTEGER"
    
    if len(dbfile) == 0:
      raise Exception("No DB specified")
    
    if len(table) == 0:
      raise Exception("No table name provided")
    
    if not os.path.exists(dbfile):
      self.__createdbfile(dbfile)
    
    self.TABLE = table
    self.DBFILE = dbfile
    self.CACHE_READY = False
    
    self.__connect()
    
    if not fields:
      fields = self.__readschema()
      
      if len(fields.keys()) == 0:
        raise Exception("No schema provided")

    super().__init__(fields,skipfieldval=True)
    
    self.TYPES["PrimaryKeyType"] = "primarykey"
    self.TYPES["ForeignKeyType"] = "foreignkey"
    
    self.TYPEMAP["int"].append("primarykey")
    self.TYPEMAP["int"].append("foreignkey")
    
    if not self._validatefields({k:v for k,v in fields.items() if not k.startswith("REF_")}):
      raise Exception(f"Invalid schema definition ({str(fields)})")
    
    if not self.__checktable():
      self.__createtable(table,fields)
    
    self.__addfieldconv()
    self.__addsqlops()
  
  def GetPrimaryKeyValue(self,q=[]):
    pkfieldar = [a for a in self.FIELDS.keys() if self.FIELDS[a] == "PrimaryKeyType"]
    if not len(pkfieldar) == 1:
      return None
    
    result = self.Query(q,pkfieldar,1)
    
    if not len(result) == 1:
      return None
    
    return (pkfieldar[0],result[0][0])
      
  
  def RunSql(self,s,count=0):
    results = self.CONN.cursor().execute(s)
    
    cmd = s.split(' ')[0]
    
    if cmd.upper() in ['INSERT','UPDATE','ALTER','CREATE','DELETE','DROP']:
      if self.USE_LOG:
        self.LOG_BUFFER.append(s)
      
      self.CONN.commit()
      
      if self.CACHE_READY:
        self.CACHE_READY = False
    else:
      return results.fetchall() if count == 0 else results.fetchmany(count)
  
  def AddField(self,fname,ftype):
    super().AddField(fname,ftype)
    self.RunSql(f'ALTER TABLE {self.TABLE} ADD COLUMN {fname} {ftype};')
  
  def Insert(self,row={}):
    insert_sql_fields = ",".join([a for a in row.keys()])
    insert_sql_values = ",".join([self.FIELD_CONV[a](row[a]) for a in row.keys()])
    insert_sql = f'INSERT INTO {self.TABLE}(' + insert_sql_fields + ") VALUES (" + insert_sql_values + ");"
    self.RunSql(insert_sql)

    if "PrimaryKeyType" in self.FIELDS.values():
      pk = [k for (k,v) in self.FIELDS.items() if v == 'PrimaryKeyType']
      q = [(k,'EQ',v) for (k,v) in row.items()]
      result = self.Query(q,pk)
      if len(result) == 1 and len(result[0]) == 1:
        return result[0][0]
    else:
      return None
  
  def BulkInsert(self,rowset=[]):
    insert_sql_fields = ",".join([a for a in rowset[0].keys()])
    
    insert_sql_value_list = []
    
    for row in rowset:
      insert_sql_value_list.append("(" + ",".join([self.FIELD_CONV[a](row[a]) for a in row.keys()]) + ")")
    
    insert_sql_values = ",".join(insert_sql_value_list)
    
    insert_sql = f'INSERT INTO {self.TABLE}(' + insert_sql_fields + ") VALUES " + insert_sql_values + ";"
    self.RunSql(insert_sql)
  
  def Delete(self,q):
    delete_sql_where = " AND ".join([self.COMPARES[(self.FIELDS[a[0]],a[1],self.FIELDS[a[0]])](a[0],a[2]) for a in q])
    delete_sql = f'DELETE FROM {self.TABLE} WHERE ' + delete_sql_where + ';'    
    self.RunSql(delete_sql)
  
  def Update(self,q,updates=[]):
    update_sql_set = ','.join([f'{a[0]} = {self.FIELD_CONV[a[0]](a[1])}' for a in updates])
    update_sql_where = " AND ".join([self.COMPARES[(self.FIELDS[a[0]],a[1],self.FIELDS[a[0]])](a[0],a[2]) for a in q])
    update_sql = f'UPDATE {self.TABLE} SET ' + update_sql_set + ((" WHERE " + update_sql_where) if len(q) > 0 else "") + ';'
    self.RunSql(update_sql)
  
  def Query(self,q=[],f=[],count=0,view=False):
    query_sql_fields = ','.join(f) if len(f) > 0 else "*"
    query_sql_where = " AND ".join([self.COMPARES[(self.FIELDS[a[0]],a[1],self.FIELDS[a[0]])](a[0],a[2]) for a in q])
    query_sql = f'SELECT ' + query_sql_fields + f' FROM {self.TABLE}' + ((' WHERE ' + query_sql_where) if len(q) > 0 else "") + ';'
    
    return self.RunSql(query_sql,count) if not view else {"type":"single","fields":self.FIELDS,"sql":query_sql}
  
  def Cache(self):
    self.clear()
    
    select_sql_fields = ",".join([a for a in self.FIELDS.keys()])
    select_sql = f"SELECT " + select_sql_fields + f" FROM {self.TABLE};"
    result = self.RunSql(select_sql)
    
    for sql_row in result:
      row = {}
      for field in [(i,v) for i,v in enumerate(self.FIELDS.keys())]:
        row[field[1]] = sql_row[field[0]]
      
      super().Insert(row)
    
    self.CACHE_READY = True
  
  def __createtable(self,table,fields):
    create_sql_fields = ",".join([f'{a} {self.FieldTypeMap[fields[a]].replace("<F>",a)}' for a in fields.keys() if not a.startswith("REF_")])
    create_sql_fk = ",".join([f"FOREIGN KEY ({a}) REFERENCES {fields["REF_" + a].split('.')[0] + "(" + fields["REF_" + a].split('.')[1] + ")"}" for a in [re.sub(r'REF_','',b) for b in fields.keys() if b.startswith("REF_")]])
    create_sql = f'CREATE TABLE {table} (' + create_sql_fields + (("," + create_sql_fk) if len(create_sql_fk) > 0 else "") + ');'
    self.RunSql(create_sql);
      
  def __checktable(self):
    check_sql = f"SELECT name FROM sqlite_master WHERE type='table' AND name='{self.TABLE}';"
    return len(self.RunSql(check_sql,1)) == 1
  
  def __createdbfile(self,f):
    c = sqlite3.connect(f)
    c.commit()
  
  def __del__(self):
    self.CONN.close()
  
  def __readschema(self):
    f = self.__getsqlfieldlist();
    d = {}
    
    for this_f in f:
      bare_field = this_f[1].replace(this_f[0],"<F>")

      ddtype = self.__unmapfieldtype(bare_field)
      d[this_f[0]] = ddtype
    
    return d
  
  def __connect(self):
    self.CONN = sqlite3.connect(self.DBFILE)
  
  def __unmapfieldtype(self,t):
    if not t in self.FieldTypeMap.values():
      raise Exception(f"Invalid field type ({t})")
    
    return [a[0] for a in self.FieldTypeMap.items() if a[1] == t][0]
  
  def __getsqlfieldlist(self):
    read_sql = f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{self.TABLE}';"
    result =  self.RunSql(read_sql,1)
    
    if not len(result) == 1:
      raise Exception(f"Schema error:  table not found ({self.TABLE})")
    else:
      create_sql = result[0][0]
      field_list = [[a.strip().split(" ")[0]," ".join(a.strip().split(" ")[1:])] for a in re.sub(r'^CREATE TABLE [^\(]+\((.+)\)$','\\1',create_sql).split(',') if not a.strip().startswith('FOREIGN KEY')]
      return field_list
  
  def __addfieldconv(self):
    self.FIELD_CONV = {}
    
    for f in [a for a in self.FIELDS.keys() if not a.startswith("REF_")]:
      if self.FIELDS[f] == "StringType":
        self.FIELD_CONV[f] = self.__str2sql
      elif self.FIELDS[f] == "NumberType" or self.FIELDS[f] == "BooleanType" or self.FIELDS[f] == "PrimaryKeyType" or self.FIELDS[f] == "ForeignKeyType":
        self.FIELD_CONV[f] = self.__num2sql
      else:
        raise Exception(f'Invalid field type ({f})')
  
  def __addsqlops(self):
    self.COMPARES = {}
    self.COMPARES[("StringType","EQ","StringType")] = self.__streq2sql
    self.COMPARES[("StringType","NE","StringType")] = self.__strne2sql
    self.COMPARES[("StringType","ST","StringType")] = self.__strst2sql
    self.COMPARES[("StringType","EN","StringType")] = self.__stren2sql
    self.COMPARES[("StringType","CN","StringType")] = self.__strcn2sql
    
    self.COMPARES[("NumberType","EQ","NumberType")] = self.__numeq2sql
    self.COMPARES[("NumberType","NE","NumberType")] = self.__numne2sql
    self.COMPARES[("NumberType","GT","NumberType")] = self.__numgt2sql
    self.COMPARES[("NumberType","LT","NumberType")] = self.__numlt2sql
    self.COMPARES[("NumberType","GE","NumberType")] = self.__numge2sql
    self.COMPARES[("NumberType","LE","NumberType")] = self.__numle2sql
    
    self.COMPARES[("BooleanType","EQ","BooleanType")] = self.__numeq2sql
    self.COMPARES[("BooleanType","NE","BooleanType")] = self.__numne2sql
    self.COMPARES[("BooleanType","GT","BooleanType")] = self.__numgt2sql
    self.COMPARES[("BooleanType","LT","BooleanType")] = self.__numlt2sql
    self.COMPARES[("BooleanType","GE","BooleanType")] = self.__numge2sql
    self.COMPARES[("BooleanType","LE","BooleanType")] = self.__numle2sql
    
    self.COMPARES[("PrimaryKeyType","EQ","PrimaryKeyType")] = self.__numeq2sql
    self.COMPARES[("PrimaryKeyType","NE","PrimaryKeyType")] = self.__numne2sql
    self.COMPARES[("PrimaryKeyType","GT","PrimaryKeyType")] = self.__numgt2sql
    self.COMPARES[("PrimaryKeyType","LT","PrimaryKeyType")] = self.__numlt2sql
    self.COMPARES[("PrimaryKeyType","GE","PrimaryKeyType")] = self.__numge2sql
    self.COMPARES[("PrimaryKeyType","LE","PrimaryKeyType")] = self.__numle2sql
    
    self.COMPARES[("ForeignKeyType","EQ","ForeignKeyType")] = self.__numeq2sql
    self.COMPARES[("ForeignKeyType","NE","ForeignKeyType")] = self.__numne2sql
    self.COMPARES[("ForeignKeyType","GT","ForeignKeyType")] = self.__numgt2sql
    self.COMPARES[("ForeignKeyType","LT","ForeignKeyType")] = self.__numlt2sql
    self.COMPARES[("ForeignKeyType","GE","ForeignKeyType")] = self.__numge2sql
    self.COMPARES[("ForeignKeyType","LE","ForeignKeyType")] = self.__numle2sql
  
  def __str2sql(self,v):
    return f"'{v}'"
  
  def __num2sql(self,v):
    return f"{v}"
  
  def __streq2sql(self,v1,v2):
    return v1 + " == " + self.__str2sql(v2)
  
  def __strne2sql(self,v1,v2):
    return v1 + " <> " + self.__str2sql(v2)
  
  def __strst2sql(self,v1,v2):
    return v1 + " LIKE " + re.sub(r"'$","%'",self.__str2sql(v2))
  
  def __stren2sql(self,v1,v2):
    return v1 + " LIKE " + re.sub(r"^'","'%",self.__str2sql(v2))
  
  def __strcn2sql(self,v1,v2):
    return v1 + " LIKE " + re.sub(r"^'([^']+)'",r"'%\1%'",self.__str2sql(v2))
  
  def __numeq2sql(self,v1,v2):
    return v1 + " == " + self.__num2sql(v2)
  
  def __numne2sql(self,v1,v2):
    return v1 + " <> " + self.__num2sql(v2)
  
  def __numgt2sql(self,v1,v2):
    return v1 + " > " + self.__num2sql(v2)
  
  def __numlt2sql(self,v1,v2):
    return v1 + " < " + self.__num2sql(v2)
  
  def __numge2sql(self,v1,v2):
    return v1 + " >= " + self.__num2sql(v2)
  
  def __numle2sql(self,v1,v2):
    return v1 + " <= " + self.__num2sql(v2)

class SqliteDefGroup(dict):
  def __init__(self,dbfile="",maxlog=10000000):
    if len(dbfile) == 0:
      raise Exception("No DB specified")
    
    if not os.path.exists(dbfile):
      self.__createdbfile(dbfile)
      
    self.DBFILE = dbfile
    self.LOGFILE = dbfile + ".log.gz"
    self.MAX_LOG = maxlog
    
    self.NEXT_LOG_SAVE = len(glob.glob(self.LOGFILE + ".*")) + 1
    
    if self.__class__.__name__ == "SqliteDefGroup":
      self.__populatetables()

    self.JOIN_CONDS = {}
    self.JOIN_CONDS['EQ'] = "=="
    self.JOIN_CONDS['GT'] = ">"
    self.JOIN_CONDS['LT'] = "<"
    self.JOIN_CONDS['CN'] = "LIKE"
    
    self.VIEWS = {}
  
  def Insert(self,t,row={}):
    newpk = self[t].Insert(row)
    self.__commitlogs(t)
    return newpk
  
  def BulkInsert(self,t,rowset=[]):
    self[t].BulkInsert(rowset)
    self.__commitlogs(t)
  
  def Update(self,t,q,update=[]):
    self[t].Update(q,update)
    self.__commitlogs(t)
  
  def Delete(self,t,q):
    self[t].Delete(q)
    self.__commitlogs(t)
  
  def Query(self,t,q=[],f=[],count=0,view=False):
    if t in self.keys():
      return self[t].Query(q,f,count,view)
    elif t in self.VIEWS.keys():
      usetab = self[list(self.keys())[0]]

      query_sql_fields = ','.join(f) if len(f) > 0 else "*"
      query_sql_where = " AND ".join([usetab.COMPARES[(self.VIEWS[t][a[0]],a[1],self.VIEWS[t][a[0]])](a[0],a[2]) for a in q])
      query_sql = f'SELECT ' + query_sql_fields + f' FROM {t}' + ((' WHERE ' + query_sql_where) if len(q) > 0 else "") + ';'

      return usetab.RunSql(query_sql,count)
  
  def JoinQuery(self,t,f={},j={},where=[],jointype=None,view=False):
    all_fields = {f"a.{k}":v for (k,v) in self[t].FIELDS.items()}
    tmap = {t:'a'}
    
    jar = list(string.ascii_lowercase[1:])
    
    join_list = []
    for this_join in j.keys():
      tmap[this_join] = jar[list(j.keys()).index(this_join)]
      all_fields = all_fields | {f"{tmap[this_join]}.{k}":v for (k,v) in self[this_join].FIELDS.items()}
    
    for this_join in j.keys():
      on_query = " AND ".join([f"{self.__swaptable(tmap,a[0])} {self.JOIN_CONDS[a[1]]} {self.__swaptable(tmap,a[2])}" for a in j[this_join]])
      join_type = f"{jointype} " if jointype else ""
      join_list.append(f"{join_type}JOIN {this_join} {tmap[this_join]} ON {on_query}")

    join_fields = {v:all_fields[self.__swaptable(tmap,k)] for (k,v) in f.items()}
    get_fields = ",".join([f"{self.__swaptable(tmap,k)} AS \"{v}\"" for (k,v) in f.items()]) if len(f) > 0 else "*"
    where_query = " AND ".join([self[t].COMPARES[(all_fields[self.__swaptable(tmap,a[0])],a[1],all_fields[self.__swaptable(tmap,a[0])])](self.__swaptable(tmap,a[0]),a[2]) for a in where])
    join_sql = f"SELECT {get_fields} FROM {t} a " + (" ".join(join_list) if len(join_list) > 0 else "") + ((f" WHERE {where_query}") if len(where) > 0 else "") + ";"
    
    return self[t].RunSql(join_sql) if not view else {"type":"join","t":t,"j":j,"fields":join_fields,"sql":join_sql}
  
  def CreateTableView(self,n,t,q=[],f=[]):
    if not n in self.VIEWS.keys():
      viewobj = self.Query(t,q,f,view=True)
      usefield = {k:self[t].FIELDS[k] for k in f}
      create_sql = f"CREATE VIEW {n} AS {viewobj["sql"]}"
      self[t].RunSql(create_sql)
      
      self.VIEWS[n] = usefield
  
  def CreateJoinView(self,n,t,f={},j={},where=[],jointype=None):
    if not n in self.VIEWS.keys():
      # throw error if view field name contains a space
      if len([a for a in f.values() if ' ' in a]) > 0:
        raise Exception(f"Invalid view field names ({",".join(f.values())})")
      
      viewobj = self.JoinQuery(t,f,j,where,jointype,view=True)
      create_sql = f"CREATE VIEW {n} AS {viewobj["sql"]}"
      self[t].RunSql(create_sql)
      
      self.VIEWS[n] = viewobj['fields']
  
  def CreateTable(self,t,f):
    self[t] = SqliteDef(f,self.DBFILE,t,True)
    self.__commitlogs(t)
  
  def ExistsTable(self,t):
    return t in self.keys()
  
  def __swaptable(self,m,s):
    for t in m.keys():
      s = re.sub(re.compile(f"{t}\\.(.*)$"),f"{m[t]}.\\1",s)
    return s
  
  def __commitlogs(self,t):
    l = self[t].LOG_BUFFER.copy()
    self[t].LOG_BUFFER.clear()
    
    l.reverse()
    
    logfile = gzip.open(self.LOGFILE,"at",encoding='utf-8')
    
    for line in l:
      logfile.write(line + "\n")
    
    logfile.close()
    
    if os.path.getsize(self.LOGFILE) > self.MAX_LOG:
      os.rename(self.LOGFILE,self.LOGFILE + self.NEXT_LOG_SAVE)
      self.NEXT_LOG_SAVE = self.NEXT_LOG_SAVE + 1
  
  def __populatetables(self):
    for this_table in self.__listtables():
      self[this_table] = SqliteDef(dbfile=self.DBFILE,table=this_table,uselog=True)
  
  def __listtables(self):
    t = []
    c = sqlite3.connect(self.DBFILE)
    resp = c.cursor().execute("SELECT name FROM sqlite_master WHERE type='table' AND name <> 'sqlite_sequence';")
    
    for table in resp.fetchall():
      t.append(table[0])
    
    return t
  
  def __createdbfile(self,f):
    c = sqlite3.connect(f)
    c.commit()
