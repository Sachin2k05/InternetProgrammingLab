"""VetCure Lab 19 local classroom prototype. Run: python server.py"""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import sqlite3,json,secrets,hashlib,time,mimetypes

ROOT=Path(__file__).parent; DB=ROOT/'vetcure.db'
def db():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c
def init():
 with db() as c:
  c.executescript('''
  CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,password TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN('farmer','doctor')),phone TEXT DEFAULT '',area TEXT DEFAULT '',created TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS doctors(user_id INTEGER PRIMARY KEY REFERENCES users(id),clinic TEXT NOT NULL,clinic_type TEXT NOT NULL CHECK(clinic_type IN('Government','Private')),specialty TEXT DEFAULT 'General veterinary care',fee REAL DEFAULT 0,bank TEXT DEFAULT '',easypaisa TEXT DEFAULT '',bio TEXT DEFAULT '',available INTEGER DEFAULT 1);
  CREATE TABLE IF NOT EXISTS subscriptions(id INTEGER PRIMARY KEY,farmer_id INTEGER NOT NULL REFERENCES users(id),doctor_id INTEGER NOT NULL REFERENCES users(id),status TEXT NOT NULL DEFAULT 'Pending',amount REAL NOT NULL DEFAULT 0,created TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(farmer_id,doctor_id));
  CREATE TABLE IF NOT EXISTS complaints(id INTEGER PRIMARY KEY,farmer_id INTEGER NOT NULL REFERENCES users(id),doctor_id INTEGER NOT NULL REFERENCES users(id),animal TEXT NOT NULL,animal_type TEXT NOT NULL,disease TEXT DEFAULT 'Unspecified',symptoms TEXT NOT NULL,media_kind TEXT DEFAULT '',media_name TEXT DEFAULT '',media_data TEXT DEFAULT '',status TEXT DEFAULT 'Submitted',created TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS responses(id INTEGER PRIMARY KEY,complaint_id INTEGER NOT NULL REFERENCES complaints(id),doctor_id INTEGER NOT NULL REFERENCES users(id),message TEXT NOT NULL,prescription TEXT DEFAULT '',created TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY,subscription_id INTEGER NOT NULL REFERENCES subscriptions(id),farmer_id INTEGER NOT NULL REFERENCES users(id),doctor_id INTEGER NOT NULL REFERENCES users(id),method TEXT NOT NULL,reference TEXT DEFAULT '',amount REAL NOT NULL,status TEXT DEFAULT 'Recorded',created TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS cures(id INTEGER PRIMARY KEY,doctor_id INTEGER NOT NULL REFERENCES users(id),title TEXT NOT NULL,animal_type TEXT NOT NULL,disease TEXT NOT NULL,description TEXT NOT NULL,prescription TEXT NOT NULL,image TEXT DEFAULT '',created TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS news(id INTEGER PRIMARY KEY,doctor_id INTEGER NOT NULL REFERENCES users(id),title TEXT NOT NULL,body TEXT NOT NULL,created TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY,farmer_id INTEGER NOT NULL REFERENCES users(id),doctor_id INTEGER REFERENCES users(id),rating INTEGER NOT NULL,message TEXT NOT NULL,created TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),expires INTEGER NOT NULL);
  ''')
  seed=[('Dr. Amina Shah','amina@govvet.test','govvet123','555-0201','North Valley','North Valley Government Veterinary Hospital','Government','Large animal health',0,'Government veterinary clinic','Govt. CVH, North Valley','0300-1112233','Experienced veterinarian supporting livestock and companion animals.'),('Dr. Omar Farooq','omar@privatevet.test','clinic12345','555-0202','Riverbend','Riverbend Animal Care','Private','Pet and livestock care',850,'Riverbend Animal Care, Riverbend','Bank account ending 8241','0300-7654321','Private clinic providing consultations by appointment.'),('Dr. Sara Khan','sara@govvet.test','govvet123','555-0203','East Farm','East Farm Government CVH','Government','Preventive animal care',0,'East Farm Government CVH','Govt. CVH, East Farm','0300-1113344','Community veterinary services and animal health guidance.')]
  for n,e,p,ph,a,cl,ct,sp,fee,bio,bank,ep,desc in seed:
   if not c.execute('SELECT id FROM users WHERE email=?',(e,)).fetchone():
    uid=c.execute('INSERT INTO users(name,email,password,role,phone,area) VALUES(?,?,?,?,?,?)',(n,e,hashlib.sha256(p.encode()).hexdigest(),'doctor',ph,a)).lastrowid
    c.execute('INSERT INTO doctors(user_id,clinic,clinic_type,specialty,fee,bank,easypaisa,bio) VALUES(?,?,?,?,?,?,?,?)',(uid,cl,ct,sp,fee,bank,ep,desc))
  if not c.execute('SELECT id FROM cures LIMIT 1').fetchone():
   did=c.execute('SELECT id FROM users WHERE email=?',('amina@govvet.test',)).fetchone()['id']
   c.execute('INSERT INTO cures(doctor_id,title,animal_type,disease,description,prescription) VALUES(?,?,?,?,?,?)',(did,'Recognizing seasonal tick fever','Cattle','Tick-borne illness','Common signs may include fever, reduced appetite, weakness, or pale gums. A veterinary examination is needed to identify the cause.','Keep the animal comfortable and contact a qualified veterinarian promptly. Medication and dosage must be determined by a veterinarian.'))
   c.execute('INSERT INTO news(doctor_id,title,body) VALUES(?,?,?)',(did,'Seasonal animal health checks','Check animals regularly for changes in appetite, activity, temperature, and skin. Contact your local veterinary clinic for advice if you notice concerning signs.'))
  if not c.execute('SELECT id FROM users WHERE email=?',('farmer@vetcure.test',)).fetchone():c.execute('INSERT INTO users(name,email,password,role,phone,area) VALUES(?,?,?,?,?,?)',('Ravi Patel','farmer@vetcure.test',hashlib.sha256(b'farm12345').hexdigest(),'farmer','555-0200','North Valley'))
def obj(r):return dict(r) if r else None
class H(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def send(self,s,x):
  b=json.dumps(x).encode();self.send_response(s);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.send_header('Access-Control-Allow-Origin','*');self.end_headers();self.wfile.write(b)
 def do_OPTIONS(self):self.send_response(204);self.send_header('Access-Control-Allow-Origin','*');self.send_header('Access-Control-Allow-Headers','Authorization, Content-Type');self.send_header('Access-Control-Allow-Methods','GET, POST, PUT, OPTIONS');self.end_headers()
 def auth(self,c,role=None):
  t=self.headers.get('Authorization','').replace('Bearer ','');u=c.execute('SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>?',(t,int(time.time()))).fetchone()
  if not u:raise PermissionError('Please sign in to continue.')
  if role and u['role']!=role:raise PermissionError('This page is for '+role+' accounts.')
  return u
 def do_GET(self):
  p=urlparse(self.path).path
  if p=='/' or p=='/index.html':
   b=(ROOT/'index.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
  if p in('/styles.css','/script.js'):
   b=(ROOT/p[1:]).read_bytes();self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(p)[0] or 'text/plain');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
  with db() as c:
   try:
    if p=='/api/doctors':self.send(200,[dict(r) for r in c.execute('SELECT u.id,u.name,u.area,d.clinic,d.clinic_type,d.specialty,d.fee,d.bank,d.easypaisa,d.bio FROM doctors d JOIN users u ON u.id=d.user_id WHERE d.available=1').fetchall()]);return
    if p=='/api/cures':self.send(200,[dict(r) for r in c.execute('SELECT c.*,u.name doctor FROM cures c JOIN users u ON u.id=c.doctor_id ORDER BY c.id DESC').fetchall()]);return
    if p=='/api/news':self.send(200,[dict(r) for r in c.execute('SELECT n.*,u.name doctor FROM news n JOIN users u ON u.id=n.doctor_id ORDER BY n.id DESC').fetchall()]);return
    if p=='/api/reports':self.send(200,[dict(r) for r in c.execute("SELECT area,disease,animal_type,COUNT(*) cases FROM complaints c JOIN users u ON u.id=c.farmer_id WHERE disease!='Unspecified' GROUP BY area,disease,animal_type ORDER BY cases DESC,area").fetchall()]);return
    if p=='/api/me':
     u=self.auth(c);self.send(200,{k:u[k] for k in('id','name','email','role','phone','area')});return
    if p in('/api/farmer/complaints','/api/farmer/subscriptions','/api/doctor/complaints','/api/doctor/users','/api/doctor/payments','/api/doctor/feedback'):
     u=self.auth(c,'farmer' if p.startswith('/api/farmer') else 'doctor')
     if p=='/api/farmer/complaints':q='SELECT x.*,d.name doctor,(SELECT message FROM responses r WHERE r.complaint_id=x.id ORDER BY id DESC LIMIT 1) response,(SELECT prescription FROM responses r WHERE r.complaint_id=x.id ORDER BY id DESC LIMIT 1) prescription FROM complaints x JOIN users d ON d.id=x.doctor_id WHERE x.farmer_id=? ORDER BY x.id DESC';args=(u['id'],)
     elif p=='/api/farmer/subscriptions':q='SELECT s.*,d.name doctor,dr.clinic,dr.clinic_type FROM subscriptions s JOIN users d ON d.id=s.doctor_id JOIN doctors dr ON dr.user_id=d.id WHERE s.farmer_id=?';args=(u['id'],)
     elif p=='/api/doctor/complaints':q='SELECT x.*,u.name farmer,u.area,u.phone FROM complaints x JOIN users u ON u.id=x.farmer_id WHERE x.doctor_id=? ORDER BY x.id DESC';args=(u['id'],)
     elif p=='/api/doctor/users':q='SELECT DISTINCT u.id,u.name,u.email,u.phone,u.area,u.created FROM users u JOIN subscriptions s ON s.farmer_id=u.id WHERE s.doctor_id=? AND s.status="Active" AND u.role="farmer"';args=(u['id'],)
     elif p=='/api/doctor/payments':q='SELECT p.*,u.name farmer FROM payments p JOIN users u ON u.id=p.farmer_id WHERE p.doctor_id=? ORDER BY p.id DESC';args=(u['id'],)
     else:q='SELECT f.*,u.name farmer FROM feedback f JOIN users u ON u.id=f.farmer_id WHERE f.doctor_id=? ORDER BY f.id DESC';args=(u['id'],)
     self.send(200,[dict(r) for r in c.execute(q,args).fetchall()]);return
    self.send(404,{'error':'Not found'})
   except PermissionError as e:self.send(401,{'error':str(e)})
 def do_POST(self):
  p=urlparse(self.path).path
  try:d=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))) or b'{}')
  except:self.send(400,{'error':'Invalid request body.'});return
  with db() as c:
   try:
    if p=='/api/register':
     name=d.get('name','').strip();email=d.get('email','').strip().lower();pw=d.get('password','');role=d.get('role','farmer')
     if not name or '@' not in email or len(pw)<8 or role not in('farmer','doctor'):self.send(400,{'error':'Enter your name, a valid email, an 8-character password, and account type.'});return
     try:uid=c.execute('INSERT INTO users(name,email,password,role,phone,area) VALUES(?,?,?,?,?,?)',(name,email,hashlib.sha256(pw.encode()).hexdigest(),role,d.get('phone',''),d.get('area',''))).lastrowid
     except sqlite3.IntegrityError:self.send(409,{'error':'That email is already registered.'});return
     if role=='doctor':
      kind=d.get('clinic_type','Private');fee=0 if kind=='Government' else max(0,float(d.get('fee',0)))
      c.execute('INSERT INTO doctors(user_id,clinic,clinic_type,specialty,fee,bank,easypaisa,bio) VALUES(?,?,?,?,?,?,?,?)',(uid,d.get('clinic','Clinic'),kind,d.get('specialty','General veterinary care'),fee,d.get('bank',''),d.get('easypaisa',''),d.get('bio','')))
     self.send(201,{'ok':True});return
    if p=='/api/login':
     u=c.execute('SELECT * FROM users WHERE email=? AND password=?',(d.get('email','').strip().lower(),hashlib.sha256(d.get('password','').encode()).hexdigest())).fetchone()
     if not u:self.send(401,{'error':'Email or password was not recognized.'});return
     token=secrets.token_urlsafe(32);c.execute('INSERT INTO sessions VALUES(?,?,?)',(token,u['id'],int(time.time())+86400));self.send(200,{'token':token,'user':{k:u[k] for k in('id','name','email','role','phone','area')}});return
    if p=='/api/logout':
     c.execute('DELETE FROM sessions WHERE token=?',(self.headers.get('Authorization','').replace('Bearer ',''),));self.send(200,{'ok':True});return
    if p=='/api/farmer/subscribe':
     u=self.auth(c,'farmer');doc=c.execute('SELECT d.*,u.name FROM doctors d JOIN users u ON u.id=d.user_id WHERE d.user_id=?',(d.get('doctor_id'),)).fetchone()
     if not doc:self.send(404,{'error':'Doctor not found.'});return
     status='Active' if doc['clinic_type']=='Government' else 'Pending';
     try:sid=c.execute('INSERT INTO subscriptions(farmer_id,doctor_id,status,amount) VALUES(?,?,?,?)',(u['id'],doc['user_id'],status,doc['fee'])).lastrowid
     except sqlite3.IntegrityError:
      s=c.execute('SELECT * FROM subscriptions WHERE farmer_id=? AND doctor_id=?',(u['id'],doc['user_id'])).fetchone();self.send(409,{'error':'You already have a subscription with this doctor.','subscription_id':s['id'],'status':s['status']});return
     self.send(201,{'subscription_id':sid,'status':status,'fee':doc['fee'],'doctor':doc['name'],'bank':doc['bank'],'easypaisa':doc['easypaisa']});return
    if p=='/api/farmer/payment':
     u=self.auth(c,'farmer');sub=c.execute('SELECT * FROM subscriptions WHERE id=? AND farmer_id=?',(d.get('subscription_id'),u['id'])).fetchone()
     if not sub:self.send(404,{'error':'Subscription not found.'});return
     if sub['amount']<=0:self.send(400,{'error':'This government clinic subscription is free.'});return
     method=d.get('method');ref=d.get('reference','').strip()
     if method not in('Bank transfer','EasyPaisa') or not ref:self.send(400,{'error':'Choose a payment method and enter its reference.'});return
     c.execute('INSERT INTO payments(subscription_id,farmer_id,doctor_id,method,reference,amount) VALUES(?,?,?,?,?,?)',(sub['id'],u['id'],sub['doctor_id'],method,ref,sub['amount']));c.execute('UPDATE subscriptions SET status="Active" WHERE id=?',(sub['id'],));self.send(201,{'ok':True});return
    if p=='/api/farmer/complaints':
     u=self.auth(c,'farmer');animal=d.get('animal','').strip();symptoms=d.get('symptoms','').strip();did=int(d.get('doctor_id') or 0)
     sub=c.execute('SELECT * FROM subscriptions WHERE farmer_id=? AND doctor_id=? AND status="Active"',(u['id'],did)).fetchone()
     if not animal or not symptoms or not sub:self.send(400,{'error':'Choose a doctor with an active subscription, and describe the animal and symptoms.'});return
     media=d.get('media_data','')
     if len(media)>3500000:self.send(400,{'error':'Attachment is too large for this demo (3.5 MB maximum).'});return
     cid=c.execute('INSERT INTO complaints(farmer_id,doctor_id,animal,animal_type,disease,symptoms,media_kind,media_name,media_data) VALUES(?,?,?,?,?,?,?,?,?)',(u['id'],did,animal,d.get('animal_type','Other'),d.get('disease','Unspecified'),symptoms,d.get('media_kind',''),d.get('media_name',''),media)).lastrowid
     self.send(201,{'id':cid});return
    if p.startswith('/api/doctor/complaints/') and p.endswith('/response'):
     u=self.auth(c,'doctor');cid=int(p.split('/')[-2]);complaint=c.execute('SELECT * FROM complaints WHERE id=? AND doctor_id=?',(cid,u['id'])).fetchone()
     if not complaint:self.send(404,{'error':'Case not found.'});return
     msg=d.get('message','').strip();pres=d.get('prescription','').strip();status=d.get('status','Responded')
     if not msg:self.send(400,{'error':'Write a response before saving.'});return
     c.execute('INSERT INTO responses(complaint_id,doctor_id,message,prescription) VALUES(?,?,?,?)',(cid,u['id'],msg,pres));c.execute('UPDATE complaints SET status=? WHERE id=?',(status,cid));self.send(200,{'ok':True});return
    if p=='/api/doctor/cures':
     u=self.auth(c,'doctor');c.execute('INSERT INTO cures(doctor_id,title,animal_type,disease,description,prescription,image) VALUES(?,?,?,?,?,?,?)',(u['id'],d.get('title',''),d.get('animal_type','Other'),d.get('disease',''),d.get('description',''),d.get('prescription',''),d.get('image','')));self.send(201,{'ok':True});return
    if p=='/api/doctor/news':
     u=self.auth(c,'doctor');c.execute('INSERT INTO news(doctor_id,title,body) VALUES(?,?,?)',(u['id'],d.get('title',''),d.get('body','')));self.send(201,{'ok':True});return
    if p=='/api/farmer/feedback':
     u=self.auth(c,'farmer');rating=max(1,min(5,int(d.get('rating',5))));did=d.get('doctor_id') or None;c.execute('INSERT INTO feedback(farmer_id,doctor_id,rating,message) VALUES(?,?,?,?)',(u['id'],did,rating,d.get('message','')));self.send(201,{'ok':True});return
    self.send(404,{'error':'Not found'})
   except PermissionError as e:self.send(401,{'error':str(e)})
   except Exception as e:self.send(400,{'error':str(e)})
 def do_DELETE(self):
  p=urlparse(self.path).path
  with db() as c:
   try:
    u=self.auth(c,'doctor')
    if p.startswith('/api/doctor/cures/'):
     c.execute('DELETE FROM cures WHERE id=? AND doctor_id=?',(int(p.rsplit('/',1)[-1]),u['id']))
    elif p.startswith('/api/doctor/news/'):
     c.execute('DELETE FROM news WHERE id=? AND doctor_id=?',(int(p.rsplit('/',1)[-1]),u['id']))
    else:self.send(404,{'error':'Not found'});return
    self.send(200,{'ok':True})
   except PermissionError as e:self.send(401,{'error':str(e)})
   except Exception as e:self.send(400,{'error':str(e)})
 def do_PUT(self):
  p=urlparse(self.path).path
  try:d=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))) or b'{}')
  except:self.send(400,{'error':'Invalid request body.'});return
  with db() as c:
   try:
    u=self.auth(c,'doctor');c.execute('UPDATE doctors SET clinic=?,clinic_type=?,specialty=?,fee=?,bank=?,easypaisa=?,bio=? WHERE user_id=?',(d.get('clinic',''),d.get('clinic_type','Private'),d.get('specialty',''),float(d.get('fee',0)),d.get('bank',''),d.get('easypaisa',''),d.get('bio',''),u['id']));self.send(200,{'ok':True})
   except PermissionError as e:self.send(401,{'error':str(e)})
   except Exception as e:self.send(400,{'error':str(e)})
if __name__=='__main__':init();print('VetCure running at http://localhost:8009');ThreadingHTTPServer(('127.0.0.1',8009),H).serve_forever()
