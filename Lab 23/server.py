"""LifeDrop Lab 23 local demo. Run: python server.py"""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs
import sqlite3,json,secrets,hashlib,time,mimetypes
ROOT=Path(__file__).parent;DB=ROOT/'lifedrop.db'
def db():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c
def init():
 with db() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT,email TEXT UNIQUE,password TEXT,role TEXT,phone TEXT DEFAULT '',area TEXT DEFAULT '');CREATE TABLE IF NOT EXISTS donors(id INTEGER PRIMARY KEY,user_id INTEGER UNIQUE REFERENCES users(id),blood_group TEXT,age INTEGER,area TEXT,phone TEXT,available INTEGER DEFAULT 1,last_donation TEXT DEFAULT '',privacy TEXT DEFAULT 'Contact through app');CREATE TABLE IF NOT EXISTS banks(id INTEGER PRIMARY KEY,user_id INTEGER UNIQUE REFERENCES users(id),name TEXT,area TEXT,address TEXT,phone TEXT);CREATE TABLE IF NOT EXISTS stock(id INTEGER PRIMARY KEY,bank_id INTEGER REFERENCES banks(id),blood_group TEXT,units INTEGER DEFAULT 0,updated TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(bank_id,blood_group));CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER,expires INTEGER);''')
  samples=[('Rose City Blood Center','center@blood.test','blood12345','Portland Central','128 Cedar Plaza','555-3301',[('O+',8),('O-',2),('A+',5),('B+',4),('AB+',2)]),('Riverbend Community Hospital','river@blood.test','blood12345','Riverbend','40 River Road','555-3302',[('O+',4),('O-',1),('A+',3),('B-',2),('AB+',1)])]
  for name,email,pw,area,address,phone,stocks in samples:
   if not c.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone():
    uid=c.execute('INSERT INTO users(name,email,password,role,phone,area) VALUES(?,?,?,?,?,?)',(name,email,hashlib.sha256(pw.encode()).hexdigest(),'hospital',phone,area)).lastrowid;bid=c.execute('INSERT INTO banks(user_id,name,area,address,phone) VALUES(?,?,?,?,?)',(uid,name,area,address,phone)).lastrowid
    for g,n in stocks:c.execute('INSERT INTO stock(bank_id,blood_group,units) VALUES(?,?,?)',(bid,g,n))
  if not c.execute('SELECT id FROM users WHERE email=?',('donor@blood.test',)).fetchone():
   uid=c.execute('INSERT INTO users(name,email,password,role,phone,area) VALUES(?,?,?,?,?,?)',('Alex Donor','donor@blood.test',hashlib.sha256(b'donor1234').hexdigest(),'donor','555-3300','Portland Central')).lastrowid;c.execute('INSERT INTO donors(user_id,blood_group,age,area,phone) VALUES(?,?,?,?,?)',(uid,'O+',28,'Portland Central','555-3300'))
class H(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def send(self,s,d):
  b=json.dumps(d).encode();self.send_response(s);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.send_header('Access-Control-Allow-Origin','*');self.end_headers();self.wfile.write(b)
 def auth(self,c,role=None):
  t=self.headers.get('Authorization','').replace('Bearer ','');r=c.execute('SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>?',(t,int(time.time()))).fetchone()
  if not r:raise PermissionError('Please sign in to continue.')
  if role and r['role']!=role:raise PermissionError('This feature is for '+role+' accounts.')
  return r
 def do_OPTIONS(self):self.send_response(204);self.send_header('Access-Control-Allow-Origin','*');self.send_header('Access-Control-Allow-Headers','Authorization, Content-Type');self.send_header('Access-Control-Allow-Methods','GET,POST,PUT,OPTIONS');self.end_headers()
 def do_GET(self):
  p=urlparse(self.path).path;q=parse_qs(urlparse(self.path).query)
  if p=='/' or p=='/index.html':
   b=(ROOT/'index.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
  if p in('/styles.css','/script.js'):
   b=(ROOT/p[1:]).read_bytes();self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(p)[0] or 'text/plain');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
  with db() as c:
   try:
    group=q.get('group',['All'])[0];area=q.get('area',[''])[0]
    if p=='/api/donors':
     sql='SELECT d.id,d.blood_group,d.area,d.available,d.last_donation,d.privacy,u.name FROM donors d JOIN users u ON u.id=d.user_id WHERE d.available=1';args=[]
     if group!='All':sql+=' AND d.blood_group=?';args.append(group)
     if area:sql+=' AND d.area LIKE ?';args.append('%'+area+'%')
     self.send(200,[dict(r) for r in c.execute(sql,args).fetchall()]);return
    if p=='/api/banks':
     sql='SELECT b.*,s.blood_group,s.units,s.updated FROM banks b JOIN stock s ON s.bank_id=b.id';args=[]
     if group!='All':sql+=' WHERE s.blood_group=?';args.append(group)
     if area:sql+=(' AND' if args else ' WHERE')+' b.area LIKE ?';args.append('%'+area+'%')
     self.send(200,[dict(r) for r in c.execute(sql,args).fetchall()]);return
    u=self.auth(c)
    if p=='/api/me':self.send(200,{k:u[k] for k in('id','name','email','role','phone','area')});return
    if p=='/api/my-donor':self.auth(c,'donor');self.send(200,dict(c.execute('SELECT * FROM donors WHERE user_id=?',(u['id'],)).fetchone() or {}));return
    if p=='/api/hospital/stock':self.auth(c,'hospital');self.send(200,[dict(x) for x in c.execute('SELECT * FROM stock WHERE bank_id=(SELECT id FROM banks WHERE user_id=?)',(u['id'],)).fetchall()]);return
    self.send(404,{'error':'Not found'})
   except PermissionError as e:self.send(401,{'error':str(e)})
 def do_POST(self):
  p=urlparse(self.path).path
  try:d=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))) or b'{}')
  except:self.send(400,{'error':'Invalid request.'});return
  with db() as c:
   try:
    if p=='/api/register':
     role=d.get('role','donor');email=d.get('email','').lower().strip()
     if role not in('donor','hospital') or '@' not in email or len(d.get('password',''))<8:self.send(400,{'error':'Complete the form and use a password with at least 8 characters.'});return
     uid=c.execute('INSERT INTO users(name,email,password,role,phone,area) VALUES(?,?,?,?,?,?)',(d.get('name',''),email,hashlib.sha256(d['password'].encode()).hexdigest(),role,d.get('phone',''),d.get('area',''))).lastrowid
     if role=='donor':c.execute('INSERT INTO donors(user_id,blood_group,age,area,phone) VALUES(?,?,?,?,?)',(uid,d.get('blood_group','O+'),int(d.get('age',18)),d.get('area',''),d.get('phone','')))
     else:
      bid=c.execute('INSERT INTO banks(user_id,name,area,address,phone) VALUES(?,?,?,?,?)',(uid,d.get('name',''),d.get('area',''),d.get('address',''),d.get('phone',''))).lastrowid
      for g in('O+','O-','A+','A-','B+','B-','AB+','AB-'):c.execute('INSERT INTO stock(bank_id,blood_group,units) VALUES(?,?,0)',(bid,g))
     self.send(201,{'ok':True});return
    if p=='/api/login':
     u=c.execute('SELECT * FROM users WHERE email=? AND password=?',(d.get('email','').lower().strip(),hashlib.sha256(d.get('password','').encode()).hexdigest())).fetchone()
     if not u:self.send(401,{'error':'Email or password was not recognized.'});return
     t=secrets.token_urlsafe(32);c.execute('INSERT INTO sessions VALUES(?,?,?)',(t,u['id'],int(time.time())+86400));self.send(200,{'token':t,'user':{'name':u['name'],'email':u['email'],'role':u['role']}});return
    if p=='/api/logout':c.execute('DELETE FROM sessions WHERE token=?',(self.headers.get('Authorization','').replace('Bearer ',''),));self.send(200,{'ok':True});return
    if p=='/api/donor':
     u=self.auth(c,'donor');c.execute('UPDATE donors SET blood_group=?,age=?,area=?,phone=?,available=?,last_donation=?,privacy=? WHERE user_id=?',(d.get('blood_group'),int(d.get('age',18)),d.get('area',''),d.get('phone',''),int(bool(d.get('available',True))),d.get('last_donation',''),d.get('privacy','Contact through app'),u['id']));self.send(200,{'ok':True});return
    if p=='/api/hospital/stock':
     u=self.auth(c,'hospital');c.execute('UPDATE stock SET units=?,updated=CURRENT_TIMESTAMP WHERE bank_id=(SELECT id FROM banks WHERE user_id=?) AND blood_group=?',(int(d.get('units',0)),u['id'],d.get('blood_group')));self.send(200,{'ok':True});return
    self.send(404,{'error':'Not found'})
   except sqlite3.IntegrityError:self.send(409,{'error':'That email has already registered.'})
   except PermissionError as e:self.send(401,{'error':str(e)})
   except Exception as e:self.send(400,{'error':str(e)})
if __name__=='__main__':init();print('LifeDrop at http://localhost:8023');ThreadingHTTPServer(('127.0.0.1',8023),H).serve_forever()
