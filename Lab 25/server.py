"""RoadAid Lab 25 local demo. Run: python server.py"""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs
import sqlite3,json,secrets,hashlib,time,mimetypes
ROOT=Path(__file__).parent;DB=ROOT/'roadaid.db'
def db():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c
def init():
 with db() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT,email TEXT UNIQUE,password TEXT,role TEXT,phone TEXT DEFAULT '',area TEXT DEFAULT '',created TEXT DEFAULT CURRENT_TIMESTAMP);CREATE TABLE IF NOT EXISTS mechanics(id INTEGER PRIMARY KEY,user_id INTEGER UNIQUE REFERENCES users(id),business TEXT,service TEXT,area TEXT,address TEXT,lat REAL,lng REAL,phone TEXT,description TEXT,license TEXT,approved INTEGER DEFAULT 0,available INTEGER DEFAULT 1);CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id),mechanic_id INTEGER REFERENCES mechanics(id),rating INTEGER,message TEXT,created TEXT DEFAULT CURRENT_TIMESTAMP);CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER,admin INTEGER DEFAULT 0,expires INTEGER);''')
  if not c.execute('SELECT id FROM users WHERE role="admin"').fetchone():c.execute('INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)',('RoadAid Admin','admin@roadaid.test',hashlib.sha256(b'road123').hexdigest(),'admin'))
  examples=[('Ari Morgan','ari@roadaid.test','mechanic123','Ari’s Roadside Auto','Battery and tire help','Old Town','14 Pine Street',45.523,-122.674,'555-4401','Mobile roadside repairs, jump starts, and tire changes.','LIC-OR-2041'),('Sam Lee','sam@roadaid.test','mechanic123','Riverbend Mobile Mechanic','Engine and towing support','Riverside','80 Bridge Avenue',45.513,-122.672,'555-4402','Licensed mobile mechanic for breakdown support and basic diagnostics.','LIC-OR-3119')]
  for n,e,p,b,s,a,addr,lat,lng,ph,desc,lic in examples:
   if not c.execute('SELECT id FROM users WHERE email=?',(e,)).fetchone():
    uid=c.execute('INSERT INTO users(name,email,password,role,phone,area) VALUES(?,?,?,?,?,?)',(n,e,hashlib.sha256(p.encode()).hexdigest(),'mechanic',ph,a)).lastrowid;c.execute('INSERT INTO mechanics(user_id,business,service,area,address,lat,lng,phone,description,license,approved) VALUES(?,?,?,?,?,?,?,?,?,?,1)',(uid,b,s,a,addr,lat,lng,ph,desc,lic))
  if not c.execute('SELECT id FROM users WHERE email=?',('driver@roadaid.test',)).fetchone():c.execute('INSERT INTO users(name,email,password,role,phone,area) VALUES(?,?,?,?,?,?)',('Casey Driver','driver@roadaid.test',hashlib.sha256(b'driver123').hexdigest(),'customer','555-4400','Old Town'))
class H(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def send(self,s,d):
  b=json.dumps(d).encode();self.send_response(s);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.send_header('Access-Control-Allow-Origin','*');self.end_headers();self.wfile.write(b)
 def auth(self,c,role=None,admin=False):
  t=self.headers.get('Authorization','').replace('Bearer ','');u=c.execute('SELECT s.admin,s.user_id,a.name admin_name,a.email admin_email,x.name,x.email,x.role FROM sessions s LEFT JOIN users a ON a.role="admin" LEFT JOIN users x ON x.id=s.user_id WHERE s.token=? AND s.expires>?',(t,int(time.time()))).fetchone()
  if not u:raise PermissionError('Please sign in to continue.')
  if admin and not u['admin']:raise PermissionError('Administrator access required.')
  if role and u['role']!=role:raise PermissionError('This page is for '+role+' accounts.')
  return u
 def do_OPTIONS(self):self.send_response(204);self.send_header('Access-Control-Allow-Origin','*');self.send_header('Access-Control-Allow-Headers','Authorization, Content-Type');self.send_header('Access-Control-Allow-Methods','GET,POST,PUT,OPTIONS');self.end_headers()
 def do_GET(self):
  p=urlparse(self.path).path;q=parse_qs(urlparse(self.path).query)
  if p=='/' or p=='/index.html':
   b=(ROOT/'index.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
  if p in('/styles.css','/script.js'):
   b=(ROOT/p[1:]).read_bytes();self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(p)[0] or 'text/plain');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
  with db() as c:
   try:
    if p=='/api/mechanics':
     sql='SELECT m.*,u.name,ROUND(AVG(f.rating),1) rating,COUNT(f.id) reviews FROM mechanics m JOIN users u ON u.id=m.user_id LEFT JOIN feedback f ON f.mechanic_id=m.id WHERE m.approved=1 AND m.available=1';args=[];term=q.get('q',[''])[0]
     if term:sql+=' AND (m.area LIKE ? OR m.service LIKE ? OR m.business LIKE ?)';args += [f'%{term}%']*3
     self.send(200,[dict(x) for x in c.execute(sql+' GROUP BY m.id ORDER BY rating DESC',args).fetchall()]);return
    u=self.auth(c)
    if p=='/api/me':self.send(200,{'id':u['user_id'],'name':u['name'],'email':u['email'],'role':u['role']});return
    if p=='/api/mechanic/profile':self.auth(c,role='mechanic');self.send(200,dict(c.execute('SELECT * FROM mechanics WHERE user_id=?',(u['user_id'],)).fetchone() or {}));return
    if p=='/api/mechanic/feedback':
     self.auth(c,role='mechanic');self.send(200,[dict(x) for x in c.execute('SELECT f.*,u.name customer FROM feedback f JOIN users u ON u.id=f.user_id WHERE f.mechanic_id=(SELECT id FROM mechanics WHERE user_id=?) ORDER BY f.id DESC',(u['user_id'],)).fetchall()]);return
    if p=='/api/admin/mechanics':self.auth(c,admin=True);self.send(200,[dict(x) for x in c.execute('SELECT m.*,u.name,u.email FROM mechanics m JOIN users u ON u.id=m.user_id ORDER BY m.id DESC').fetchall()]);return
    self.send(404,{'error':'Not found'})
   except PermissionError as e:self.send(401,{'error':str(e)})
 def do_POST(self):
  p=urlparse(self.path).path
  try:d=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))) or b'{}')
  except:self.send(400,{'error':'Invalid request.'});return
  with db() as c:
   try:
    if p=='/api/register':
     role=d.get('role','customer');email=d.get('email','').lower().strip()
     if role not in('customer','mechanic') or '@' not in email or len(d.get('password',''))<8:self.send(400,{'error':'Complete registration details and use a password of at least 8 characters.'});return
     uid=c.execute('INSERT INTO users(name,email,password,role,phone,area) VALUES(?,?,?,?,?,?)',(d.get('name',''),email,hashlib.sha256(d['password'].encode()).hexdigest(),role,d.get('phone',''),d.get('area',''))).lastrowid
     if role=='mechanic':c.execute('INSERT INTO mechanics(user_id,business,service,area,address,lat,lng,phone,description,license) VALUES(?,?,?,?,?,?,?,?,?,?)',(uid,d.get('business',''),d.get('service',''),d.get('area',''),d.get('address',''),float(d.get('lat',0)),float(d.get('lng',0)),d.get('phone',''),d.get('description',''),d.get('license','')))
     self.send(201,{'ok':True,'message':'Mechanic listings are visible after admin approval.' if role=='mechanic' else 'Account created.'});return
    if p=='/api/login':
     u=c.execute('SELECT * FROM users WHERE email=? AND password=?',(d.get('email','').lower().strip(),hashlib.sha256(d.get('password','').encode()).hexdigest())).fetchone()
     if not u or bool(d.get('admin'))!=(u['role']=='admin'):self.send(401,{'error':'Login details not recognized.'});return
     t=secrets.token_urlsafe(32);c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(t,u['id'],1 if u['role']=='admin' else 0,int(time.time())+86400));self.send(200,{'token':t,'user':{'name':u['name'],'email':u['email'],'role':u['role']}});return
    if p=='/api/logout':c.execute('DELETE FROM sessions WHERE token=?',(self.headers.get('Authorization','').replace('Bearer ',''),));self.send(200,{'ok':True});return
    if p=='/api/mechanic/business':
     u=self.auth(c,role='mechanic');c.execute('UPDATE mechanics SET business=?,service=?,area=?,address=?,lat=?,lng=?,phone=?,description=?,license=?,available=? WHERE user_id=?',(d.get('business',''),d.get('service',''),d.get('area',''),d.get('address',''),float(d.get('lat',0)),float(d.get('lng',0)),d.get('phone',''),d.get('description',''),d.get('license',''),int(bool(d.get('available',True))),u['user_id']));self.send(200,{'ok':True});return
    if p=='/api/feedback':
     u=self.auth(c,role='customer');c.execute('INSERT INTO feedback(user_id,mechanic_id,rating,message) VALUES(?,?,?,?)',(u['user_id'],d.get('mechanic_id'),max(1,min(5,int(d.get('rating',5)))),d.get('message','')));self.send(201,{'ok':True});return
    if p.startswith('/api/admin/mechanics/'):
     self.auth(c,admin=True);mid=int(p.rsplit('/',1)[-1]);c.execute('UPDATE mechanics SET approved=? WHERE id=?',(1 if d.get('approved') else 0,mid));self.send(200,{'ok':True});return
    self.send(404,{'error':'Not found'})
   except sqlite3.IntegrityError:self.send(409,{'error':'That email is already registered.'})
   except PermissionError as e:self.send(401,{'error':str(e)})
   except Exception as e:self.send(400,{'error':str(e)})
if __name__=='__main__':init();print('RoadAid at http://localhost:8025');ThreadingHTTPServer(('127.0.0.1',8025),H).serve_forever()
