"""ComplainEase local classroom server. Run with: python server.py"""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import base64,hashlib,json,secrets,sqlite3

ROOT=Path(__file__).resolve().parent;DB=ROOT/'complainease.db';PORT=8005
DEFAULTS={
 'contact_email':'help@complainease.example','contact_phone':'1-800-555-0144',
 'citizen_registration':'true','officer_registration':'true',
 'citizen_submit':'true','citizen_map':'true','citizen_tracking':'true','citizen_search':'true','citizen_feedback':'true',
 'officer_proof':'true','officer_search':'true','site_message':'We’re here to help. Every concern deserves a thoughtful response.'
}
CATEGORIES=[('Roads & sidewalks','⌁'),('Waste & sanitation','♻'),('Water services','◌'),('Street lighting','☼'),('Public safety','♡'),('Parks & public spaces','✳'),('Other concern','＋')]
FAQ=[{'q':'How do I track a complaint?','a':'Sign in and open My complaints. Each complaint has a reference number, status updates, and notes from the resolution team.'},{'q':'Can I add more information later?','a':'Yes. Open a submitted complaint and use Add information to share a new note or upload supporting evidence.'},{'q':'What happens after I submit?','a':'The complaint is recorded and appears in the officer work queue. You’ll see status changes here; email or SMS delivery requires a connected messaging service.'},{'q':'How do I share the location?','a':'Search for a place or click on the map to pin the location. You can also type an address or landmark.'}]
def con():
 d=sqlite3.connect(DB);d.row_factory=sqlite3.Row;d.execute('PRAGMA foreign_keys=ON');return d
def phash(p,s):return hashlib.pbkdf2_hmac('sha256',p.encode(),s.encode(),180000).hex()
def init():
 with con() as d:
  d.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,phone TEXT DEFAULT '',role TEXT NOT NULL DEFAULT 'citizen',status TEXT DEFAULT 'approved',password_hash TEXT NOT NULL,salt TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY,name TEXT UNIQUE NOT NULL,icon TEXT DEFAULT '＋',active INTEGER DEFAULT 1);
  CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS complaints(id INTEGER PRIMARY KEY,reference TEXT UNIQUE NOT NULL,citizen_id INTEGER NOT NULL REFERENCES users(id),officer_id INTEGER REFERENCES users(id) ON DELETE SET NULL,category TEXT NOT NULL,title TEXT NOT NULL,description TEXT NOT NULL,location TEXT NOT NULL,latitude REAL,longitude REAL,status TEXT DEFAULT 'Submitted',created_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS attachments(id INTEGER PRIMARY KEY,complaint_id INTEGER NOT NULL REFERENCES complaints(id) ON DELETE CASCADE,uploader_id INTEGER NOT NULL REFERENCES users(id),kind TEXT NOT NULL,filename TEXT NOT NULL,mime TEXT NOT NULL,data BLOB NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS updates(id INTEGER PRIMARY KEY,complaint_id INTEGER NOT NULL REFERENCES complaints(id) ON DELETE CASCADE,user_id INTEGER NOT NULL REFERENCES users(id),status TEXT NOT NULL,note TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY,complaint_id INTEGER NOT NULL UNIQUE REFERENCES complaints(id) ON DELETE CASCADE,citizen_id INTEGER NOT NULL REFERENCES users(id),rating INTEGER NOT NULL,comment TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,message TEXT NOT NULL,channel TEXT DEFAULT 'In-app demo',created_at TEXT DEFAULT CURRENT_TIMESTAMP);''')
  for name,icon in CATEGORIES:d.execute('INSERT OR IGNORE INTO categories(name,icon) VALUES(?,?)',(name,icon))
  for k,v in DEFAULTS.items():d.execute('INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)',(k,v))
  if not d.execute("SELECT id FROM users WHERE email='admin@complainease.test'").fetchone():
   salt=secrets.token_hex(16);d.execute("INSERT INTO users(name,email,phone,role,status,password_hash,salt) VALUES('ComplainEase Admin','admin@complainease.test','1-800-555-0144','admin','approved',?,?)",(phash('resolve12345',salt),salt))
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def send(self,s,x,typ='application/json; charset=utf-8',headers=None):
  b=x if isinstance(x,bytes) else (json.dumps(x).encode() if typ.startswith('application/json') else x.encode());self.send_response(s);self.send_header('Content-Type',typ);self.send_header('Content-Length',str(len(b)))
  for k,v in (headers or {}).items():self.send_header(k,v)
  self.end_headers();self.wfile.write(b)
 def body(self):
  try:return json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))) or b'{}')
  except:return {}
 def me(self):
  try:uid=int(self.headers.get('X-User','0'))
  except:uid=0
  with con() as d:return d.execute('SELECT id,name,email,phone,role,status FROM users WHERE id=?',(uid,)).fetchone()
 def allowed(self,roles=None):
  u=self.me()
  return u if u and u['status']=='approved' and (not roles or u['role'] in roles) else None
 def settings(self):
  with con() as d:return {r['key']:r['value'] for r in d.execute('SELECT key,value FROM settings')}
 def save_files(self,d,cid,uid,kind,files):
  if not isinstance(files,list):return 'Files need to be sent as a list.'
  prepared=[]
  for f in files[:5]:
   try:
    name=Path(str(f.get('name','upload'))).name[:120];mime=str(f.get('type','application/octet-stream'))[:100];raw=base64.b64decode(f.get('data',''),validate=True)
   except Exception:return 'A file could not be read.'
   if len(raw)>4*1024*1024:return 'Each upload must be under 4 MB.'
   if mime not in ('image/jpeg','image/png','image/webp','application/pdf','text/plain'):return 'Upload a JPG, PNG, WEBP, PDF, or plain text file.'
   prepared.append((cid,uid,kind,name,mime,raw))
  for row in prepared:d.execute('INSERT INTO attachments(complaint_id,uploader_id,kind,filename,mime,data) VALUES(?,?,?,?,?,?)',row)
  return None
 def do_GET(self):
  p=urlparse(self.path).path;u=self.me()
  if p=='/':self.send(200,(ROOT/'index.html').read_bytes(),'text/html; charset=utf-8');return
  if p in ('/styles.css','/script.js'):
   f=ROOT/p.lstrip('/');self.send(200,f.read_bytes(),'text/css; charset=utf-8' if f.suffix=='.css' else 'application/javascript; charset=utf-8');return
  if p=='/api/settings':
   s=self.settings();self.send(200,{k:v for k,v in s.items() if k!='site_message'}|{'site_message':s.get('site_message','')});return
  if p=='/api/categories':
   with con() as d:self.send(200,[dict(x) for x in d.execute('SELECT * FROM categories WHERE active=1 ORDER BY id')]);return
  if p=='/api/faq':self.send(200,FAQ);return
  if p=='/api/me':self.send(200,dict(u) if u and u['status']=='approved' else {});return
  if p.startswith('/api/files/'):
   aid=int(p.rsplit('/',1)[-1]);u=self.allowed()
   if not u:self.send(401,{'error':'Sign in to view this file.'});return
   with con() as d:
    row=d.execute('SELECT a.*,c.citizen_id,c.officer_id FROM attachments a JOIN complaints c ON c.id=a.complaint_id WHERE a.id=?',(aid,)).fetchone()
    if not row:self.send(404,{'error':'File not found.'});return
    if u['role']=='citizen' and row['citizen_id']!=u['id'] or u['role']=='officer' and row['officer_id'] not in (None,u['id']) or row['mime'] not in ('image/jpeg','image/png','image/webp','application/pdf','text/plain'):self.send(403,{'error':'You cannot access this file.'});return
    filename=Path(row['filename']).name.replace('"','')
    self.send(200,bytes(row['data']),row['mime'],{'Content-Disposition':f'inline; filename="{filename}"','X-Content-Type-Options':'nosniff'});return
  if p in ('/api/complaints','/api/officers','/api/notifications','/api/users') and not self.allowed():self.send(401,{'error':'Sign in to continue.'});return
  if p.startswith('/api/complaints/') and not self.allowed():self.send(401,{'error':'Sign in to continue.'});return
  u=self.allowed() if u and u['status']=='approved' else None
  if p=='/api/complaints':
   with con() as d:
    q='SELECT c.*,u.name citizen_name,u.email citizen_email,o.name officer_name FROM complaints c JOIN users u ON u.id=c.citizen_id LEFT JOIN users o ON o.id=c.officer_id'
    if u['role']=='citizen':rows=d.execute(q+' WHERE c.citizen_id=? ORDER BY c.id DESC',(u['id'],)).fetchall()
    elif u['role']=='officer':rows=d.execute(q+' WHERE c.officer_id=? OR c.officer_id IS NULL ORDER BY c.id DESC',(u['id'],)).fetchall()
    else:rows=d.execute(q+' ORDER BY c.id DESC').fetchall()
    results=[]
    for r in rows:
     x=dict(r);x['attachments']=[dict(a) for a in d.execute('SELECT id,kind,filename,mime,created_at FROM attachments WHERE complaint_id=? ORDER BY id',(r['id'],))];x['updates']=[dict(a) for a in d.execute('SELECT x.*,u.name author FROM updates x JOIN users u ON u.id=x.user_id WHERE x.complaint_id=? ORDER BY x.id',(r['id'],))];f=d.execute('SELECT rating,comment,created_at FROM feedback WHERE complaint_id=?',(r['id'],)).fetchone();x['feedback']=dict(f) if f else None;results.append(x)
    self.send(200,results);return
  if p=='/api/officers':
   if u['role']!='admin':self.send(403,{'error':'Administrator access required.'});return
   with con() as d:self.send(200,[dict(x) for x in d.execute("SELECT id,name,email,phone,status,created_at FROM users WHERE role='officer' ORDER BY id DESC")]);return
  if p=='/api/users':
   if u['role']!='admin':self.send(403,{'error':'Administrator access required.'});return
   with con() as d:self.send(200,[dict(x) for x in d.execute('SELECT id,name,email,phone,role,status,created_at FROM users ORDER BY id DESC')]);return
  if p=='/api/notifications':
   with con() as d:self.send(200,[dict(x) for x in d.execute('SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 40',(u['id'],))]);return
  if p.startswith('/api/complaints/'):
   try:cid=int(p.rsplit('/',1)[-1])
   except:self.send(404,{'error':'Complaint not found.'});return
   with con() as d:
    q='SELECT c.*,u.name citizen_name,o.name officer_name FROM complaints c JOIN users u ON u.id=c.citizen_id LEFT JOIN users o ON o.id=c.officer_id WHERE c.id=?';row=d.execute(q,(cid,)).fetchone()
    if not row:self.send(404,{'error':'Complaint not found.'});return
    if u['role']=='citizen' and row['citizen_id']!=u['id'] or u['role']=='officer' and row['officer_id'] not in (None,u['id']):self.send(403,{'error':'You cannot view this complaint.'});return
    x=dict(row);x['attachments']=[dict(a) for a in d.execute('SELECT id,kind,filename,mime,created_at FROM attachments WHERE complaint_id=?',(cid,))];x['updates']=[dict(a) for a in d.execute('SELECT x.*,u.name author FROM updates x JOIN users u ON u.id=x.user_id WHERE x.complaint_id=? ORDER BY x.id',(cid,))];self.send(200,x);return
  self.send(404,{'error':'Not found.'})
 def do_POST(self):
  p=urlparse(self.path).path;x=self.body()
  if p in ('/api/register','/api/login'):
   with con() as d:
    if p.endswith('register'):
     name=str(x.get('name','')).strip()[:80];email=str(x.get('email','')).strip().lower()[:120];phone=str(x.get('phone','')).strip()[:32];password=str(x.get('password',''));role=x.get('role','citizen')
     if self.settings().get(role+'_registration','true')=='false':self.send(403,{'error':'Registration is currently closed for this account type.'});return
     if not name or '@' not in email or len(password)<8 or role not in ('citizen','officer'):self.send(400,{'error':'Enter your name, a valid email, an 8+ character password, and account type.'});return
     salt=secrets.token_hex(16);status='pending' if role=='officer' else 'approved'
     try:cur=d.execute('INSERT INTO users(name,email,phone,role,status,password_hash,salt) VALUES(?,?,?,?,?,?,?)',(name,email,phone,role,status,phash(password,salt),salt))
     except sqlite3.IntegrityError:self.send(409,{'error':'An account already uses that email.'});return
     self.send(201,{'id':cur.lastrowid,'name':name,'email':email,'phone':phone,'role':role,'status':status});return
    row=d.execute('SELECT * FROM users WHERE email=?',(str(x.get('email','')).lower().strip(),)).fetchone();password=str(x.get('password',''))
    if not row or not secrets.compare_digest(phash(password,row['salt']),row['password_hash']):self.send(401,{'error':'Email or password did not match.'});return
    if row['status']!='approved':self.send(403,{'error':'This account is waiting for administrator approval or has been paused.'});return
    self.send(200,{k:row[k] for k in ('id','name','email','phone','role','status')});return
  u=self.allowed()
  if not u:self.send(401,{'error':'Sign in to continue.'});return
  with con() as d:
   if p=='/api/complaints' and u['role']=='citizen':
    if self.settings().get('citizen_submit','true')=='false':self.send(403,{'error':'Complaint submission is temporarily unavailable.'});return
    title=str(x.get('title','')).strip()[:120];category=str(x.get('category','')).strip()[:80];desc=str(x.get('description','')).strip()[:5000];location=str(x.get('location','')).strip()[:300]
    if not title or not category or len(desc)<12 or len(location)<3:self.send(400,{'error':'Add a title, category, description, and location.'});return
    try:lat=float(x['latitude']) if x.get('latitude') not in (None,'') else None;lon=float(x['longitude']) if x.get('longitude') not in (None,'') else None
    except:self.send(400,{'error':'Map coordinates are invalid.'});return
    ref='CE-'+secrets.token_hex(4).upper();cur=d.execute('INSERT INTO complaints(reference,citizen_id,category,title,description,location,latitude,longitude) VALUES(?,?,?,?,?,?,?,?)',(ref,u['id'],category,title,desc,location,lat,lon));cid=cur.lastrowid
    err=self.save_files(d,cid,u['id'],'submission',x.get('files',[]))
    if err:d.execute('DELETE FROM complaints WHERE id=?',(cid,));self.send(400,{'error':err});return
    d.execute('INSERT INTO updates(complaint_id,user_id,status,note) VALUES(?,?,?,?)',(cid,u['id'],'Submitted','Complaint received and added to the resolution queue.'));d.execute('INSERT INTO notifications(user_id,message) VALUES(?,?)',(u['id'],f'Complaint {ref} was submitted. We’ll keep you posted.'))
    self.send(201,{'id':cid,'reference':ref});return
   if p.startswith('/api/complaints/') and p.endswith('/evidence') and u['role']=='citizen':
    cid=int(p.split('/')[-2]);row=d.execute('SELECT * FROM complaints WHERE id=? AND citizen_id=?',(cid,u['id'])).fetchone()
    if not row:self.send(404,{'error':'Complaint not found.'});return
    note=str(x.get('note','')).strip()[:2000];err=self.save_files(d,cid,u['id'],'evidence',x.get('files',[]))
    if err:self.send(400,{'error':err});return
    if note:d.execute('INSERT INTO updates(complaint_id,user_id,status,note) VALUES(?,?,?,?)',(cid,u['id'],row['status'],note))
    self.send(201,{'ok':True});return
   if p.startswith('/api/complaints/') and p.endswith('/feedback') and u['role']=='citizen':
    cid=int(p.split('/')[-2]);row=d.execute('SELECT * FROM complaints WHERE id=? AND citizen_id=?',(cid,u['id'])).fetchone()
    if not row or row['status'] not in ('Resolved','Closed'):self.send(400,{'error':'Feedback is available after resolution.'});return
    try:rating=max(1,min(5,int(x.get('rating',5))))
    except:rating=5
    try:d.execute('INSERT INTO feedback(complaint_id,citizen_id,rating,comment) VALUES(?,?,?,?)',(cid,u['id'],rating,str(x.get('comment',''))[:1000]))
    except sqlite3.IntegrityError:self.send(409,{'error':'Feedback has already been sent.'});return
    self.send(201,{'ok':True});return
   if p.startswith('/api/complaints/') and p.endswith('/resolve') and u['role']=='officer':
    cid=int(p.split('/')[-2]);row=d.execute('SELECT * FROM complaints WHERE id=?',(cid,)).fetchone()
    if not row or row['officer_id'] not in (None,u['id']):self.send(403,{'error':'This complaint is assigned to another officer.'});return
    status=str(x.get('status','In progress'))
    if status not in ('Assigned','In progress','Resolved','Closed','Reopened'):self.send(400,{'error':'Choose a valid complaint status.'});return
    note=str(x.get('note','')).strip()[:3000]
    if x.get('files') and self.settings().get('officer_proof','true')=='false':self.send(403,{'error':'Proof uploads are currently hidden.'});return
    err=self.save_files(d,cid,u['id'],'proof',x.get('files',[]))
    if err:self.send(400,{'error':err});return
    d.execute('UPDATE complaints SET officer_id=?,status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(u['id'],status,cid))
    d.execute('INSERT INTO updates(complaint_id,user_id,status,note) VALUES(?,?,?,?)',(cid,u['id'],status,note));d.execute('INSERT INTO notifications(user_id,message) VALUES(?,?)',(row['citizen_id'],f'Complaint {row["reference"]} is now {status.lower()}.'+(f' {note}' if note else '')));self.send(200,{'ok':True});return
   if p=='/api/admin/officers' and u['role']=='admin':
    name=str(x.get('name','')).strip()[:80];email=str(x.get('email','')).strip().lower()[:120];phone=str(x.get('phone','')).strip()[:32];password=str(x.get('password',''))
    if not name or '@' not in email or len(password)<8:self.send(400,{'error':'Enter name, valid email, and a password with at least 8 characters.'});return
    salt=secrets.token_hex(16)
    try:d.execute('INSERT INTO users(name,email,phone,role,status,password_hash,salt) VALUES(?,?,?,\'officer\',\'approved\',?,?)',(name,email,phone,phash(password,salt),salt))
    except sqlite3.IntegrityError:self.send(409,{'error':'That email already has an account.'});return
    self.send(201,{'ok':True});return
   if p=='/api/admin/account' and u['role']=='admin':
    name=str(x.get('name','')).strip()[:80];email=str(x.get('email','')).strip().lower()[:120];phone=str(x.get('phone','')).strip()[:32];password=str(x.get('password',''));role=x.get('role','citizen')
    if not name or '@' not in email or len(password)<8 or role not in ('citizen','officer','admin'):self.send(400,{'error':'Enter name, valid email, password (8+ characters), and a valid role.'});return
    salt=secrets.token_hex(16)
    try:d.execute('INSERT INTO users(name,email,phone,role,status,password_hash,salt) VALUES(?,?,?,?,?,?,?)',(name,email,phone,role,'approved',phash(password,salt),salt))
    except sqlite3.IntegrityError:self.send(409,{'error':'That email already has an account.'});return
    self.send(201,{'ok':True});return
   if p=='/api/admin/categories' and u['role']=='admin':
    name=str(x.get('name','')).strip()[:80];icon=str(x.get('icon','＋'))[:8]
    if not name:self.send(400,{'error':'Category name is required.'});return
    try:d.execute('INSERT INTO categories(name,icon) VALUES(?,?)',(name,icon))
    except sqlite3.IntegrityError:self.send(409,{'error':'That category already exists.'});return
    self.send(201,{'ok':True});return
   if p=='/api/admin/settings' and u['role']=='admin':
    for key,val in x.items():
     if key in DEFAULTS:d.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,str(val)[:300]))
    self.send(200,{'ok':True});return
   if p=='/api/admin/assign' and u['role']=='admin':
    cid=int(x.get('complaint_id',0));oid=x.get('officer_id');officer=d.execute("SELECT id FROM users WHERE id=? AND role='officer' AND status='approved'",(int(oid),)).fetchone() if oid else None
    if oid and not officer:self.send(400,{'error':'Select an approved officer.'});return
    c=d.execute('SELECT * FROM complaints WHERE id=?',(cid,)).fetchone()
    if not c:self.send(404,{'error':'Complaint not found.'});return
    d.execute('UPDATE complaints SET officer_id=?,status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(int(oid) if oid else None,'Assigned' if oid else 'Submitted',cid));d.execute('INSERT INTO updates(complaint_id,user_id,status,note) VALUES(?,?,?,?)',(cid,u['id'],'Assigned' if oid else 'Submitted','Assigned to resolution officer.' if oid else 'Assignment cleared.'));self.send(200,{'ok':True});return
  self.send(404,{'error':'Not found.'})
 def do_PUT(self):
  p=urlparse(self.path).path;x=self.body();u=self.allowed(['admin'])
  if not u:self.send(403,{'error':'Administrator access required.'});return
  with con() as d:
   if p.startswith('/api/admin/users/'):
    uid=int(p.rsplit('/',1)[-1]);fields=[];vals=[]
    for k in ('name','email','phone','role','status'):
     if k in x:fields.append(k+'=?');vals.append(str(x[k])[:120])
    if x.get('role') and x['role'] not in ('citizen','officer','admin'):self.send(400,{'error':'Invalid account role.'});return
    if x.get('status') and x['status'] not in ('approved','pending','disabled'):self.send(400,{'error':'Invalid account status.'});return
    if x.get('password'):
     if len(str(x['password']))<8:self.send(400,{'error':'Passwords must have at least 8 characters.'});return
     salt=secrets.token_hex(16);fields+=['salt=?','password_hash=?'];vals += [salt,phash(str(x['password']),salt)]
    if not fields:self.send(400,{'error':'No account changes were provided.'});return
    vals.append(uid)
    try:d.execute('UPDATE users SET '+','.join(fields)+' WHERE id=?',vals)
    except sqlite3.IntegrityError:self.send(409,{'error':'That email is already in use.'});return
    self.send(200,{'ok':True});return
   self.send(404,{'error':'Not found.'})
 def do_DELETE(self):
  p=urlparse(self.path).path;u=self.allowed(['admin'])
  if not u:self.send(403,{'error':'Administrator access required.'});return
  with con() as d:
   if p.startswith('/api/admin/categories/'):
    cid=int(p.rsplit('/',1)[-1]);d.execute('UPDATE categories SET active=0 WHERE id=?',(cid,));self.send(200,{'ok':True});return
   if p.startswith('/api/admin/users/'):
    uid=int(p.rsplit('/',1)[-1])
    if uid==u['id']:self.send(400,{'error':'You cannot delete the admin account currently in use.'});return
    d.execute('DELETE FROM feedback WHERE citizen_id=?',(uid,));d.execute('UPDATE complaints SET citizen_id=? WHERE citizen_id=?',(u['id'],uid));d.execute('UPDATE attachments SET uploader_id=? WHERE uploader_id=?',(u['id'],uid));d.execute('UPDATE updates SET user_id=? WHERE user_id=?',(u['id'],uid));d.execute('DELETE FROM users WHERE id=?',(uid,));self.send(200,{'ok':True});return
  self.send(404,{'error':'Not found.'})
if __name__=='__main__':
 init();print(f'ComplainEase is running at http://localhost:{PORT}');ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
