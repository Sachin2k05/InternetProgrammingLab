"""VoteOnline classroom prototype. Run locally with: python server.py"""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime,timedelta,timezone
import hashlib,hmac,json,secrets,sqlite3

ROOT=Path(__file__).resolve().parent;DB=ROOT/'voteonline.db';PORT=8006;OTP_KEY=b'voteonline-classroom-demo-key-change-before-use'
def now():return datetime.now(timezone.utc)
def stamp(dt=None):return (dt or now()).isoformat(timespec='seconds')
def con():
 d=sqlite3.connect(DB);d.row_factory=sqlite3.Row;d.execute('PRAGMA foreign_keys=ON');return d
def pw_hash(password,salt):return hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),180000).hex()
def voter_hash(vid):return hmac.new(OTP_KEY,vid.strip().upper().encode(),hashlib.sha256).hexdigest()
def init():
 with con() as d:
  d.executescript('''CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,salt TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS wards(id INTEGER PRIMARY KEY,name TEXT UNIQUE NOT NULL,code TEXT UNIQUE NOT NULL);
  CREATE TABLE IF NOT EXISTS voters(id INTEGER PRIMARY KEY,voter_id TEXT UNIQUE NOT NULL,name TEXT NOT NULL,email TEXT NOT NULL,phone TEXT DEFAULT '',ward_id INTEGER REFERENCES wards(id),status TEXT DEFAULT 'active',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS elections(id INTEGER PRIMARY KEY,title TEXT NOT NULL,description TEXT DEFAULT '',kind TEXT DEFAULT 'General',opens_at TEXT,closes_at TEXT,status TEXT DEFAULT 'Draft',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS candidates(id INTEGER PRIMARY KEY,election_id INTEGER NOT NULL REFERENCES elections(id) ON DELETE CASCADE,name TEXT NOT NULL,party TEXT DEFAULT '',bio TEXT DEFAULT '',ward_id INTEGER REFERENCES wards(id),color TEXT DEFAULT '#5473ad',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS voter_elections(voter_id INTEGER NOT NULL REFERENCES voters(id) ON DELETE CASCADE,election_id INTEGER NOT NULL REFERENCES elections(id) ON DELETE CASCADE,ward_id INTEGER REFERENCES wards(id),PRIMARY KEY(voter_id,election_id));
  CREATE TABLE IF NOT EXISTS otp_codes(id INTEGER PRIMARY KEY,voter_id INTEGER NOT NULL REFERENCES voters(id) ON DELETE CASCADE,purpose TEXT NOT NULL,code_hash TEXT NOT NULL,salt TEXT NOT NULL,expires_at TEXT NOT NULL,used INTEGER DEFAULT 0,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,actor TEXT NOT NULL,actor_id INTEGER NOT NULL,expires_at TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS participation(id INTEGER PRIMARY KEY,election_id INTEGER NOT NULL REFERENCES elections(id),voter_hash TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(election_id,voter_hash));
  CREATE TABLE IF NOT EXISTS ballots(id INTEGER PRIMARY KEY,election_id INTEGER NOT NULL REFERENCES elections(id),candidate_id INTEGER NOT NULL REFERENCES candidates(id),ballot_hash TEXT UNIQUE NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS voter_history(id INTEGER PRIMARY KEY,voter_id INTEGER NOT NULL REFERENCES voters(id),election_id INTEGER NOT NULL REFERENCES elections(id),receipt_hash TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(voter_id,election_id));
  CREATE TABLE IF NOT EXISTS delivery_log(id INTEGER PRIMARY KEY,voter_id INTEGER NOT NULL REFERENCES voters(id),channel TEXT NOT NULL,purpose TEXT NOT NULL,destination TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);''')
  if not d.execute("SELECT 1 FROM admins WHERE email='admin@voteonline.test'").fetchone():
   salt=secrets.token_hex(16);d.execute("INSERT INTO admins(name,email,password_hash,salt) VALUES('VoteOnline Administrator','admin@voteonline.test',?,?)",(pw_hash('ballot12345',salt),salt))
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def send(self,s,data):
  b=json.dumps(data).encode();self.send_response(s);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def body(self):
  try:return json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))) or b'{}')
  except:return {}
 def auth(self):
  token=self.headers.get('X-Admin') or self.headers.get('X-Voter') or ''
  if not token:return (None,None)
  key=hashlib.sha256(token.encode()).hexdigest()
  with con() as d:
   row=d.execute('SELECT * FROM sessions WHERE token_hash=? AND expires_at>?',(key,stamp())).fetchone()
   if not row:return (None,None)
   if row['actor']=='admin':return ('admin',d.execute('SELECT id,name,email FROM admins WHERE id=?',(row['actor_id'],)).fetchone())
   return ('voter',d.execute('SELECT id,voter_id,name,email,phone,ward_id,status FROM voters WHERE id=? AND status="active"',(row['actor_id'],)).fetchone())
 def admin(self):
  role,obj=self.auth();return obj if role=='admin' else None
 def voter(self):
  role,obj=self.auth();return obj if role=='voter' else None
 def mint_session(self,actor,actor_id):
  token=secrets.token_urlsafe(32);expires=stamp(now()+timedelta(hours=8))
  with con() as d:d.execute('INSERT INTO sessions(token_hash,actor,actor_id,expires_at) VALUES(?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),actor,actor_id,expires))
  return token
 def do_GET(self):
  p=urlparse(self.path).path;role,obj=self.auth()
  if p=='/':
   self.send_response(200);data=(ROOT/'index.html').read_bytes();self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
  if p in ('/styles.css','/script.js'):
   f=ROOT/p.lstrip('/');data=f.read_bytes();self.send_response(200);self.send_header('Content-Type','text/css; charset=utf-8' if f.suffix=='.css' else 'application/javascript; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
  if p=='/api/me':self.send(200,{'role':role,**(dict(obj) if obj else {})});return
  if p=='/api/wards':
   with con() as d:self.send(200,[dict(x) for x in d.execute('SELECT * FROM wards ORDER BY name')]);return
  if p=='/api/elections':
   with con() as d:
    rows=d.execute('SELECT * FROM elections ORDER BY id DESC').fetchall();out=[]
    for e in rows:
     x=dict(e);x['candidates']=[dict(c) for c in d.execute('SELECT c.*,w.name ward_name FROM candidates c LEFT JOIN wards w ON w.id=c.ward_id WHERE c.election_id=? ORDER BY c.id',(e['id'],))];assignment=d.execute('SELECT ward_id FROM voter_elections WHERE voter_id=? AND election_id=?',(obj['id'],e['id'])).fetchone() if obj and role=='voter' else None;x['my_ward_id']=assignment['ward_id'] if assignment else None;x['my_vote']=bool(obj and role=='voter' and d.execute('SELECT 1 FROM participation WHERE election_id=? AND voter_hash=?',(e['id'],voter_hash(obj['voter_id']))).fetchone());x['eligible']=bool(assignment);x['turnout_count']=d.execute('SELECT COUNT(*) n FROM participation WHERE election_id=?',(e['id'],)).fetchone()['n'];x['results']=None
     if e['status']=='Closed' or role=='admin':x['results']=[dict(r) for r in d.execute('SELECT c.id,c.name,c.party,COUNT(b.id) votes FROM candidates c LEFT JOIN ballots b ON b.candidate_id=c.id AND b.election_id=c.election_id WHERE c.election_id=? GROUP BY c.id ORDER BY votes DESC,c.id',(e['id'],))]
     out.append(x)
    self.send(200,out);return
  if p=='/api/admin/voters':
   if not self.admin():self.send(403,{'error':'Administrator access required.'});return
   with con() as d:self.send(200,[dict(x) for x in d.execute('SELECT v.*,w.name ward_name FROM voters v LEFT JOIN wards w ON w.id=v.ward_id ORDER BY v.id DESC')]);return
  if p=='/api/admin/candidates':
   if not self.admin():self.send(403,{'error':'Administrator access required.'});return
   with con() as d:self.send(200,[dict(x) for x in d.execute('SELECT c.*,e.title election_title,w.name ward_name FROM candidates c JOIN elections e ON e.id=c.election_id LEFT JOIN wards w ON w.id=c.ward_id ORDER BY c.id DESC')]);return
  if p=='/api/history':
   v=self.voter()
   if not v:self.send(401,{'error':'Voter verification required.'});return
   with con() as d:self.send(200,[dict(x) for x in d.execute('SELECT h.created_at,e.title,e.kind,e.status FROM voter_history h JOIN elections e ON e.id=h.election_id WHERE h.voter_id=? ORDER BY h.id DESC',(v['id'],))]);return
  if p=='/api/admin/results':
   if not self.admin():self.send(403,{'error':'Administrator access required.'});return
   with con() as d:
    rows=d.execute('SELECT * FROM elections ORDER BY id DESC').fetchall();out=[]
    for e in rows:out.append({'election':dict(e),'turnout':d.execute('SELECT COUNT(*) n FROM participation WHERE election_id=?',(e['id'],)).fetchone()['n'],'results':[dict(r) for r in d.execute('SELECT c.id,c.name,c.party,COUNT(b.id) votes FROM candidates c LEFT JOIN ballots b ON b.candidate_id=c.id AND b.election_id=c.election_id WHERE c.election_id=? GROUP BY c.id ORDER BY votes DESC',(e['id'],))]})
    self.send(200,out);return
  self.send(404,{'error':'Not found.'})
 def do_POST(self):
  p=urlparse(self.path).path;x=self.body()
  if p=='/api/admin/login':
   with con() as d:a=d.execute('SELECT * FROM admins WHERE email=?',(str(x.get('email','')).lower().strip(),)).fetchone()
   if not a or not hmac.compare_digest(pw_hash(str(x.get('password','')),a['salt']),a['password_hash']):self.send(401,{'error':'Email or password did not match.'});return
   self.send(200,{'token':self.mint_session('admin',a['id']),'role':'admin','name':a['name'],'email':a['email']});return
  if p=='/api/auth/request':
   vid=str(x.get('voter_id','')).strip().upper()
   with con() as d:v=d.execute('SELECT * FROM voters WHERE voter_id=? AND status="active"',(vid,)).fetchone()
   if not v:self.send(404,{'error':'Voter ID not found or inactive. Contact the election administrator.'});return
   code=f'{secrets.randbelow(1000000):06d}';salt=secrets.token_hex(12);purpose='login';expires=stamp(now()+timedelta(minutes=5))
   with con() as d:d.execute('INSERT INTO otp_codes(voter_id,purpose,code_hash,salt,expires_at) VALUES(?,?,?,?,?)',(v['id'],purpose,hashlib.sha256((salt+code).encode()).hexdigest(),salt,expires));d.execute('INSERT INTO delivery_log(voter_id,channel,purpose,destination) VALUES(?,?,?,?)',(v['id'],'Email/SMS demo',purpose,v['email']))
   self.send(200,{'ok':True,'message':'Demo verification code is ready. Real email/SMS delivery is not connected.','demo_otp':code,'expires_in_seconds':300});return
  if p=='/api/auth/verify':
   vid=str(x.get('voter_id','')).strip().upper();code=str(x.get('otp','')).strip()
   with con() as d:
    v=d.execute('SELECT * FROM voters WHERE voter_id=? AND status="active"',(vid,)).fetchone();otp=d.execute('SELECT * FROM otp_codes WHERE voter_id=? AND purpose="login" AND used=0 ORDER BY id DESC LIMIT 1',(v['id'],)).fetchone() if v else None
    if not otp or otp['expires_at']<stamp() or not hmac.compare_digest(hashlib.sha256((otp['salt']+code).encode()).hexdigest(),otp['code_hash']):self.send(401,{'error':'That one-time code is incorrect or expired.'});return
    d.execute('UPDATE otp_codes SET used=1 WHERE id=?',(otp['id'],));token=secrets.token_urlsafe(32);d.execute('INSERT INTO sessions(token_hash,actor,actor_id,expires_at) VALUES(?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),'voter',v['id'],stamp(now()+timedelta(hours=8))));self.send(200,{'token':token,'role':'voter','name':v['name'],'voter_id':v['voter_id'],'ward_id':v['ward_id']});return
  v=self.voter();admin=self.admin()
  if p=='/api/otp/vote':
   if not v:self.send(401,{'error':'Sign in as a voter first.'});return
   eid=int(x.get('election_id',0))
   with con() as d:
    e=d.execute('SELECT * FROM elections WHERE id=? AND status="Open"',(eid,)).fetchone()
    if not e:self.send(400,{'error':'This election is not open.'});return
    elig=d.execute('SELECT 1 FROM voter_elections WHERE voter_id=? AND election_id=?',(v['id'],eid)).fetchone()
    if not elig:self.send(403,{'error':'Your voter record is not allocated to this election.'});return
    if d.execute('SELECT 1 FROM participation WHERE election_id=? AND voter_hash=?',(eid,voter_hash(v['voter_id']))).fetchone():self.send(409,{'error':'Your vote has already been recorded for this election.'});return
    code=f'{secrets.randbelow(1000000):06d}';salt=secrets.token_hex(12);expires=stamp(now()+timedelta(minutes=5));purpose=f'vote:{eid}';d.execute('INSERT INTO otp_codes(voter_id,purpose,code_hash,salt,expires_at) VALUES(?,?,?,?,?)',(v['id'],purpose,hashlib.sha256((salt+code).encode()).hexdigest(),salt,expires));d.execute('INSERT INTO delivery_log(voter_id,channel,purpose,destination) VALUES(?,?,?,?)',(v['id'],'Email/SMS demo',purpose,v['email']))
   self.send(200,{'ok':True,'demo_otp':code,'message':'Demo voting code generated. Real OTP delivery is not connected.','expires_in_seconds':300});return
  if p=='/api/vote':
   if not v:self.send(401,{'error':'Voter sign-in required.'});return
   eid=int(x.get('election_id',0));candidate=int(x.get('candidate_id',0));code=str(x.get('otp','')).strip()
   with con() as d:
    e=d.execute('SELECT * FROM elections WHERE id=? AND status="Open"',(eid,)).fetchone();elig=d.execute('SELECT ward_id FROM voter_elections WHERE voter_id=? AND election_id=?',(v['id'],eid)).fetchone();otp=d.execute('SELECT * FROM otp_codes WHERE voter_id=? AND purpose=? AND used=0 ORDER BY id DESC LIMIT 1',(v['id'],f'vote:{eid}')).fetchone()
    if not e or not elig:self.send(403,{'error':'This voter is not eligible in the open election.'});return
    if not otp or otp['expires_at']<stamp() or not hmac.compare_digest(hashlib.sha256((otp['salt']+code).encode()).hexdigest(),otp['code_hash']):self.send(401,{'error':'Voting code is incorrect or expired.'});return
    c=d.execute('SELECT * FROM candidates WHERE id=? AND election_id=? AND (ward_id IS NULL OR ward_id=?)',(candidate,eid,elig['ward_id'])).fetchone()
    if not c:self.send(400,{'error':'Choose a candidate available in your ward.'});return
    vh=voter_hash(v['voter_id']);
    try:d.execute('INSERT INTO participation(election_id,voter_hash) VALUES(?,?)',(eid,vh))
    except sqlite3.IntegrityError:self.send(409,{'error':'A vote is already recorded for this voter.'});return
    d.execute('INSERT INTO ballots(election_id,candidate_id,ballot_hash) VALUES(?,?,?)',(eid,candidate,secrets.token_hex(24)));d.execute('UPDATE otp_codes SET used=1 WHERE id=?',(otp['id'],));receipt='VO-'+secrets.token_hex(5).upper();d.execute('INSERT INTO voter_history(voter_id,election_id,receipt_hash) VALUES(?,?,?)',(v['id'],eid,hashlib.sha256(receipt.encode()).hexdigest()));self.send(201,{'ok':True,'receipt':receipt,'message':'Your selection has been recorded. The ballot is stored without a voter ID.'});return
  if not admin:self.send(403,{'error':'Administrator access required.'});return
  with con() as d:
   if p=='/api/admin/wards':
    name=str(x.get('name','')).strip()[:80];code=str(x.get('code','')).strip().upper()[:20]
    if not name or not code:self.send(400,{'error':'Ward name and code are required.'});return
    try:d.execute('INSERT INTO wards(name,code) VALUES(?,?)',(name,code))
    except sqlite3.IntegrityError:self.send(409,{'error':'That ward name or code already exists.'});return
    self.send(201,{'ok':True});return
   if p=='/api/admin/elections':
    title=str(x.get('title','')).strip()[:120];desc=str(x.get('description','')).strip()[:1000];kind=str(x.get('kind','General'))
    if not title:self.send(400,{'error':'Election title is required.'});return
    cur=d.execute('INSERT INTO elections(title,description,kind,opens_at,closes_at,status) VALUES(?,?,?,?,?,?)',(title,desc,kind,str(x.get('opens_at',''))[:40],str(x.get('closes_at',''))[:40],str(x.get('status','Draft'))));self.send(201,{'id':cur.lastrowid});return
   if p=='/api/admin/candidates':
    eid=int(x.get('election_id',0));name=str(x.get('name','')).strip()[:100];party=str(x.get('party','')).strip()[:100];bio=str(x.get('bio','')).strip()[:1000];ward=x.get('ward_id') or None
    if not name or not d.execute('SELECT 1 FROM elections WHERE id=?',(eid,)).fetchone():self.send(400,{'error':'Choose an election and enter the candidate name.'});return
    d.execute('INSERT INTO candidates(election_id,name,party,bio,ward_id,color) VALUES(?,?,?,?,?,?)',(eid,name,party,bio,int(ward) if ward else None,str(x.get('color','#5473ad'))[:20]));self.send(201,{'ok':True});return
   if p=='/api/admin/voters':
    result=self.add_voter(d,x)
    self.send(result[0],result[1]);return
   if p=='/api/admin/import-voters':
    rows=x.get('voters',[]);created=0;errors=[]
    for i,row in enumerate(rows[:1000],start=1):
     status,data=self.add_voter(d,row)
     if status<300:created+=1
     else:errors.append({'row':i,'error':data.get('error')})
    self.send(200,{'created':created,'errors':errors[:50]});return
   if p=='/api/admin/allocate':
    voter=d.execute('SELECT * FROM voters WHERE id=?',(int(x.get('voter_id',0)),)).fetchone();e=d.execute('SELECT * FROM elections WHERE id=?',(int(x.get('election_id',0)),)).fetchone()
    if not voter or not e:self.send(400,{'error':'Choose an existing voter and election.'});return
    ward_id=int(x.get('ward_id') or voter['ward_id'] or 0) or None
    d.execute('INSERT INTO voter_elections(voter_id,election_id,ward_id) VALUES(?,?,?) ON CONFLICT(voter_id,election_id) DO UPDATE SET ward_id=excluded.ward_id',(voter['id'],e['id'],ward_id));self.send(200,{'ok':True});return
  self.send(404,{'error':'Not found.'})
 def add_voter(self,d,x):
  vid=str(x.get('voter_id','')).strip().upper()[:40];name=str(x.get('name','')).strip()[:100];email=str(x.get('email','')).strip().lower()[:120];phone=str(x.get('phone','')).strip()[:30];ward=x.get('ward_id') or None
  if not vid or not name or '@' not in email:return (400,{'error':'Voter ID, name, and a valid email are required.'})
  if ward and not d.execute('SELECT 1 FROM wards WHERE id=?',(int(ward),)).fetchone():return (400,{'error':'Selected ward does not exist.'})
  election_ids=x.get('election_ids',[])
  if any(not d.execute('SELECT 1 FROM elections WHERE id=?',(int(eid),)).fetchone() for eid in election_ids):return (400,{'error':'One selected election does not exist.'})
  try:
   cur=d.execute('INSERT INTO voters(voter_id,name,email,phone,ward_id,status) VALUES(?,?,?,?,?,?)',(vid,name,email,phone,int(ward) if ward else None,str(x.get('status','active'))));voter_pk=cur.lastrowid
   for eid in election_ids:d.execute('INSERT OR IGNORE INTO voter_elections(voter_id,election_id,ward_id) VALUES(?,?,?)',(voter_pk,int(eid),int(ward) if ward else None))
   return (201,{'ok':True,'id':voter_pk})
  except sqlite3.IntegrityError:d.rollback();return (409,{'error':f'Voter ID {vid} already exists or a selected record is invalid.'})
 def do_PUT(self):
  p=urlparse(self.path).path;x=self.body();admin=self.admin()
  if not admin:self.send(403,{'error':'Administrator access required.'});return
  with con() as d:
   if p.startswith('/api/admin/elections/'):
    eid=int(p.rsplit('/',1)[-1]);status=x.get('status')
    if status not in ('Draft','Open','Closed'):self.send(400,{'error':'Status must be Draft, Open, or Closed.'});return
    d.execute('UPDATE elections SET status=? WHERE id=?',(status,eid));self.send(200,{'ok':True});return
   if p.startswith('/api/admin/voters/'):
    vid=int(p.rsplit('/',1)[-1]);fields=[];vals=[]
    for k in ('voter_id','name','email','phone','status','ward_id'):
     if k in x:fields.append(k+'=?');vals.append(int(x[k]) if k=='ward_id' and x[k] else (None if k=='ward_id' else str(x[k])))
    if not fields:self.send(400,{'error':'No voter changes provided.'});return
    vals.append(vid)
    try:d.execute('UPDATE voters SET '+','.join(fields)+' WHERE id=?',vals)
    except sqlite3.IntegrityError:self.send(409,{'error':'Voter ID already exists or ward is invalid.'});return
    self.send(200,{'ok':True});return
  self.send(404,{'error':'Not found.'})
 def do_DELETE(self):
  p=urlparse(self.path).path
  if not self.admin():self.send(403,{'error':'Administrator access required.'});return
  with con() as d:
   if p.startswith('/api/admin/voters/'):
    d.execute('UPDATE voters SET status="inactive" WHERE id=?',(int(p.rsplit('/',1)[-1]),));d.execute('DELETE FROM sessions WHERE actor="voter" AND actor_id=?',(int(p.rsplit('/',1)[-1]),));self.send(200,{'ok':True});return
   if p.startswith('/api/admin/candidates/'):
    cid=int(p.rsplit('/',1)[-1])
    if d.execute('SELECT 1 FROM ballots WHERE candidate_id=?',(cid,)).fetchone():self.send(409,{'error':'A candidate with recorded votes cannot be removed.'});return
    d.execute('DELETE FROM candidates WHERE id=?',(cid,));self.send(200,{'ok':True});return
   if p.startswith('/api/admin/wards/'):
    wid=int(p.rsplit('/',1)[-1]);used=sum(d.execute(f'SELECT COUNT(*) n FROM {table} WHERE {col}=?',(wid,)).fetchone()['n'] for table,col in [('voters','ward_id'),('candidates','ward_id'),('voter_elections','ward_id')])
    if used:self.send(409,{'error':'This ward is assigned to a voter or candidate and cannot be removed yet.'});return
    d.execute('DELETE FROM wards WHERE id=?',(wid,));self.send(200,{'ok':True});return
  self.send(404,{'error':'Not found.'})
if __name__=='__main__':
 init();print(f'VoteOnline is running at http://localhost:{PORT}');ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
