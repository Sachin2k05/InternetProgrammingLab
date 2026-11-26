"""EasyToll local classroom demo. Start with: python server.py"""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from datetime import date,timedelta
import hashlib,json,secrets,sqlite3

ROOT=Path(__file__).resolve().parent; DB=ROOT/'easytoll.db'; PORT=8004
def con():
 d=sqlite3.connect(DB);d.row_factory=sqlite3.Row;d.execute('PRAGMA foreign_keys=ON');return d
def pwd(text,salt):return hashlib.pbkdf2_hmac('sha256',text.encode(),salt.encode(),180000).hex()
def init():
 with con() as d:
  d.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,phone TEXT DEFAULT '',role TEXT NOT NULL DEFAULT 'driver',status TEXT DEFAULT 'approved',password_hash TEXT NOT NULL,salt TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS tolls(id INTEGER PRIMARY KEY,name TEXT NOT NULL,location TEXT NOT NULL,region TEXT NOT NULL,rate REAL NOT NULL,active INTEGER DEFAULT 1,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS vehicles(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,plate TEXT UNIQUE NOT NULL,make TEXT DEFAULT '',model TEXT DEFAULT '',kind TEXT DEFAULT 'Car',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS wallet(user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,balance REAL DEFAULT 0);
  CREATE TABLE IF NOT EXISTS ledger(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),kind TEXT NOT NULL,amount REAL NOT NULL,description TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS passes(id INTEGER PRIMARY KEY,pass_code TEXT UNIQUE NOT NULL,user_id INTEGER NOT NULL REFERENCES users(id),vehicle_id INTEGER NOT NULL REFERENCES vehicles(id),toll_id INTEGER REFERENCES tolls(id),pass_type TEXT NOT NULL,status TEXT DEFAULT 'Pending',valid_until TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS tickets(id INTEGER PRIMARY KEY,ticket_code TEXT UNIQUE NOT NULL,user_id INTEGER NOT NULL REFERENCES users(id),vehicle_id INTEGER NOT NULL REFERENCES vehicles(id),toll_id INTEGER NOT NULL REFERENCES tolls(id),price REAL NOT NULL,status TEXT DEFAULT 'Ready',travel_date TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS gates(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id),name TEXT NOT NULL,location TEXT NOT NULL,region TEXT NOT NULL,status TEXT DEFAULT 'Pending',updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS transactions(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),kind TEXT NOT NULL,amount REAL NOT NULL,reference TEXT DEFAULT '',description TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS recurring(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,vehicle_id INTEGER NOT NULL REFERENCES vehicles(id),from_region TEXT NOT NULL,to_region TEXT NOT NULL,enabled INTEGER DEFAULT 1,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,message TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);''')
  for row in [('Riverbend Toll Plaza','Highway 8, near Salem','Oregon',5.5),('Cedar Pass Toll Gate','I-80, Summit County','Colorado',8.25),('Lakeside Express Toll','Route 41, Lake County','Illinois',4.75),('Golden Gate Connector','Bay Bridge approach','California',7.0)]:d.execute('INSERT OR IGNORE INTO tolls(name,location,region,rate) SELECT ?,?,?,? WHERE NOT EXISTS(SELECT 1 FROM tolls WHERE name=?)',(*row,row[0]))
  if not d.execute("SELECT 1 FROM users WHERE email='admin@easytoll.test'").fetchone():
   salt=secrets.token_hex(16);d.execute("INSERT INTO users(name,email,role,status,password_hash,salt) VALUES('EasyToll Admin','admin@easytoll.test','admin','approved',?,?)",(pwd('toll12345',salt),salt))
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
  p=urlparse(self.path).path;u=self.me()
  if p=='/api/me':self.out(200,dict(u) if u else {});return
  if p=='/api/tolls':
   with con() as d:self.out(200,[dict(x) for x in d.execute('SELECT * FROM tolls WHERE active=1 ORDER BY region,name')]);return
  if p in ('/api/vehicles','/api/passes','/api/tickets','/api/transactions','/api/notifications','/api/recurring','/api/gates','/api/users','/api/wallet') and not u:self.out(401,{'error':'Sign in to continue.'});return
  if p=='/api/wallet':
   with con() as d:d.execute('INSERT OR IGNORE INTO wallet(user_id,balance) VALUES(?,0)',(u['id'],));w=d.execute('SELECT balance FROM wallet WHERE user_id=?',(u['id'],)).fetchone();self.out(200,{'balance':w['balance']});return
  if p=='/api/vehicles':
   with con() as d:rows=d.execute('SELECT * FROM vehicles WHERE user_id=? ORDER BY id DESC',(u['id'],)).fetchall();self.out(200,[dict(x) for x in rows]);return
  if p=='/api/passes':
   if u['role'] not in ('driver','admin'):self.out(403,{'error':'Driver or administrator access required.'});return
   with con() as d:q='SELECT p.*,v.plate,t.name toll_name FROM passes p JOIN vehicles v ON v.id=p.vehicle_id LEFT JOIN tolls t ON t.id=p.toll_id';rows=d.execute(q+' WHERE p.user_id=? ORDER BY p.id DESC',(u['id'],)).fetchall() if u['role']=='driver' else d.execute(q+' ORDER BY p.id DESC').fetchall();self.out(200,[dict(x) for x in rows]);return
  if p=='/api/tickets':
   if u['role'] not in ('driver','admin'):self.out(403,{'error':'Driver or administrator access required.'});return
   with con() as d:q='SELECT k.*,v.plate,t.name toll_name FROM tickets k JOIN vehicles v ON v.id=k.vehicle_id JOIN tolls t ON t.id=k.toll_id';rows=d.execute(q+' WHERE k.user_id=? ORDER BY k.id DESC',(u['id'],)).fetchall() if u['role']=='driver' else d.execute(q+' ORDER BY k.id DESC').fetchall();self.out(200,[dict(x) for x in rows]);return
  if p=='/api/transactions':
   if u['role'] not in ('driver','admin'):self.out(403,{'error':'Driver or administrator access required.'});return
   with con() as d:q='SELECT * FROM transactions';rows=d.execute(q+' WHERE user_id=? ORDER BY id DESC',(u['id'],)).fetchall() if u['role']=='driver' else d.execute(q+' ORDER BY id DESC').fetchall();self.out(200,[dict(x) for x in rows]);return
  if p=='/api/notifications':
   with con() as d:self.out(200,[dict(x) for x in d.execute('SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 25',(u['id'],))]);return
  if p=='/api/recurring':
   if u['role'] not in ('driver','admin'):self.out(403,{'error':'Driver or administrator access required.'});return
   with con() as d:q='SELECT r.*,v.plate FROM recurring r JOIN vehicles v ON v.id=r.vehicle_id';rows=d.execute(q+' WHERE r.user_id=?',(u['id'],)).fetchall() if u['role']=='driver' else d.execute(q).fetchall();self.out(200,[dict(x) for x in rows]);return
  if p=='/api/gates':
   with con() as d:
    q='SELECT g.*,u.name operator,u.email FROM gates g LEFT JOIN users u ON u.id=g.user_id';rows=d.execute(q+' WHERE g.user_id=?',(u['id'],)).fetchall() if u['role']=='gate' else d.execute(q).fetchall();self.out(200,[dict(x) for x in rows]);return
  if p=='/api/users':
   if u['role']!='admin':self.out(403,{'error':'Administrator access required.'});return
   with con() as d:self.out(200,[dict(x) for x in d.execute('SELECT id,name,email,phone,role,status,created_at FROM users ORDER BY id DESC')]);return
  if p=='/':self.out(200,(ROOT/'index.html').read_bytes(),'text/html; charset=utf-8');return
  target=(ROOT/p.lstrip('/')).resolve()
  if target.parent!=ROOT or not target.exists():self.out(404,'Not found','text/plain');return
  typ='text/css; charset=utf-8' if target.suffix=='.css' else 'application/javascript; charset=utf-8' if target.suffix=='.js' else 'application/octet-stream';self.out(200,target.read_bytes(),typ)
 def do_POST(self):
  p=urlparse(self.path).path;x=self.body()
  if p in ('/api/register','/api/login'):
   with con() as d:
    if p.endswith('register'):
     name=str(x.get('name','')).strip()[:80];email=str(x.get('email','')).strip().lower()[:120];phone=str(x.get('phone','')).strip()[:32];pw=str(x.get('password',''));role=x.get('role','driver')
     if not name or '@' not in email or len(pw)<8 or role not in ('driver','gate'):self.out(400,{'error':'Enter a name, valid email, 8+ character password, and account type.'});return
     salt=secrets.token_hex(16);status='pending' if role=='gate' else 'approved'
     try:cur=d.execute('INSERT INTO users(name,email,phone,role,status,password_hash,salt) VALUES(?,?,?,?,?,?,?)',(name,email,phone,role,status,pwd(pw,salt),salt));uid=cur.lastrowid
     except sqlite3.IntegrityError:self.out(409,{'error':'That email already has an account.'});return
     if role=='driver':d.execute('INSERT INTO wallet(user_id,balance) VALUES(?,0)',(uid,))
     self.out(201,{'id':uid,'name':name,'email':email,'phone':phone,'role':role,'status':status});return
    row=d.execute('SELECT * FROM users WHERE email=?',(str(x.get('email','')).lower().strip(),)).fetchone();password=str(x.get('password',''))
    if not row or not secrets.compare_digest(pwd(password,row['salt']),row['password_hash']):self.out(401,{'error':'Email or password did not match.'});return
    if row['status']=='pending':self.out(403,{'error':'Toll-gate access is waiting for administrator approval.'});return
    if row['role']=='driver':d.execute('INSERT OR IGNORE INTO wallet(user_id,balance) VALUES(?,0)',(row['id'],))
    self.out(200,{k:row[k] for k in ('id','name','email','phone','role','status')});return
  u=self.me()
  if not u:self.out(401,{'error':'Sign in first.'});return
  with con() as d:
   if p=='/api/vehicles' and u['role']=='driver':
    plate=str(x.get('plate','')).strip().upper()[:16];make=str(x.get('make','')).strip()[:40];model=str(x.get('model','')).strip()[:40];kind=str(x.get('kind','Car'))
    if not plate:self.out(400,{'error':'Enter a license plate.'});return
    try:cur=d.execute('INSERT INTO vehicles(user_id,plate,make,model,kind) VALUES(?,?,?,?,?)',(u['id'],plate,make,model,kind))
    except sqlite3.IntegrityError:self.out(409,{'error':'That vehicle plate is already registered.'});return
    self.out(201,{'id':cur.lastrowid});return
   if p=='/api/wallet/topup' and u['role']=='driver':
    try:amount=round(float(x.get('amount',0)),2)
    except:amount=0
    if amount<5 or amount>5000:self.out(400,{'error':'Choose a demo top-up between $5 and $5,000.'});return
    d.execute('INSERT OR IGNORE INTO wallet(user_id,balance) VALUES(?,0)',(u['id'],));d.execute('UPDATE wallet SET balance=balance+? WHERE user_id=?',(amount,u['id']));d.execute('INSERT INTO ledger(user_id,kind,amount,description) VALUES(?,?,?,?)',(u['id'],'Top-up',amount,'Demo wallet top-up'));d.execute('INSERT INTO transactions(user_id,kind,amount,description) VALUES(?,?,?,?)',(u['id'],'Wallet top-up',amount,'Demo wallet credit'));self.out(201,{'ok':True,'balance':d.execute('SELECT balance FROM wallet WHERE user_id=?',(u['id'],)).fetchone()['balance']});return
   if p=='/api/passes/apply' and u['role']=='driver':
    vid=int(x.get('vehicle_id',0));tid=int(x.get('toll_id',0));kind=str(x.get('pass_type','Monthly'))
    if kind not in ('Monthly','Annual'):kind='Monthly'
    if not d.execute('SELECT 1 FROM vehicles WHERE id=? AND user_id=?',(vid,u['id'])).fetchone():self.out(400,{'error':'Choose one of your vehicles.'});return
    code='PASS-'+secrets.token_hex(4).upper();d.execute('INSERT INTO passes(pass_code,user_id,vehicle_id,toll_id,pass_type) VALUES(?,?,?,?,?)',(code,u['id'],vid,tid or None,kind));d.execute('INSERT INTO notifications(user_id,message) VALUES(?,?)',(u['id'],f'{kind} toll pass request {code} is waiting for approval.'));self.out(201,{'ok':True,'code':code});return
   if p=='/api/tickets/buy' and u['role']=='driver':
    vid=int(x.get('vehicle_id',0));tid=int(x.get('toll_id',0));travel=str(x.get('travel_date',''))
    if not travel or travel<date.today().isoformat():self.out(400,{'error':'Choose today or a future travel date.'});return
    toll=d.execute('SELECT * FROM tolls WHERE id=? AND active=1',(tid,)).fetchone()
    if not toll or not d.execute('SELECT 1 FROM vehicles WHERE id=? AND user_id=?',(vid,u['id'])).fetchone():self.out(400,{'error':'Choose your vehicle and a valid toll gate.'});return
    d.execute('INSERT OR IGNORE INTO wallet(user_id,balance) VALUES(?,0)',(u['id'],));w=d.execute('SELECT balance FROM wallet WHERE user_id=?',(u['id'],)).fetchone()['balance']
    if w<toll['rate']:self.out(400,{'error':f'Wallet balance is {w:.2f}. Add money to cover this {toll["rate"]:.2f} toll.'});return
    code='TKT-'+secrets.token_hex(4).upper();d.execute('UPDATE wallet SET balance=balance-? WHERE user_id=?',(toll['rate'],u['id']));d.execute('INSERT INTO tickets(ticket_code,user_id,vehicle_id,toll_id,price,travel_date) VALUES(?,?,?,?,?,?)',(code,u['id'],vid,tid,toll['rate'],travel));d.execute('INSERT INTO transactions(user_id,kind,amount,reference,description) VALUES(?,?,?,?,?)',(u['id'],'Advance toll ticket',-toll['rate'],code,f'Prepaid travel at {toll["name"]}'));self.out(201,{'ok':True,'code':code,'price':toll['rate']});return
   if p=='/api/recurring' and u['role']=='driver':
    vid=int(x.get('vehicle_id',0));a=str(x.get('from_region','')).strip()[:60];b=str(x.get('to_region','')).strip()[:60]
    if not d.execute('SELECT 1 FROM vehicles WHERE id=? AND user_id=?',(vid,u['id'])).fetchone() or not a or not b:self.out(400,{'error':'Add your vehicle and choose a route.'});return
    d.execute('INSERT INTO recurring(user_id,vehicle_id,from_region,to_region) VALUES(?,?,?,?)',(u['id'],vid,a,b));self.out(201,{'ok':True});return
   if p=='/api/gates/register':
    if u['role'] not in ('admin','gate'):self.out(403,{'error':'Toll-gate account required.'});return
    name=str(x.get('name','')).strip()[:80];loc=str(x.get('location','')).strip()[:120];region=str(x.get('region','')).strip()[:60]
    if not name or not loc or not region:self.out(400,{'error':'Enter gate name, location, and region.'});return
    d.execute('INSERT INTO gates(user_id,name,location,region,status) VALUES(?,?,?,?,?)',(u['id'],name,loc,region,'Approved' if u['role']=='admin' else 'Pending'));self.out(201,{'ok':True});return
   if p=='/api/verify' and u['role'] in ('gate','admin'):
    code=str(x.get('code','')).strip().upper();gate_id=int(x.get('gate_id',0))
    gate=d.execute('SELECT * FROM gates WHERE id=? AND status="Approved"',(gate_id,)).fetchone()
    if not gate or (u['role']=='gate' and gate['user_id']!=u['id']):self.out(403,{'valid':False,'error':'Your gate login is not approved for this location.'});return
    ticket=d.execute('SELECT k.*,v.plate,t.name toll_name,t.region toll_region FROM tickets k JOIN vehicles v ON v.id=k.vehicle_id JOIN tolls t ON t.id=k.toll_id WHERE k.ticket_code=?',(code,)).fetchone()
    if ticket:
     if ticket['status']!='Ready':self.out(200,{'valid':False,'type':'ticket','error':'This ticket has already been used.'});return
     if ticket['toll_region'].lower()!=gate['region'].lower():self.out(200,{'valid':False,'type':'ticket','error':f'This ticket is for {ticket["toll_name"]} in {ticket["toll_region"]}.'});return
     d.execute('UPDATE tickets SET status="Used" WHERE id=?',(ticket['id'],));d.execute('INSERT INTO transactions(user_id,kind,amount,reference,description) VALUES(?,?,?,?,?)',(ticket['user_id'],'Toll passage',0,code,f'Verified at {gate["name"]}'));self.out(200,{'valid':True,'type':'ticket','plate':ticket['plate'],'gate':gate['name'],'message':'Ticket valid. Passage recorded.'});return
    passrow=d.execute('SELECT p.*,v.plate FROM passes p JOIN vehicles v ON v.id=p.vehicle_id WHERE p.pass_code=?',(code,)).fetchone()
    if passrow and passrow['status']=='Approved' and passrow['valid_until'] and passrow['valid_until']>=date.today().isoformat() and (not passrow['toll_id'] or d.execute('SELECT region FROM tolls WHERE id=?',(passrow['toll_id'],)).fetchone()['region'].lower()==gate['region'].lower()):self.out(200,{'valid':True,'type':'pass','plate':passrow['plate'],'gate':gate['name'],'message':'Toll pass approved and valid.'});return
    self.out(200,{'valid':False,'error':'Pass or eTicket ID was not found, approved, or valid.'});return
   if p=='/api/tolls' and u['role']=='admin':
    name=str(x.get('name','')).strip();loc=str(x.get('location','')).strip();region=str(x.get('region','')).strip()
    try:rate=round(float(x.get('rate',0)),2)
    except:rate=0
    if not name or not loc or not region or rate<=0:self.out(400,{'error':'Enter gate name, location, region, and a positive toll rate.'});return
    d.execute('INSERT INTO tolls(name,location,region,rate) VALUES(?,?,?,?)',(name,loc,region,rate));self.out(201,{'ok':True});return
   if p=='/api/admin/approve-pass' and u['role']=='admin':
    pid=int(x.get('pass_id',0));row=d.execute('SELECT * FROM passes WHERE id=? AND status="Pending"',(pid,)).fetchone()
    if not row:self.out(404,{'error':'Pending pass request not found.'});return
    fee=40 if row['pass_type']=='Monthly' else 400;d.execute('INSERT OR IGNORE INTO wallet(user_id,balance) VALUES(?,0)',(row['user_id'],));w=d.execute('SELECT balance FROM wallet WHERE user_id=?',(row['user_id'],)).fetchone()['balance']
    if w<fee:self.out(400,{'error':f'Driver needs {fee:.2f} wallet balance before approval.'});return
    until=(date.today()+timedelta(days=30 if row['pass_type']=='Monthly' else 365)).isoformat();d.execute('UPDATE wallet SET balance=balance-? WHERE user_id=?',(fee,row['user_id']));d.execute('UPDATE passes SET status="Approved",valid_until=? WHERE id=?',(until,pid));d.execute('INSERT INTO transactions(user_id,kind,amount,reference,description) VALUES(?,?,?,?,?)',(row['user_id'],'Toll pass',-fee,row['pass_code'],f'{row["pass_type"]} toll pass approved'));d.execute('INSERT INTO notifications(user_id,message) VALUES(?,?)',(row['user_id'],f'Toll pass {row["pass_code"]} approved until {until}.'));self.out(200,{'ok':True});return
   if p=='/api/admin/users' and u['role']=='admin':
    name=str(x.get('name','')).strip()[:80];email=str(x.get('email','')).strip().lower()[:120];phone=str(x.get('phone','')).strip()[:32];role=x.get('role','driver');password=str(x.get('password',''))
    if not name or '@' not in email or role not in ('driver','gate','admin') or len(password)<8:self.out(400,{'error':'Enter a name, valid email, 8+ character password, and account role.'});return
    salt=secrets.token_hex(16)
    try:cur=d.execute('INSERT INTO users(name,email,phone,role,status,password_hash,salt) VALUES(?,?,?,?,?,?,?)',(name,email,phone,role,'approved' if role!='gate' else 'pending',pwd(password,salt),salt))
    except sqlite3.IntegrityError:self.out(409,{'error':'That email already has an account.'});return
    if role=='driver':d.execute('INSERT INTO wallet(user_id,balance) VALUES(?,0)',(cur.lastrowid,))
    self.out(201,{'ok':True});return
   self.out(404,{'error':'Not found'})
 def do_PUT(self):
  p=urlparse(self.path).path;x=self.body();u=self.me()
  if p.startswith('/api/gates/') and u and u['role']=='gate':
   gid=int(p.rsplit('/',1)[-1]);loc=str(x.get('location','')).strip()[:120];region=str(x.get('region','')).strip()[:60]
   with con() as d:
    g=d.execute('SELECT * FROM gates WHERE id=? AND user_id=? AND status="Approved"',(gid,u['id'])).fetchone()
    if not g:self.out(403,{'error':'You are not approved for this toll location.'});return
    d.execute('UPDATE gates SET location=?,region=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(loc or g['location'],region or g['region'],gid))
   self.out(200,{'ok':True});return
  if not u or u['role']!='admin':self.out(403,{'error':'Administrator access required.'});return
  with con() as d:
   if p.startswith('/api/users/'):
    uid=int(p.rsplit('/',1)[-1]);fields=[];vals=[]
    if 'role' in x and x['role'] not in ('driver','gate','admin'):self.out(400,{'error':'Invalid account role.'});return
    if 'status' in x and x['status'] not in ('approved','pending'):self.out(400,{'error':'Invalid account status.'});return
    if x.get('password') and len(str(x['password']))<8:self.out(400,{'error':'New passwords need at least 8 characters.'});return
    for k in ('name','email','phone','role','status'):
     if k in x:fields.append(k+'=?');vals.append(str(x[k]))
    if 'password' in x and len(str(x['password']))>=8:salt=secrets.token_hex(16);fields+=['salt=?','password_hash=?'];vals += [salt,pwd(str(x['password']),salt)]
    if not fields:self.out(400,{'error':'No user changes provided.'});return
    vals.append(uid);d.execute('UPDATE users SET '+','.join(fields)+' WHERE id=?',vals);self.out(200,{'ok':True});return
   if p.startswith('/api/gates/'):
    gid=int(p.rsplit('/',1)[-1]);fields=[];vals=[]
    for k in ('name','location','region','status'):
     if k in x:fields.append(k+'=?');vals.append(str(x[k]))
    fields.append('updated_at=CURRENT_TIMESTAMP');vals.append(gid);d.execute('UPDATE gates SET '+','.join(fields)+' WHERE id=?',vals);self.out(200,{'ok':True});return
  self.out(404,{'error':'Not found'})
 def do_DELETE(self):
  p=urlparse(self.path).path;u=self.me()
  if not u or u['role']!='admin':self.out(403,{'error':'Administrator access required.'});return
  with con() as d:
   if p.startswith('/api/tolls/'):
    d.execute('UPDATE tolls SET active=0 WHERE id=?',(int(p.rsplit('/',1)[-1]),));self.out(200,{'ok':True});return
   if p.startswith('/api/users/'):
    uid=int(p.rsplit('/',1)[-1])
    if uid==u['id']:self.out(400,{'error':'You cannot delete the admin account currently in use.'});return
    d.execute('DELETE FROM passes WHERE user_id=?',(uid,));d.execute('DELETE FROM tickets WHERE user_id=?',(uid,));d.execute('DELETE FROM transactions WHERE user_id=?',(uid,));d.execute('DELETE FROM ledger WHERE user_id=?',(uid,));d.execute('DELETE FROM recurring WHERE user_id=?',(uid,));d.execute('DELETE FROM notifications WHERE user_id=?',(uid,));d.execute('UPDATE gates SET user_id=NULL WHERE user_id=?',(uid,));d.execute('DELETE FROM vehicles WHERE user_id=?',(uid,));d.execute('DELETE FROM users WHERE id=?',(uid,));self.out(200,{'ok':True});return
  self.out(404,{'error':'Not found'})
if __name__=='__main__':
 init();print(f'EasyToll is running at http://localhost:{PORT}');ThreadingHTTPServer(('127.0.0.1',PORT),H).serve_forever()
