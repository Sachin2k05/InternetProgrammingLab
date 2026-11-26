"""CleanRoute Lab 22 local demo. Run: python server.py"""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import sqlite3,json,secrets,hashlib,time,mimetypes,math
ROOT=Path(__file__).parent;DB=ROOT/'cleanroute.db'
def db():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c
def init():
 with db() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT,email TEXT UNIQUE,password TEXT,role TEXT,area TEXT DEFAULT '',approved INTEGER DEFAULT 1);CREATE TABLE IF NOT EXISTS bins(id INTEGER PRIMARY KEY,label TEXT,area TEXT,address TEXT,lat REAL,lng REAL,category TEXT,fill INTEGER DEFAULT 0,status TEXT DEFAULT 'Active');CREATE TABLE IF NOT EXISTS routes(id INTEGER PRIMARY KEY,driver_id INTEGER REFERENCES users(id),name TEXT,day TEXT,stops TEXT,status TEXT DEFAULT 'Assigned',created TEXT DEFAULT CURRENT_TIMESTAMP);CREATE TABLE IF NOT EXISTS complaints(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id),bin_id INTEGER REFERENCES bins(id),area TEXT,details TEXT,status TEXT DEFAULT 'Received',created TEXT DEFAULT CURRENT_TIMESTAMP);CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER,admin INTEGER DEFAULT 0,expires INTEGER);''')
  if not c.execute('SELECT id FROM users WHERE role="admin"').fetchone():c.execute('INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)',('CleanRoute Admin','admin@cleanroute.test',hashlib.sha256(b'clean123').hexdigest(),'admin'))
  if not c.execute('SELECT id FROM users WHERE role="driver"').fetchone():c.execute('INSERT INTO users(name,email,password,role,area) VALUES(?,?,?,?,?)',('Jordan Driver','driver@cleanroute.test',hashlib.sha256(b'drive123').hexdigest(),'driver','Old Town'))
  if not c.execute('SELECT id FROM users WHERE role="public"').fetchone():c.execute('INSERT INTO users(name,email,password,role,area) VALUES(?,?,?,?,?)',('Taylor Neighbor','neighbor@cleanroute.test',hashlib.sha256(b'public123').hexdigest(),'public','Old Town'))
  if not c.execute('SELECT id FROM bins LIMIT 1').fetchone():
   for x in [('Bin A','Old Town','Market Square',45.522,-122.676,'Mixed',72),('Bin B','Old Town','Pine Street',45.527,-122.671,'Recycling',48),('Bin C','Riverside','River Park',45.516,-122.668,'Mixed',89),('Bin D','Riverside','Bridge Avenue',45.512,-122.674,'Organic',34)]:c.execute('INSERT INTO bins(label,area,address,lat,lng,category,fill) VALUES(?,?,?,?,?,?,?)',x)
def pack(r):return dict(r) if r else None
class H(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def send(self,s,d):
  b=json.dumps(d).encode();self.send_response(s);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.send_header('Access-Control-Allow-Origin','*');self.end_headers();self.wfile.write(b)
 def auth(self,c,role=None,admin=False):
  t=self.headers.get('Authorization','').replace('Bearer ','');u=c.execute('SELECT s.admin,s.user_id,a.name admin_name,a.email admin_email,x.name,x.email,x.role FROM sessions s LEFT JOIN users a ON a.role="admin" LEFT JOIN users x ON x.id=s.user_id WHERE s.token=? AND s.expires>?',(t,int(time.time()))).fetchone()
  if not u:raise PermissionError('Please sign in.')
  if admin and not u['admin']:raise PermissionError('Administrator access required.')
  if role and u['role']!=role:raise PermissionError('This page is for '+role+' accounts.')
  return u
 def do_OPTIONS(self):self.send_response(204);self.send_header('Access-Control-Allow-Origin','*');self.send_header('Access-Control-Allow-Headers','Authorization, Content-Type');self.send_header('Access-Control-Allow-Methods','GET,POST,PUT,OPTIONS');self.end_headers()
 def do_GET(self):
  p=urlparse(self.path).path
  if p=='/' or p=='/index.html':
   b=(ROOT/'index.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
  if p in('/styles.css','/script.js'):
   b=(ROOT/p[1:]).read_bytes();self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(p)[0] or 'text/plain');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
  with db() as c:
   try:
    if p=='/api/bins':self.send(200,[pack(r) for r in c.execute('SELECT * FROM bins ORDER BY area,label').fetchall()]);return
    u=self.auth(c)
    if p=='/api/me':self.send(200,{'name':u['admin_name'] if u['admin'] else u['name'],'email':u['admin_email'] if u['admin'] else u['email'],'role':'admin' if u['admin'] else u['role']});return
    if p=='/api/complaints':
     if u['admin']:rows=c.execute('SELECT p.*,b.label bin FROM complaints p LEFT JOIN bins b ON b.id=p.bin_id ORDER BY p.id DESC').fetchall()
     elif u['role']=='public':rows=c.execute('SELECT p.*,b.label bin FROM complaints p LEFT JOIN bins b ON b.id=p.bin_id WHERE p.user_id=? ORDER BY p.id DESC',(u['user_id'],)).fetchall()
     else:raise PermissionError('Public account access required.')
     self.send(200,[pack(r) for r in rows]);return
    if p=='/api/admin/drivers':self.auth(c,admin=True);self.send(200,[pack(r) for r in c.execute("SELECT id,name,email,area FROM users WHERE role='driver'").fetchall()]);return
    if p=='/api/admin/report':
     self.auth(c,admin=True);self.send(200,{'bins':c.execute('SELECT COUNT(*) n FROM bins').fetchone()['n'],'complaints':c.execute('SELECT COUNT(*) n FROM complaints').fetchone()['n'],'open':c.execute("SELECT COUNT(*) n FROM complaints WHERE status!='Resolved'").fetchone()['n'],'areas':[pack(x) for x in c.execute('SELECT area,COUNT(*) complaints FROM complaints GROUP BY area').fetchall()]});return
    if p=='/api/driver/routes':self.auth(c,role='driver');self.send(200,[pack(r) for r in c.execute('SELECT * FROM routes WHERE driver_id=? ORDER BY id DESC',(u['user_id'],)).fetchall()]);return
    self.send(404,{'error':'Not found'})
   except PermissionError as e:self.send(401,{'error':str(e)})
 def do_POST(self):
  p=urlparse(self.path).path
  try:d=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))) or b'{}')
  except:self.send(400,{'error':'Invalid request.'});return
  with db() as c:
   try:
    if p=='/api/register':
     email=d.get('email','').lower().strip();role=d.get('role','public')
     if role not in('public','driver') or '@' not in email or len(d.get('password',''))<8:self.send(400,{'error':'Complete the registration details and use a password of at least 8 characters.'});return
     c.execute('INSERT INTO users(name,email,password,role,area) VALUES(?,?,?,?,?)',(d.get('name',''),email,hashlib.sha256(d['password'].encode()).hexdigest(),role,d.get('area','')));self.send(201,{'ok':True});return
    if p=='/api/login':
     email=d.get('email','').lower().strip();u=c.execute('SELECT * FROM users WHERE email=? AND password=?',(email,hashlib.sha256(d.get('password','').encode()).hexdigest())).fetchone()
     if not u or bool(d.get('admin'))!=(u['role']=='admin'):self.send(401,{'error':'Login details not recognized.'});return
     t=secrets.token_urlsafe(32);c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(t,u['id'],1 if u['role']=='admin' else 0,int(time.time())+86400));self.send(200,{'token':t});return
    if p=='/api/logout':c.execute('DELETE FROM sessions WHERE token=?',(self.headers.get('Authorization','').replace('Bearer ',''),));self.send(200,{'ok':True});return
    if p=='/api/complaints':
     u=self.auth(c,role='public');c.execute('INSERT INTO complaints(user_id,bin_id,area,details) VALUES(?,?,?,?)',(u['user_id'],d.get('bin_id') or None,d.get('area',''),d.get('details','')));self.send(201,{'ok':True});return
    if p=='/api/admin/bins':
     self.auth(c,admin=True);c.execute('INSERT INTO bins(label,area,address,lat,lng,category,fill) VALUES(?,?,?,?,?,?,?)',(d.get('label',''),d.get('area',''),d.get('address',''),float(d.get('lat',0)),float(d.get('lng',0)),d.get('category','Mixed'),int(d.get('fill',0))));self.send(201,{'ok':True});return
    if p=='/api/admin/route':
     u=self.auth(c,admin=True);driver=c.execute("SELECT id FROM users WHERE id=? AND role='driver'",(d.get('driver_id'),)).fetchone();bins=[pack(x) for x in c.execute('SELECT * FROM bins WHERE area=? AND status="Active" AND fill>=?',(d.get('area',''),int(d.get('minimum_fill',0)))).fetchall()]
     if not driver:self.send(404,{'error':'Choose a driver.'});return
     if not bins:self.send(400,{'error':'No bins match that area and fill level.'});return
     # Nearest-neighbor ordering from a depot coordinate, using local coordinates.
     current=(float(d.get('depot_lat',45.52)),float(d.get('depot_lng',-122.68)));ordered=[]
     while bins:
      nxt=min(bins,key=lambda b:math.hypot(b['lat']-current[0],b['lng']-current[1]));bins.remove(nxt);ordered.append(nxt);current=(nxt['lat'],nxt['lng'])
     route_id=c.execute('INSERT INTO routes(driver_id,name,day,stops) VALUES(?,?,?,?)',(driver['id'],d.get('name','Daily collection route'),d.get('day','Today'),json.dumps(ordered))).lastrowid;self.send(201,{'id':route_id,'stops':ordered});return
    if p=='/api/driver/load':
     u=self.auth(c,role='driver');rid=int(d.get('route_id',0));c.execute('UPDATE bins SET fill=? WHERE id=? AND EXISTS(SELECT 1 FROM routes WHERE id=? AND driver_id=?)',(max(0,min(100,100-int(d.get('collected',0)))),d.get('bin_id'),rid,u['user_id']));self.send(200,{'ok':True});return
    if p.startswith('/api/admin/complaint/'):
     self.auth(c,admin=True);c.execute('UPDATE complaints SET status=? WHERE id=?',(d.get('status','Reviewed'),int(p.rsplit('/',1)[-1])));self.send(200,{'ok':True});return
    if p.startswith('/api/driver/routes/'):
     u=self.auth(c,role='driver');c.execute('UPDATE routes SET status=? WHERE id=? AND driver_id=?',(d.get('status','In progress'),int(p.rsplit('/',1)[-1]),u['user_id']));self.send(200,{'ok':True});return
    self.send(404,{'error':'Not found'})
   except sqlite3.IntegrityError:self.send(409,{'error':'That email is already registered.'})
   except PermissionError as e:self.send(401,{'error':str(e)})
   except Exception as e:self.send(400,{'error':str(e)})
 def do_PUT(self):
  p=urlparse(self.path).path
  try:d=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))) or b'{}')
  except:self.send(400,{'error':'Invalid request.'});return
  with db() as c:
   try:
    self.auth(c,admin=True);bid=int(p.rsplit('/',1)[-1]);c.execute('UPDATE bins SET label=?,area=?,address=?,lat=?,lng=?,category=?,fill=?,status=? WHERE id=?',(d.get('label',''),d.get('area',''),d.get('address',''),float(d.get('lat',0)),float(d.get('lng',0)),d.get('category','Mixed'),int(d.get('fill',0)),d.get('status','Active'),bid));self.send(200,{'ok':True})
   except PermissionError as e:self.send(401,{'error':str(e)})
   except Exception as e:self.send(400,{'error':str(e)})
 def do_DELETE(self):
  p=urlparse(self.path).path
  with db() as c:
   try:self.auth(c,admin=True);c.execute('UPDATE bins SET status="Inactive" WHERE id=?',(int(p.rsplit('/',1)[-1]),));self.send(200,{'ok':True})
   except PermissionError as e:self.send(401,{'error':str(e)})
   except Exception as e:self.send(400,{'error':str(e)})
if __name__=='__main__':init();print('CleanRoute at http://localhost:8022');ThreadingHTTPServer(('127.0.0.1',8022),H).serve_forever()
