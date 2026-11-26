"""RentRide Lab 20 classroom rental prototype. Run: python server.py"""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs
import sqlite3,json,secrets,hashlib,time,mimetypes

ROOT=Path(__file__).parent;DB=ROOT/'rentride.db'
def db():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c
def init():
 with db() as c:
  c.executescript('''
  CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,password TEXT NOT NULL,phone TEXT DEFAULT '',address TEXT DEFAULT '',created TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY,email TEXT UNIQUE NOT NULL,password TEXT NOT NULL,name TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS vehicles(id INTEGER PRIMARY KEY,name TEXT NOT NULL,brand TEXT NOT NULL,type TEXT NOT NULL,location TEXT NOT NULL,description TEXT NOT NULL,price_day REAL NOT NULL,seats INTEGER NOT NULL,transmission TEXT NOT NULL,fuel TEXT NOT NULL,image TEXT DEFAULT '',available INTEGER DEFAULT 1,created TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS bookings(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),vehicle_id INTEGER NOT NULL REFERENCES vehicles(id),start_date TEXT NOT NULL,end_date TEXT NOT NULL,pickup_time TEXT NOT NULL,pickup_address TEXT NOT NULL,customer_phone TEXT NOT NULL,checkin_note TEXT DEFAULT '',payment_method TEXT NOT NULL,total REAL NOT NULL,status TEXT NOT NULL DEFAULT 'Pending',created TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),vehicle_id INTEGER NOT NULL REFERENCES vehicles(id),booking_id INTEGER NOT NULL UNIQUE REFERENCES bookings(id),rating INTEGER NOT NULL,message TEXT NOT NULL,created TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER,admin_id INTEGER,expires INTEGER NOT NULL);
  ''')
  if not c.execute('SELECT id FROM admins LIMIT 1').fetchone():c.execute('INSERT INTO admins(email,password,name) VALUES(?,?,?)',('admin@rentride.test',hashlib.sha256(b'rentride123').hexdigest(),'RentRide Admin'))
  if not c.execute('SELECT id FROM vehicles LIMIT 1').fetchone():
   cars=[('City Bloom','Honda','Compact','Downtown','Easy to park and comfortable for weekend city trips.',48,5,'Automatic','Hybrid','🚗'),('Trail Ready','Toyota','SUV','Northside','Roomy SUV with space for the whole crew and their bags.',82,7,'Automatic','Petrol','🚙'),('Cargo Buddy','Ford','Truck','West End','A dependable pickup for projects, moves, and long weekends.',76,3,'Automatic','Petrol','🛻'),('Open Road','Volkswagen','Sedan','Downtown','A smooth, fuel-friendly ride for the road ahead.',59,5,'Automatic','Diesel','🚘'),('Weekend Wanderer','Jeep','SUV','Riverside','Take the scenic route in this capable all-wheel drive.',95,5,'Automatic','Petrol','🚙'),('Little Sprinter','Nissan','Compact','East Market','A nimble, practical city car with great mileage.',42,5,'Manual','Petrol','🚗')]
   for x in cars:c.execute('INSERT INTO vehicles(name,brand,type,location,description,price_day,seats,transmission,fuel,image) VALUES(?,?,?,?,?,?,?,?,?,?)',x)
def row(r):return dict(r) if r else None
class H(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def send(self,s,d):
  b=json.dumps(d).encode();self.send_response(s);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.send_header('Access-Control-Allow-Origin','*');self.end_headers();self.wfile.write(b)
 def body(self):return json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))) or b'{}')
 def auth(self,c,admin=False):
  t=self.headers.get('Authorization','').replace('Bearer ','');r=c.execute('SELECT s.*,u.name user_name,u.email user_email,a.name admin_name,a.email admin_email FROM sessions s LEFT JOIN users u ON u.id=s.user_id LEFT JOIN admins a ON a.id=s.admin_id WHERE s.token=? AND s.expires>?',(t,int(time.time()))).fetchone()
  if not r:raise PermissionError('Please sign in to continue.')
  if admin and not r['admin_id']:raise PermissionError('Admin access is required.')
  if not admin and not r['user_id']:raise PermissionError('Please sign in with a customer account.')
  return r
 def do_OPTIONS(self):self.send_response(204);self.send_header('Access-Control-Allow-Origin','*');self.send_header('Access-Control-Allow-Headers','Authorization, Content-Type');self.send_header('Access-Control-Allow-Methods','GET, POST, PUT, DELETE, OPTIONS');self.end_headers()
 def do_GET(self):
  p=urlparse(self.path).path;q=parse_qs(urlparse(self.path).query)
  if p=='/' or p=='/index.html':
   b=(ROOT/'index.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
  if p in('/styles.css','/script.js'):
   b=(ROOT/p[1:]).read_bytes();self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(p)[0] or 'text/plain');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
  with db() as c:
   try:
    if p=='/api/vehicles':
     sql='SELECT v.*,ROUND(AVG(r.rating),1) rating,COUNT(r.id) review_count FROM vehicles v LEFT JOIN reviews r ON r.vehicle_id=v.id WHERE v.available=1';args=[]
     term=q.get('q',[''])[0].strip()
     if term:sql+=' AND (v.name LIKE ? OR v.brand LIKE ? OR v.description LIKE ? OR v.location LIKE ?)';args += [f'%{term}%']*4
     typ=q.get('type',['All'])[0];loc=q.get('location',['All'])[0]
     if typ!='All':sql+=' AND v.type=?';args.append(typ)
     if loc!='All':sql+=' AND v.location=?';args.append(loc)
     start=q.get('start',[''])[0];end=q.get('end',[''])[0]
     if start and end:sql+=' AND NOT EXISTS(SELECT 1 FROM bookings b WHERE b.vehicle_id=v.id AND b.status NOT IN ("Declined","Cancelled") AND b.start_date<=? AND b.end_date>=?)';args += [end,start]
     sql+=' GROUP BY v.id ORDER BY v.id';self.send(200,[dict(x) for x in c.execute(sql,args).fetchall()]);return
    if p=='/api/meta':
     self.send(200,{'locations':[x['location'] for x in c.execute('SELECT DISTINCT location FROM vehicles ORDER BY location').fetchall()]});return
    if p=='/api/me':
     u=self.auth(c);isadmin=bool(u['admin_id']);profile=c.execute('SELECT phone,address FROM users WHERE id=?',(u['user_id'],)).fetchone() if not isadmin else None;self.send(200,{'id':u['admin_id'] if isadmin else u['user_id'],'name':u['admin_name'] if isadmin else u['user_name'],'email':u['admin_email'] if isadmin else u['user_email'],'role':'admin' if isadmin else 'customer','phone':profile['phone'] if profile else '','address':profile['address'] if profile else ''});return
    if p in('/api/bookings','/api/admin/bookings','/api/admin/vehicles','/api/admin/reviews'):
     if p=='/api/bookings':u=self.auth(c);out=c.execute('SELECT b.*,v.name vehicle,v.brand,v.image,v.location FROM bookings b JOIN vehicles v ON v.id=b.vehicle_id WHERE b.user_id=? ORDER BY b.id DESC',(u['user_id'],)).fetchall()
     elif p=='/api/admin/bookings':self.auth(c,True);out=c.execute('SELECT b.*,v.name vehicle,v.brand,v.image,u.name customer,u.email,u.phone FROM bookings b JOIN vehicles v ON v.id=b.vehicle_id JOIN users u ON u.id=b.user_id ORDER BY b.id DESC').fetchall()
     elif p=='/api/admin/vehicles':self.auth(c,True);out=c.execute('SELECT * FROM vehicles ORDER BY id DESC').fetchall()
     else:self.auth(c,True);out=c.execute('SELECT r.*,u.name customer,v.name vehicle FROM reviews r JOIN users u ON u.id=r.user_id JOIN vehicles v ON v.id=r.vehicle_id ORDER BY r.id DESC').fetchall()
     self.send(200,[dict(x) for x in out]);return
    self.send(404,{'error':'Not found'})
   except PermissionError as e:self.send(401,{'error':str(e)})
 def do_POST(self):
  p=urlparse(self.path).path
  try:d=self.body()
  except:self.send(400,{'error':'Invalid request body.'});return
  with db() as c:
   try:
    if p=='/api/register':
     email=d.get('email','').strip().lower();pw=d.get('password','');name=d.get('name','').strip()
     if not name or '@' not in email or len(pw)<8:self.send(400,{'error':'Enter your name, valid email, and a password of at least 8 characters.'});return
     try:c.execute('INSERT INTO users(name,email,password,phone,address) VALUES(?,?,?,?,?)',(name,email,hashlib.sha256(pw.encode()).hexdigest(),d.get('phone',''),d.get('address','')))
     except sqlite3.IntegrityError:self.send(409,{'error':'That email already has an account.'});return
     self.send(201,{'ok':True});return
    if p in('/api/login','/api/admin/login'):
     admin=p.endswith('/admin/login');table='admins' if admin else 'users';u=c.execute(f'SELECT * FROM {table} WHERE email=? AND password=?',(d.get('email','').strip().lower(),hashlib.sha256(d.get('password','').encode()).hexdigest())).fetchone()
     if not u:self.send(401,{'error':'Email or password was not recognized.'});return
     t=secrets.token_urlsafe(32);c.execute('INSERT INTO sessions(token,user_id,admin_id,expires) VALUES(?,?,?,?)',(t,None if admin else u['id'],u['id'] if admin else None,int(time.time())+86400));self.send(200,{'token':t,'user':{'id':u['id'],'name':u['name'],'email':u['email'],'role':'admin' if admin else 'customer'}});return
    if p=='/api/logout':c.execute('DELETE FROM sessions WHERE token=?',(self.headers.get('Authorization','').replace('Bearer ',''),));self.send(200,{'ok':True});return
    if p=='/api/bookings':
     u=self.auth(c);vid=int(d.get('vehicle_id',0));v=c.execute('SELECT * FROM vehicles WHERE id=? AND available=1',(vid,)).fetchone();start=d.get('start_date','');end=d.get('end_date','')
     if not v:self.send(404,{'error':'Vehicle is unavailable.'});return
     if not start or not end or end<start:self.send(400,{'error':'Choose a valid pickup and return date.'});return
     conflict=c.execute('SELECT id FROM bookings WHERE vehicle_id=? AND status NOT IN("Declined","Cancelled") AND start_date<=? AND end_date>=?',(vid,end,start)).fetchone()
     if conflict:self.send(409,{'error':'Those dates are already requested. Please select other dates.'});return
     days=(__import__('datetime').date.fromisoformat(end)-__import__('datetime').date.fromisoformat(start)).days+1
     if days<1 or days>60:self.send(400,{'error':'Choose a rental period from 1 to 60 days.'});return
     phone=d.get('customer_phone') or '';addr=d.get('pickup_address','').strip()
     if not phone or not addr:self.send(400,{'error':'Add a contact number and pickup address.'});return
     total=days*v['price_day'];bid=c.execute('INSERT INTO bookings(user_id,vehicle_id,start_date,end_date,pickup_time,pickup_address,customer_phone,checkin_note,payment_method,total) VALUES(?,?,?,?,?,?,?,?,?,?)',(u['user_id'],vid,start,end,d.get('pickup_time','09:00'),addr,phone,d.get('checkin_note',''),d.get('payment_method','Pay at pickup'),total)).lastrowid
     self.send(201,{'id':bid,'total':total,'days':days});return
    if p=='/api/reviews':
     u=self.auth(c);bid=int(d.get('booking_id',0));b=c.execute('SELECT * FROM bookings WHERE id=? AND user_id=? AND status IN("Returned","Completed")',(bid,u['user_id'])).fetchone()
     if not b:self.send(400,{'error':'Only completed rentals can be reviewed.'});return
     try:c.execute('INSERT INTO reviews(user_id,vehicle_id,booking_id,rating,message) VALUES(?,?,?,?,?)',(u['user_id'],b['vehicle_id'],bid,max(1,min(5,int(d.get('rating',5)))),d.get('message','')))
     except sqlite3.IntegrityError:self.send(409,{'error':'This booking already has a review.'});return
     self.send(201,{'ok':True});return
    if p=='/api/admin/vehicles':
     self.auth(c,True);self.vehicle(c,d);return
    if p=='/api/admin/bookings':
     self.auth(c,True);bid=int(d.get('id',0));status=d.get('status');
     if status not in('Approved','Declined','Checked in','Returned','Completed'):self.send(400,{'error':'Select a valid booking status.'});return
     c.execute('UPDATE bookings SET status=? WHERE id=?',(status,bid));self.send(200,{'ok':True});return
    self.send(404,{'error':'Not found'})
   except PermissionError as e:self.send(401,{'error':str(e)})
   except Exception as e:self.send(400,{'error':str(e)})
 def do_PUT(self):
  p=urlparse(self.path).path
  try:d=self.body()
  except:self.send(400,{'error':'Invalid request body.'});return
  with db() as c:
   try:
    if p=='/api/profile':
     u=self.auth(c);c.execute('UPDATE users SET name=?,phone=?,address=? WHERE id=?',(d.get('name','').strip(),d.get('phone',''),d.get('address',''),u['user_id']));self.send(200,{'ok':True});return
    self.auth(c,True)
    if p.startswith('/api/admin/vehicles/'):self.vehicle(c,d,int(p.rsplit('/',1)[-1]));return
    self.send(404,{'error':'Not found'})
   except PermissionError as e:self.send(401,{'error':str(e)})
   except Exception as e:self.send(400,{'error':str(e)})
 def do_DELETE(self):
  p=urlparse(self.path).path
  with db() as c:
   try:
    self.auth(c,True)
    if p.startswith('/api/admin/vehicles/'):
     vid=int(p.rsplit('/',1)[-1]);used=c.execute('SELECT id FROM bookings WHERE vehicle_id=? LIMIT 1',(vid,)).fetchone()
     if used:c.execute('UPDATE vehicles SET available=0 WHERE id=?',(vid,))
     else:c.execute('DELETE FROM vehicles WHERE id=?',(vid,))
     self.send(200,{'ok':True});return
    self.send(404,{'error':'Not found'})
   except PermissionError as e:self.send(401,{'error':str(e)})
   except Exception as e:self.send(400,{'error':str(e)})
 def vehicle(self,c,d,vid=None):
  name=d.get('name','').strip();brand=d.get('brand','').strip();typ=d.get('type','Car');location=d.get('location','').strip();desc=d.get('description','').strip();price=float(d.get('price_day',0));seats=int(d.get('seats',5));trans=d.get('transmission','Automatic');fuel=d.get('fuel','Petrol');image=d.get('image','')
  if not name or not brand or not location or not desc or price<=0:self.send(400,{'error':'Complete vehicle details and set a daily price above zero.'});return
  if image.startswith('data:') and len(image)>1800000:self.send(400,{'error':'Vehicle image is too large. Choose an image under 1.3 MB.'});return
  if vid:c.execute('UPDATE vehicles SET name=?,brand=?,type=?,location=?,description=?,price_day=?,seats=?,transmission=?,fuel=?,image=? WHERE id=?',(name,brand,typ,location,desc,price,seats,trans,fuel,image,vid))
  else:c.execute('INSERT INTO vehicles(name,brand,type,location,description,price_day,seats,transmission,fuel,image) VALUES(?,?,?,?,?,?,?,?,?,?)',(name,brand,typ,location,desc,price,seats,trans,fuel,image))
  self.send(200,{'ok':True})
if __name__=='__main__':init();print('RentRide running at http://localhost:8010');ThreadingHTTPServer(('127.0.0.1',8010),H).serve_forever()
