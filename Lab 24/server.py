"""Wanderlust Travels Lab 24 local demo. Run: python server.py"""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import sqlite3,json,secrets,hashlib,time,mimetypes
ROOT=Path(__file__).parent;DB=ROOT/'wanderlust.db'
def db():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c
def init():
 with db() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT,email TEXT UNIQUE,password TEXT,role TEXT DEFAULT 'traveler',created TEXT DEFAULT CURRENT_TIMESTAMP);CREATE TABLE IF NOT EXISTS destinations(id INTEGER PRIMARY KEY,name TEXT,region TEXT,description TEXT,image TEXT DEFAULT '',price REAL DEFAULT 0);CREATE TABLE IF NOT EXISTS food(id INTEGER PRIMARY KEY,name TEXT,place TEXT,region TEXT,description TEXT,price REAL);CREATE TABLE IF NOT EXISTS hotels(id INTEGER PRIMARY KEY,name TEXT,region TEXT,description TEXT,price REAL,rooms INTEGER DEFAULT 1);CREATE TABLE IF NOT EXISTS routes(id INTEGER PRIMARY KEY,name TEXT,origin TEXT,destination TEXT,duration TEXT,description TEXT,price REAL);CREATE TABLE IF NOT EXISTS bookings(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id),hotel_id INTEGER REFERENCES hotels(id),guest_name TEXT,guests INTEGER,checkin TEXT,checkout TEXT,contact TEXT,total REAL,status TEXT DEFAULT 'Confirmed',created TEXT DEFAULT CURRENT_TIMESTAMP);CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER,admin INTEGER DEFAULT 0,expires INTEGER);''')
  if not c.execute('SELECT id FROM users WHERE role="admin"').fetchone():c.execute('INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)',('Wanderlust Admin','admin@wanderlust.test',hashlib.sha256(b'wander123').hexdigest(),'admin'))
  if not c.execute('SELECT id FROM users WHERE role="traveler"').fetchone():c.execute('INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)',('Jamie Traveler','traveler@wanderlust.test',hashlib.sha256(b'trip12345').hexdigest(),'traveler'))
  if not c.execute('SELECT id FROM destinations LIMIT 1').fetchone():
   for x in [('Kyoto, Japan','East Asia','Quiet lanes, temple gardens, and a wonderful food culture.','⛩',520),('Lisbon, Portugal','Europe','Hillside views, tiled streets, and sunlit coastal day trips.','🌅',430),('Marrakech, Morocco','North Africa','Colorful markets, courtyard stays, and desert adventures.','🕌',390),('Vancouver, Canada','North America','Ocean air, mountain paths, and a lively waterfront.','🏔',480)]:c.execute('INSERT INTO destinations(name,region,description,image,price) VALUES(?,?,?,?,?)',x)
   for x in [('Cedar House Kyoto','Kyoto','A calm garden guesthouse near the old town.',118,12),('Blue Door Lisbon','Lisbon','A bright boutique stay close to the tram and cafés.',96,18),('Atlas Courtyard','Marrakech','A traditional riad with a quiet courtyard pool.',84,9),('Harborlight Inn','Vancouver','Easy access to the seawall and downtown.',142,22)]:c.execute('INSERT INTO hotels(name,region,description,price,rooms) VALUES(?,?,?,?,?)',x)
   for x in [('Market breakfast','Kyoto','Kyoto','Seasonal breakfast with local market ingredients.',18),('Pastel tasting walk','Lisbon','Lisbon','A guided stroll through neighborhood bakeries.',26),('Spice table supper','Marrakech','Marrakech','Home-style supper with a local host.',31)]:c.execute('INSERT INTO food(name,place,region,description,price) VALUES(?,?,?,?,?)',x)
   for x in [('Old town & temple loop','Kyoto','Kyoto East','5 hours','A gentle route through gardens, shrines, and back streets.',44),('River and hill tram','Lisbon','Belém','4 hours','A scenic day along the river and historic neighborhoods.',38),('Atlas foothills','Marrakech','Ourika Valley','Full day','A guided drive out to the foothill villages.',78)]:c.execute('INSERT INTO routes(name,origin,destination,duration,description,price) VALUES(?,?,?,?,?,?)',x)
class H(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def send(self,s,d):
  b=json.dumps(d).encode();self.send_response(s);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.send_header('Access-Control-Allow-Origin','*');self.end_headers();self.wfile.write(b)
 def auth(self,c,admin=False):
  t=self.headers.get('Authorization','').replace('Bearer ','');r=c.execute('SELECT s.admin,s.user_id,u.name,u.email,u.role FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>?',(t,int(time.time()))).fetchone()
  if not r:raise PermissionError('Please sign in to continue.')
  if admin and not r['admin']:raise PermissionError('Administrator access required.')
  return r
 def do_OPTIONS(self):self.send_response(204);self.send_header('Access-Control-Allow-Origin','*');self.send_header('Access-Control-Allow-Headers','Authorization, Content-Type');self.send_header('Access-Control-Allow-Methods','GET,POST,PUT,OPTIONS');self.end_headers()
 def do_GET(self):
  p=urlparse(self.path).path
  if p=='/' or p=='/index.html':
   b=(ROOT/'index.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
  if p in('/styles.css','/script.js'):
   b=(ROOT/p[1:]).read_bytes();self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(p)[0] or 'text/plain');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
  with db() as c:
   try:
    paths={'/api/destinations':'destinations','/api/food':'food','/api/hotels':'hotels','/api/routes':'routes'}
    if p in paths:self.send(200,[dict(r) for r in c.execute('SELECT * FROM '+paths[p]).fetchall()]);return
    u=self.auth(c)
    if p=='/api/me':self.send(200,{k:u[k] for k in('name','email','role')});return
    if p=='/api/bookings':
     sql='SELECT b.*,h.name hotel,h.region FROM bookings b JOIN hotels h ON h.id=b.hotel_id';args=[]
     if not u['admin']:sql+=' WHERE b.user_id=?';args=[u['user_id']]
     self.send(200,[dict(x) for x in c.execute(sql+' ORDER BY b.id DESC',args).fetchall()]);return
    self.send(404,{'error':'Not found'})
   except PermissionError as e:self.send(401,{'error':str(e)})
 def do_POST(self):
  p=urlparse(self.path).path
  try:d=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))) or b'{}')
  except:self.send(400,{'error':'Invalid request.'});return
  with db() as c:
   try:
    if p=='/api/register':
     email=d.get('email','').lower().strip()
     if '@' not in email or len(d.get('password',''))<8:self.send(400,{'error':'Provide a valid email and password of at least 8 characters.'});return
     c.execute('INSERT INTO users(name,email,password) VALUES(?,?,?)',(d.get('name',''),email,hashlib.sha256(d['password'].encode()).hexdigest()));self.send(201,{'ok':True});return
    if p=='/api/login':
     u=c.execute('SELECT * FROM users WHERE email=? AND password=?',(d.get('email','').lower().strip(),hashlib.sha256(d.get('password','').encode()).hexdigest())).fetchone()
     if not u or bool(d.get('admin'))!=(u['role']=='admin'):self.send(401,{'error':'Login details not recognized.'});return
     t=secrets.token_urlsafe(32);c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(t,u['id'],int(u['role']=='admin'),int(time.time())+86400));self.send(200,{'token':t,'user':{'name':u['name'],'email':u['email'],'role':u['role']}});return
    if p=='/api/logout':c.execute('DELETE FROM sessions WHERE token=?',(self.headers.get('Authorization','').replace('Bearer ',''),));self.send(200,{'ok':True});return
    if p=='/api/bookings':
     u=self.auth(c);hid=int(d.get('hotel_id',0));h=c.execute('SELECT * FROM hotels WHERE id=?',(hid,)).fetchone()
     if not h:self.send(404,{'error':'Choose a listed hotel.'});return
     checkin=__import__('datetime').date.fromisoformat(d.get('checkin'));checkout=__import__('datetime').date.fromisoformat(d.get('checkout'));days=(checkout-checkin).days
     if days<1 or days>90:self.send(400,{'error':'Choose a check-out date after check-in, up to 90 nights.'});return
     if not 1<=int(d.get('guests',1))<=h['rooms']*4:self.send(400,{'error':'Guest count exceeds the available room capacity.'});return
     if not d.get('guest_name') or not d.get('contact'):self.send(400,{'error':'Add guest name and contact details.'});return
     total=days*h['price']*int(d.get('guests',1));c.execute('INSERT INTO bookings(user_id,hotel_id,guest_name,guests,checkin,checkout,contact,total) VALUES(?,?,?,?,?,?,?,?)',(u['user_id'],hid,d.get('guest_name'),int(d.get('guests',1)),d.get('checkin'),d.get('checkout'),d.get('contact'),total));self.send(201,{'ok':True,'total':total});return
    if p=='/api/admin/destinations':
     self.auth(c,True);c.execute('INSERT INTO destinations(name,region,description,image,price) VALUES(?,?,?,?,?)',(d.get('name',''),d.get('region',''),d.get('description',''),d.get('image','✈'),float(d.get('price',0))));self.send(201,{'ok':True});return
    if p=='/api/admin/food':
     self.auth(c,True);c.execute('INSERT INTO food(name,place,region,description,price) VALUES(?,?,?,?,?)',(d.get('name',''),d.get('place',''),d.get('region',''),d.get('description',''),float(d.get('price',0))));self.send(201,{'ok':True});return
    if p=='/api/admin/hotels':
     self.auth(c,True);c.execute('INSERT INTO hotels(name,region,description,price,rooms) VALUES(?,?,?,?,?)',(d.get('name',''),d.get('region',''),d.get('description',''),float(d.get('price',0)),int(d.get('rooms',1))));self.send(201,{'ok':True});return
    if p=='/api/admin/routes':
     self.auth(c,True);c.execute('INSERT INTO routes(name,origin,destination,duration,description,price) VALUES(?,?,?,?,?,?)',(d.get('name',''),d.get('origin',''),d.get('destination',''),d.get('duration',''),d.get('description',''),float(d.get('price',0))));self.send(201,{'ok':True});return
    self.send(404,{'error':'Not found'})
   except sqlite3.IntegrityError:self.send(409,{'error':'That email is already registered.'})
   except PermissionError as e:self.send(401,{'error':str(e)})
   except Exception as e:self.send(400,{'error':str(e)})
 def do_PUT(self):
  p=urlparse(self.path).path
  try:d=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))) or b'{}')
  except:self.send(400,{'error':'Invalid request.'});return
  with db() as c:
   try:self.auth(c,True);c.execute('UPDATE bookings SET status=? WHERE id=?',(d.get('status','Confirmed'),int(p.rsplit('/',1)[-1])));self.send(200,{'ok':True})
   except PermissionError as e:self.send(401,{'error':str(e)})
   except Exception as e:self.send(400,{'error':str(e)})
if __name__=='__main__':init();print('Wanderlust at http://localhost:8024');ThreadingHTTPServer(('127.0.0.1',8024),H).serve_forever()
