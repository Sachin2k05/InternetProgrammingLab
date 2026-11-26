"""InsureEasy local demo server. Start with: python server.py"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import hashlib, json, secrets, sqlite3
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parent; DB=ROOT/'insureeasy.db'; PORT=8001
PLANS=[
 {"id":1,"kind":"Health","name":"Everyday Health","provider":"Clover Care","price":148,"cover":5000000,"rating":4.8,"tag":"POPULAR","color":"mint","description":"Flexible health cover for everyday care, hospital stays, and the unexpected.","features":["₹5 lakh annual cover","Cashless care at 8,000+ hospitals","Annual health checkup","No-claim bonus"]},
 {"id":2,"kind":"Health","name":"Wellness Plus","provider":"Horizon Health","price":219,"cover":10000000,"rating":4.9,"tag":"GREAT COVER","color":"blue","description":"More room to breathe, with higher cover and thoughtful wellness benefits.","features":["₹10 lakh annual cover","Cashless care at 10,000+ hospitals","Daycare procedures covered","Mental wellness support"]},
 {"id":3,"kind":"Auto","name":"Roadside Ready","provider":"Northstar Auto","price":86,"cover":750000,"rating":4.7,"tag":"BEST VALUE","color":"peach","description":"Drive with confidence with a reliable policy and help when you need it.","features":["Comprehensive cover","24/7 roadside assistance","Zero depreciation add-on","Quick digital claims"]},
 {"id":4,"kind":"Auto","name":"Full Drive Cover","provider":"Evergreen Mutual","price":124,"cover":1500000,"rating":4.8,"tag":"POPULAR","color":"mint","description":"Extra protection for your car, your passengers, and the road ahead.","features":["₹15 lakh own-damage cover","Engine and key protection","Roadside assistance","Courtesy car benefit"]},
 {"id":5,"kind":"Home","name":"Home Sweet Home","provider":"Hearthstone","price":59,"cover":2500000,"rating":4.6,"tag":"EASY START","color":"blue","description":"Protect the place you love, from everyday accidents to bigger surprises.","features":["Building and contents cover","Fire and water damage","Temporary accommodation","Simple online claims"]},
 {"id":6,"kind":"Home","name":"Home Complete","provider":"Clover Care","price":97,"cover":5000000,"rating":4.9,"tag":"GREAT COVER","color":"peach","description":"Comprehensive cover for your home, belongings, and peace of mind.","features":["₹50 lakh building cover","Contents and valuables cover","Personal liability protection","Emergency home assistance"]}
]
def con():
 d=sqlite3.connect(DB);d.row_factory=sqlite3.Row;d.execute('PRAGMA foreign_keys=ON');return d
def init():
 with con() as d:
  d.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,phone TEXT DEFAULT '',role TEXT NOT NULL CHECK(role IN ('admin','agent','customer')),status TEXT DEFAULT 'approved',password_hash TEXT NOT NULL,salt TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS policies(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),plan_id INTEGER NOT NULL,kind TEXT NOT NULL,plan_name TEXT NOT NULL,premium REAL NOT NULL,cover REAL NOT NULL,due_date TEXT NOT NULL,status TEXT DEFAULT 'Active',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS claims(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),policy_id INTEGER NOT NULL REFERENCES policies(id),details TEXT NOT NULL,status TEXT DEFAULT 'Received',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),policy_id INTEGER NOT NULL REFERENCES policies(id),amount REAL NOT NULL,paid_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),policy_id INTEGER NOT NULL REFERENCES policies(id),message TEXT NOT NULL,channel TEXT DEFAULT 'SMS demo',sent_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS applications(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),plan_id INTEGER NOT NULL,status TEXT DEFAULT 'Pending',created_at TEXT DEFAULT CURRENT_TIMESTAMP);''')
  if not d.execute("SELECT id FROM users WHERE email='admin@insureeasy.test'").fetchone():
   salt=secrets.token_hex(16);pw=hashlib.pbkdf2_hmac('sha256',b'admin12345',salt.encode(),180000).hex();d.execute("INSERT INTO users(name,email,role,status,password_hash,salt) VALUES(?,?,?,?,?,?)",('InsureEasy Admin','admin@insureeasy.test','admin','approved',pw,salt))
class H(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def out(self,status,obj,typ='application/json; charset=utf-8'):
  b=obj if isinstance(obj,bytes) else (json.dumps(obj).encode() if typ.startswith('application/json') else obj.encode());self.send_response(status);self.send_header('Content-Type',typ);self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def body(self):
  try:return json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))) or b'{}')
  except:return {}
 def me(self):
  try:uid=int(self.headers.get('X-User','0'))
  except:uid=0
  with con() as d:return d.execute('SELECT id,name,email,phone,role,status FROM users WHERE id=?',(uid,)).fetchone()
 def do_GET(self):
  p=urlparse(self.path).path
  if p=='/api/plans':self.out(200,PLANS);return
  if p=='/api/me':u=self.me();self.out(200,dict(u) if u else {});return
  u=self.me()
  if p in ('/api/policies','/api/claims','/api/agents','/api/customers','/api/applications','/api/alerts') and not u:self.out(401,{'error':'Please sign in first.'});return
  with con() as d:
   if p=='/api/policies':
    q='SELECT p.*,u.name customer_name FROM policies p JOIN users u ON p.user_id=u.id';rows=d.execute(q+' WHERE p.user_id=?',(u['id'],)).fetchall() if u['role']=='customer' else d.execute(q).fetchall();self.out(200,[dict(x) for x in rows]);return
   if p=='/api/claims':
    q='SELECT c.*,p.plan_name,u.name customer_name FROM claims c JOIN policies p ON c.policy_id=p.id JOIN users u ON c.user_id=u.id';rows=d.execute(q+' WHERE c.user_id=?' if u['role']=='customer' else q,(u['id'],) if u['role']=='customer' else ()).fetchall();self.out(200,[dict(x) for x in rows]);return
   if p=='/api/agents' and u['role']=='admin':self.out(200,[dict(x) for x in d.execute("SELECT id,name,email,phone,status,created_at FROM users WHERE role='agent' ORDER BY id DESC")]);return
   if p=='/api/customers' and u['role'] in ('agent','admin'):self.out(200,[dict(x) for x in d.execute("SELECT id,name,email,phone,created_at FROM users WHERE role='customer' ORDER BY id DESC")]);return
   if p=='/api/applications':
    q='SELECT a.*,u.name customer_name FROM applications a JOIN users u ON a.user_id=u.id';rows=d.execute(q+' WHERE a.user_id=?' if u['role']=='customer' else q,(u['id'],) if u['role']=='customer' else ()).fetchall();self.out(200,[dict(x) for x in rows]);return
   if p=='/api/alerts':
    q='SELECT a.*,p.plan_name FROM alerts a JOIN policies p ON a.policy_id=p.id';rows=d.execute(q+' WHERE a.user_id=? ORDER BY a.sent_at DESC' if u['role']=='customer' else q+' ORDER BY a.sent_at DESC',(u['id'],) if u['role']=='customer' else ()).fetchall();self.out(200,[dict(x) for x in rows]);return
  if p=='/':self.out(200,(ROOT/'index.html').read_bytes(),'text/html; charset=utf-8');return
  target=(ROOT/p.lstrip('/')).resolve()
  if target.parent!=ROOT or not target.exists():self.out(404,'Not found','text/plain');return
  typ='text/css; charset=utf-8' if target.suffix=='.css' else 'application/javascript; charset=utf-8' if target.suffix=='.js' else 'application/octet-stream';self.out(200,target.read_bytes(),typ)
 def do_POST(self):
  p=urlparse(self.path).path;x=self.body()
  if p in ('/api/register','/api/login'):
   with con() as d:
    if p.endswith('register'):
     name=str(x.get('name','')).strip()[:80];email=str(x.get('email','')).strip().lower()[:120];phone=str(x.get('phone','')).strip()[:32];role=x.get('role','customer');password=str(x.get('password',''))
     if not name or '@' not in email or len(password)<8 or role not in ('agent','customer'):self.out(400,{'error':'Enter your name, a valid email, and a password of at least 8 characters.'});return
     salt=secrets.token_hex(16);pw=hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),180000).hex();status='pending' if role=='agent' else 'approved'
     try:cur=d.execute('INSERT INTO users(name,email,phone,role,status,password_hash,salt) VALUES(?,?,?,?,?,?,?)',(name,email,phone,role,status,pw,salt))
     except sqlite3.IntegrityError:self.out(409,{'error':'An account already uses that email.'});return
     if role=='agent':self.out(201,{'id':cur.lastrowid,'name':name,'role':role,'status':status});return
     self.out(201,{'id':cur.lastrowid,'name':name,'role':role,'status':status});return
    email=str(x.get('email','')).lower().strip();pw=str(x.get('password',''));u=d.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
    if not u or not secrets.compare_digest(hashlib.pbkdf2_hmac('sha256',pw.encode(),u['salt'].encode(),180000).hex(),u['password_hash']):self.out(401,{'error':'Email or password does not match.'});return
    if u['status']=='pending':self.out(403,{'error':'Agent access is waiting for administrator approval.'});return
    self.out(200,{'id':u['id'],'name':u['name'],'email':u['email'],'role':u['role'],'status':u['status']});return
  u=self.me()
  if not u:self.out(401,{'error':'Please sign in first.'});return
  with con() as d:
   if p=='/api/applications':
    pid=int(x.get('plan_id',0));plan=next((z for z in PLANS if z['id']==pid),None)
    if not plan:self.out(400,{'error':'Choose a valid policy.'});return
    d.execute('INSERT INTO applications(user_id,plan_id) VALUES(?,?)',(u['id'],pid));self.out(201,{'ok':True,'message':'Application received. An agent will follow up.'});return
   if p=='/api/policies' and u['role'] in ('agent','admin'):
    email=str(x.get('email','')).lower().strip();c=d.execute("SELECT * FROM users WHERE email=? AND role='customer'",(email,)).fetchone();plan=next((z for z in PLANS if z['id']==int(x.get('plan_id',0))),None)
    if not c or not plan:self.out(400,{'error':'Enter a registered customer email and choose a valid policy.'});return
    d.execute('INSERT INTO policies(user_id,plan_id,kind,plan_name,premium,cover,due_date) VALUES(?,?,?,?,?,?,?)',(c['id'],plan['id'],plan['kind'],plan['name'],plan['price'],'%.2f'%plan['cover'],str(x.get('due_date','2026-12-17'))));self.out(201,{'ok':True});return
   if p=='/api/claims':
    pid=int(x.get('policy_id',0));pol=d.execute('SELECT * FROM policies WHERE id=? AND user_id=?',(pid,u['id'])).fetchone()
    if not pol:self.out(400,{'error':'Choose one of your active policies.'});return
    details=str(x.get('details','')).strip()[:1000]
    if len(details)<8:self.out(400,{'error':'Please add a few details about the claim.'});return
    d.execute('INSERT INTO claims(user_id,policy_id,details) VALUES(?,?,?)',(u['id'],pid,details));self.out(201,{'ok':True});return
   if p=='/api/payments':
    pid=int(x.get('policy_id',0));pol=d.execute('SELECT * FROM policies WHERE id=? AND user_id=?',(pid,u['id'])).fetchone()
    if not pol:self.out(400,{'error':'Choose one of your active policies.'});return
    d.execute('INSERT INTO payments(user_id,policy_id,amount) VALUES(?,?,?)',(u['id'],pid,pol['premium']));self.out(201,{'ok':True,'message':'Demo payment recorded successfully.'});return
   if p=='/api/alerts' and u['role'] in ('agent','admin'):
    pid=int(x.get('policy_id',0));pol=d.execute('SELECT * FROM policies WHERE id=?',(pid,)).fetchone()
    if not pol:self.out(400,{'error':'Choose a valid policy.'});return
    msg=f"InsureEasy reminder: {pol['plan_name']} premium of ₹{pol['premium']} is due on {pol['due_date']}. This is a demo SMS log.";d.execute('INSERT INTO alerts(user_id,policy_id,message) VALUES(?,?,?)',(pol['user_id'],pid,msg));self.out(201,{'ok':True,'message':'Reminder added to the SMS demo log. Connect an SMS gateway to deliver messages.'});return
   if p.startswith('/api/agents/') and p.endswith('/approve') and u['role']=='admin':
    uid=int(p.split('/')[-2]);cur=d.execute("UPDATE users SET status='approved' WHERE id=? AND role='agent'",(uid,));self.out(200,{'ok':cur.rowcount>0});return
   if p=='/api/agents/create-customer' and u['role']=='agent':
    name=str(x.get('name','')).strip()[:80];email=str(x.get('email','')).strip().lower()[:120];phone=str(x.get('phone','')).strip()[:32];password=str(x.get('password','Customer123!'))
    if not name or '@' not in email:self.out(400,{'error':'Enter a customer name and valid email.'});return
    salt=secrets.token_hex(16);h=hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),180000).hex()
    try:d.execute("INSERT INTO users(name,email,phone,role,status,password_hash,salt) VALUES(?,?,?,'customer','approved',?,?)",(name,email,phone,h,salt))
    except sqlite3.IntegrityError:self.out(409,{'error':'An account already uses that email.'});return
    self.out(201,{'ok':True});return
  self.out(404,{'error':'Not found'})
 def do_PUT(self):
  p=urlparse(self.path).path;x=self.body();u=self.me()
  if not u or u['role']!='admin':self.out(403,{'error':'Administrator access required.'});return
  if p.startswith('/api/claims/'):
   status=x.get('status','Under review')
   if status not in ('Under review','Approved','Closed'):self.out(400,{'error':'Invalid status'});return
   with con() as d:d.execute('UPDATE claims SET status=? WHERE id=?',(status,int(p.split('/')[-1])))
   self.out(200,{'ok':True});return
  self.out(404,{'error':'Not found'})
if __name__=='__main__':
 init();print(f'InsureEasy is running at http://localhost:{PORT}');ThreadingHTTPServer(('127.0.0.1',PORT),H).serve_forever()
