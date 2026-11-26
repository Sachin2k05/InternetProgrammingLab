"""CareerBoard Lab 21 local demo. Run: python server.py"""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs
import sqlite3,json,secrets,hashlib,time,mimetypes
ROOT=Path(__file__).parent;DB=ROOT/'careerboard.db'
def db():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c
def init():
 with db() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS accounts(id INTEGER PRIMARY KEY,name TEXT,email TEXT UNIQUE,password TEXT,role TEXT,company TEXT DEFAULT '',location TEXT DEFAULT '',approved INTEGER DEFAULT 1,created TEXT DEFAULT CURRENT_TIMESTAMP);CREATE TABLE IF NOT EXISTS vacancies(id INTEGER PRIMARY KEY,director_id INTEGER REFERENCES accounts(id),title TEXT,category TEXT,location TEXT,description TEXT,contact TEXT,image TEXT DEFAULT '',created TEXT DEFAULT CURRENT_TIMESTAMP);CREATE TABLE IF NOT EXISTS applications(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES accounts(id),vacancy_id INTEGER REFERENCES vacancies(id),resume TEXT,privacy TEXT DEFAULT 'All companies',status TEXT DEFAULT 'Submitted',created TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(user_id,vacancy_id));CREATE TABLE IF NOT EXISTS saved_jobs(user_id INTEGER REFERENCES accounts(id),vacancy_id INTEGER REFERENCES vacancies(id),PRIMARY KEY(user_id,vacancy_id));CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER,admin INTEGER DEFAULT 0,expires INTEGER);''')
  for n,e,p,r,co,loc in [('Maya Chen','maya@career.test','applicant1','applicant','','Portland'),('Northstar Studio','director@career.test','director1','director','Northstar Studio','Portland')]:
   if not c.execute('SELECT id FROM accounts WHERE email=?',(e,)).fetchone():c.execute('INSERT INTO accounts(name,email,password,role,company,location,approved) VALUES(?,?,?,?,?,?,1)',(n,e,hashlib.sha256(p.encode()).hexdigest(),r,co,loc))
  if not c.execute('SELECT id FROM accounts WHERE email=?',('admin@career.test',)).fetchone():c.execute('INSERT INTO accounts(name,email,password,role,approved) VALUES(?,?,?,?,1)',('CareerBoard Admin','admin@career.test',hashlib.sha256(b'career123').hexdigest(),'admin'))
  if not c.execute('SELECT id FROM vacancies LIMIT 1').fetchone():
   did=c.execute('SELECT id FROM accounts WHERE email=?',('director@career.test',)).fetchone()['id']
   for x in [('Product Designer','Design','Portland','Help shape a thoughtful product experience with a collaborative team.','jobs@northstar.test','✦'),('Community Coordinator','Operations','Remote','Build welcoming programs and connect people to useful resources.','jobs@northstar.test','◎'),('Frontend Developer','Technology','Portland','Create accessible, fast web experiences with a curious engineering team.','jobs@northstar.test','⌘')]:c.execute('INSERT INTO vacancies(director_id,title,category,location,description,contact,image) VALUES(?,?,?,?,?,?,?)',(did,*x))
def pack(r):return dict(r) if r else None
class H(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def send(self,s,d):
  b=json.dumps(d).encode();self.send_response(s);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.send_header('Access-Control-Allow-Origin','*');self.end_headers();self.wfile.write(b)
 def auth(self,c,admin=False,role=None):
  t=self.headers.get('Authorization','').replace('Bearer ','');u=c.execute('SELECT s.admin,s.user_id,a.name admin_name,a.email admin_email,x.name,x.email,x.role,x.approved FROM sessions s LEFT JOIN accounts a ON a.email="admin@career.test" LEFT JOIN accounts x ON x.id=s.user_id WHERE s.token=? AND s.expires>?',(t,int(time.time()))).fetchone()
  if not u:raise PermissionError('Please sign in to continue.')
  if admin and not u['admin']:raise PermissionError('Administrator access required.')
  if role and (u['role']!=role or not u['approved']):raise PermissionError('An approved '+role+' account is required.')
  return u
 def do_OPTIONS(self):self.send_response(204);self.send_header('Access-Control-Allow-Origin','*');self.send_header('Access-Control-Allow-Headers','Authorization, Content-Type');self.send_header('Access-Control-Allow-Methods','GET,POST,PUT,DELETE,OPTIONS');self.end_headers()
 def do_GET(self):
  p=urlparse(self.path).path;q=parse_qs(urlparse(self.path).query)
  if p=='/' or p=='/index.html':
   b=(ROOT/'index.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
  if p in('/styles.css','/script.js'):
   b=(ROOT/p[1:]).read_bytes();self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(p)[0] or 'text/plain');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
  with db() as c:
   try:
    if p=='/api/vacancies':
     sql='SELECT v.*,a.company FROM vacancies v JOIN accounts a ON a.id=v.director_id WHERE 1=1';args=[]
     for col,key in [('location','location'),('category','category')]:
      val=q.get(key,['All'])[0]
      if val not in('All',''):sql+=f' AND v.{col}=?';args.append(val)
     term=q.get('q',[''])[0]
     if term:sql+=' AND (v.title LIKE ? OR v.description LIKE ? OR a.company LIKE ?)';args += [f'%{term}%']*3
     self.send(200,[pack(r) for r in c.execute(sql+' ORDER BY v.id DESC',args).fetchall()]);return
    u=self.auth(c)
    if p=='/api/me':self.send(200,{k:u[k] for k in('name','email','role')});return
    if p=='/api/my-applications':self.send(200,[pack(r) for r in c.execute('SELECT ap.*,v.title,v.company,v.location FROM applications ap JOIN vacancies v ON v.id=ap.vacancy_id JOIN accounts a ON a.id=v.director_id WHERE ap.user_id=? ORDER BY ap.id DESC',(u['user_id'],)).fetchall()]);return
    if p=='/api/saved':self.send(200,[pack(r) for r in c.execute('SELECT v.*,a.company FROM saved_jobs s JOIN vacancies v ON v.id=s.vacancy_id JOIN accounts a ON a.id=v.director_id WHERE s.user_id=?',(u['user_id'],)).fetchall()]);return
    if p=='/api/director/vacancies':self.auth(c,role='director');self.send(200,[pack(r) for r in c.execute('SELECT * FROM vacancies WHERE director_id=?',(u['user_id'],)).fetchall()]);return
    if p=='/api/director/applications':self.auth(c,role='director');self.send(200,[pack(r) for r in c.execute('SELECT ap.*,a.name applicant,a.email,v.title FROM applications ap JOIN accounts a ON a.id=ap.user_id JOIN vacancies v ON v.id=ap.vacancy_id WHERE v.director_id=?',(u['user_id'],)).fetchall()]);return
    if p=='/api/admin/directors':self.auth(c,True);self.send(200,[pack(r) for r in c.execute("SELECT id,name,email,company,location,approved FROM accounts WHERE role='director'").fetchall()]);return
    if p=='/api/admin/users':self.auth(c,True);self.send(200,[pack(r) for r in c.execute("SELECT id,name,email,role,company,location,approved FROM accounts ORDER BY id DESC").fetchall()]);return
    if p=='/api/admin/report':self.auth(c,True);self.send(200,{'vacancies':c.execute('SELECT COUNT(*) n FROM vacancies').fetchone()['n'],'applications':c.execute('SELECT COUNT(*) n FROM applications').fetchone()['n'],'applicants':c.execute("SELECT COUNT(*) n FROM accounts WHERE role='applicant'").fetchone()['n']});return
    self.send(404,{'error':'Not found'})
   except PermissionError as e:self.send(401,{'error':str(e)})
 def do_POST(self):
  p=urlparse(self.path).path
  try:d=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))) or b'{}')
  except:self.send(400,{'error':'Invalid request.'});return
  with db() as c:
   try:
    if p=='/api/register':
     role=d.get('role','applicant');email=d.get('email','').lower().strip();
     if role not in('applicant','director') or not d.get('name') or '@' not in email or len(d.get('password',''))<8:self.send(400,{'error':'Complete the registration details. Password must have at least 8 characters.'});return
     try:c.execute('INSERT INTO accounts(name,email,password,role,company,location,approved) VALUES(?,?,?,?,?,?,?)',(d['name'],email,hashlib.sha256(d['password'].encode()).hexdigest(),role,d.get('company',''),d.get('location',''),0 if role=='director' else 1))
     except sqlite3.IntegrityError:self.send(409,{'error':'Email is already registered.'});return
     self.send(201,{'ok':True,'message':'Director profiles wait for admin approval.' if role=='director' else 'Account created.'});return
    if p=='/api/login':
     email=d.get('email','').lower().strip();admin=bool(d.get('admin'));table='accounts';u=c.execute('SELECT * FROM accounts WHERE email=? AND password=?',(email,hashlib.sha256(d.get('password','').encode()).hexdigest())).fetchone()
     if not u or (admin and u['role']!='admin') or (not admin and u['role']=='admin'):self.send(401,{'error':'Email or password not recognized.'});return
     if u['role']=='director' and not u['approved']:self.send(403,{'error':'Director registration is awaiting administrator approval.'});return
     t=secrets.token_urlsafe(32);c.execute('INSERT INTO sessions(token,user_id,admin,expires) VALUES(?,?,?,?)',(t,u['id'],1 if admin else 0,int(time.time())+86400));self.send(200,{'token':t,'user':{'name':u['name'],'email':u['email'],'role':u['role']}});return
    if p=='/api/logout':c.execute('DELETE FROM sessions WHERE token=?',(self.headers.get('Authorization','').replace('Bearer ',''),));self.send(200,{'ok':True});return
    if p=='/api/apply':
     u=self.auth(c,role='applicant');c.execute('INSERT INTO applications(user_id,vacancy_id,resume,privacy) VALUES(?,?,?,?)',(u['user_id'],d.get('vacancy_id'),d.get('resume',''),d.get('privacy','All companies')));self.send(201,{'ok':True});return
    if p=='/api/save':
     u=self.auth(c,role='applicant');c.execute('INSERT OR IGNORE INTO saved_jobs VALUES(?,?)',(u['user_id'],d.get('vacancy_id')));self.send(200,{'ok':True});return
    if p=='/api/director/vacancies':
     u=self.auth(c,role='director');c.execute('INSERT INTO vacancies(director_id,title,category,location,description,contact,image) VALUES(?,?,?,?,?,?,?)',(u['user_id'],d.get('title',''),d.get('category',''),d.get('location',''),d.get('description',''),d.get('contact',''),d.get('image','')));self.send(201,{'ok':True});return
    if p.startswith('/api/director/applications/'):
     u=self.auth(c,role='director');aid=int(p.rsplit('/',1)[-1]);status=d.get('status','Reviewed');c.execute('UPDATE applications SET status=? WHERE id=? AND vacancy_id IN(SELECT id FROM vacancies WHERE director_id=?)',(status,aid,u['user_id']));self.send(200,{'ok':True});return
    if p.startswith('/api/admin/directors/'):
     self.auth(c,True);aid=int(p.rsplit('/',1)[-1]);c.execute('UPDATE accounts SET approved=? WHERE id=? AND role="director"',(1 if d.get('approved') else 0,aid));self.send(200,{'ok':True});return
    self.send(404,{'error':'Not found'})
   except sqlite3.IntegrityError:self.send(409,{'error':'You already applied for this vacancy.'})
   except PermissionError as e:self.send(401,{'error':str(e)})
   except Exception as e:self.send(400,{'error':str(e)})
if __name__=='__main__':init();print('CareerBoard at http://localhost:8021');ThreadingHTTPServer(('127.0.0.1',8021),H).serve_forever()
