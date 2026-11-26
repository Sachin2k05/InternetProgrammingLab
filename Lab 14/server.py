"""ReNewMarket local demo server. Start with: python server.py"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import hashlib, json, secrets, sqlite3

ROOT=Path(__file__).resolve().parent; DB=ROOT/'renewmarket.db'; PORT=8003
SEED=[
 (1,'Film camera, ready for its next roll','Electronics','Minolta X-700 · tested and working. Includes a 50mm lens and a fresh light seal.','photo-1516035069371-29a1b244cc32',165,'Very good','Portland, OR'),
 (2,'The comfiest little reading chair','Furniture','A sturdy mid-century chair with soft moss-green upholstery. A few signs of a happy life.','photo-1505693416388-ac5ce068fe85',220,'Good','Brooklyn, NY'),
 (3,'Wool coat for crisp morning walks','Clothing','A warm charcoal wool-blend coat, barely worn. Size M; relaxed fit with roomy pockets.','photo-1539533018447-63fcce2678e3',78,'Very good','Chicago, IL'),
 (4,'A lamp that makes evenings softer','Furniture','Vintage ceramic base with a linen shade. Works beautifully and includes a warm LED bulb.','photo-1507473885765-e6ed057f782c',64,'Good','Austin, TX'),
 (5,'Pocket-sized music player','Electronics','Classic portable music player in silver. Battery holds a charge; charger and earbuds included.','photo-1511379938547-c1f69419868d',48,'Like new','Seattle, WA'),
 (6,'Hand-thrown stoneware set','Collectibles','Four handmade cups with a lovely speckled glaze. Each one is a little different.','photo-1578749556568-bc2c40e68b61',52,'Very good','Denver, CO'),
 (7,'Everyday leather crossbody','Clothing','Soft tan leather with an adjustable strap and plenty of life left. Clean, conditioned, ready to go.','photo-1548036328-c9fa89d128fa',55,'Good','Brooklyn, NY'),
 (8,'A small desk with big ideas','Furniture','Compact oak writing desk with one drawer. Just right for a sunny corner or a first apartment.','photo-1497366754035-f200968a6e72',135,'Very good','Portland, OR')
]
def connect():
 d=sqlite3.connect(DB); d.row_factory=sqlite3.Row; d.execute('PRAGMA foreign_keys=ON'); return d
def hash_pw(password,salt): return hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),180000).hex()
def init():
 with connect() as d:
  d.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,phone TEXT DEFAULT '',role TEXT NOT NULL DEFAULT 'buyer',password_hash TEXT NOT NULL,salt TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY,name TEXT UNIQUE NOT NULL,icon TEXT DEFAULT '✳');
  CREATE TABLE IF NOT EXISTS listings(id INTEGER PRIMARY KEY,title TEXT NOT NULL,category TEXT NOT NULL,description TEXT NOT NULL,image TEXT NOT NULL,price REAL NOT NULL,condition TEXT NOT NULL,location TEXT NOT NULL,seller_id INTEGER REFERENCES users(id),active INTEGER DEFAULT 1,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS favorites(user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,PRIMARY KEY(user_id,listing_id));
  CREATE TABLE IF NOT EXISTS offers(id INTEGER PRIMARY KEY,listing_id INTEGER NOT NULL REFERENCES listings(id),buyer_id INTEGER NOT NULL REFERENCES users(id),amount REAL NOT NULL,message TEXT DEFAULT '',status TEXT DEFAULT 'Open',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY,order_code TEXT UNIQUE NOT NULL,buyer_id INTEGER NOT NULL REFERENCES users(id),listing_id INTEGER NOT NULL REFERENCES listings(id),price REAL NOT NULL,status TEXT DEFAULT 'Confirmed',logistics TEXT DEFAULT 'Pickup to arrange',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY,order_id INTEGER NOT NULL REFERENCES orders(id),from_user INTEGER NOT NULL REFERENCES users(id),to_user INTEGER NOT NULL REFERENCES users(id),rating INTEGER NOT NULL,comment TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,message TEXT NOT NULL,read INTEGER DEFAULT 0,created_at TEXT DEFAULT CURRENT_TIMESTAMP);''')
  for name,icon in [('Electronics','⌁'),('Furniture','⌂'),('Clothing','◇'),('Collectibles','✳')]:d.execute('INSERT OR IGNORE INTO categories(name,icon) VALUES(?,?)',(name,icon))
  if not d.execute('SELECT 1 FROM listings LIMIT 1').fetchone():
   for it in SEED:d.execute('INSERT INTO listings(id,title,category,description,image,price,condition,location) VALUES(?,?,?,?,?,?,?,?)',it)
  if not d.execute("SELECT 1 FROM users WHERE email='admin@renewmarket.test'").fetchone():
   salt=secrets.token_hex(16);d.execute("INSERT INTO users(name,email,role,password_hash,salt) VALUES(?,?,?,?,?)",('ReNew Admin','admin@renewmarket.test','admin',hash_pw('renew12345',salt),salt))
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def send(self,status,data,typ='application/json; charset=utf-8'):
  body=data if isinstance(data,bytes) else (json.dumps(data).encode() if typ.startswith('application/json') else data.encode());self.send_response(status);self.send_header('Content-Type',typ);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 def body(self):
  try:return json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))) or b'{}')
  except:return {}
 def me(self):
  try:uid=int(self.headers.get('X-User','0'))
  except:uid=0
  with connect() as d:return d.execute('SELECT id,name,email,phone,role FROM users WHERE id=?',(uid,)).fetchone()
 def require(self,roles=None):
  u=self.me()
  if not u:return None
  if roles and u['role'] not in roles:return None
  return u
 def do_GET(self):
  p=urlparse(self.path).path;u=self.me()
  if p=='/api/listings':
   with connect() as d:
    rows=d.execute('SELECT l.*,u.name seller_name FROM listings l LEFT JOIN users u ON u.id=l.seller_id WHERE l.active=1 ORDER BY l.id DESC').fetchall(); out=[]
    for row in rows:
     x=dict(row); x['favorite']=bool(u and d.execute('SELECT 1 FROM favorites WHERE user_id=? AND listing_id=?',(u['id'],row['id'])).fetchone()); out.append(x)
    self.send(200,out);return
  if p=='/api/categories':
   with connect() as d:self.send(200,[dict(r) for r in d.execute('SELECT c.*,COUNT(l.id) count FROM categories c LEFT JOIN listings l ON l.category=c.name AND l.active=1 GROUP BY c.id ORDER BY count DESC,c.name')]);return
  if p=='/api/me':self.send(200,dict(u) if u else {});return
  if p=='/api/orders':
   if not u:self.send(401,{'error':'Sign in to see your transactions.'});return
   with connect() as d:
    q='SELECT o.*,l.title listing_title,b.name buyer_name,s.name seller_name FROM orders o JOIN listings l ON l.id=o.listing_id JOIN users b ON b.id=o.buyer_id LEFT JOIN users s ON s.id=l.seller_id'; rows=d.execute(q+' WHERE o.buyer_id=? OR l.seller_id=? ORDER BY o.id DESC',(u['id'],u['id'])).fetchall() if u['role']!='admin' else d.execute(q+' ORDER BY o.id DESC').fetchall();self.send(200,[dict(r) for r in rows]);return
  if p=='/api/users':
   if not u or u['role']!='admin':self.send(403,{'error':'Administrator access required.'});return
   with connect() as d:self.send(200,[dict(r) for r in d.execute('SELECT u.id,u.name,u.email,u.phone,u.role,u.created_at,COUNT(DISTINCT o.id) transaction_count FROM users u LEFT JOIN orders o ON o.buyer_id=u.id GROUP BY u.id ORDER BY u.id DESC')]);return
  if p=='/api/notifications':
   if not u:self.send(401,{'error':'Sign in to see notifications.'});return
   with connect() as d:self.send(200,[dict(r) for r in d.execute('SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 20',(u['id'],))]);return
  if p=='/api/offers':
   if not u:self.send(401,{'error':'Sign in to view offers.'});return
   with connect() as d:
    q='SELECT f.*,l.title,b.name buyer_name,s.id seller_id FROM offers f JOIN listings l ON l.id=f.listing_id JOIN users b ON b.id=f.buyer_id LEFT JOIN users s ON s.id=l.seller_id';rows=d.execute(q+' WHERE f.buyer_id=? OR s.id=? ORDER BY f.id DESC',(u['id'],u['id'])).fetchall();self.send(200,[dict(r) for r in rows]);return
  if p=='/':self.send(200,(ROOT/'index.html').read_bytes(),'text/html; charset=utf-8');return
  target=(ROOT/p.lstrip('/')).resolve()
  if target.parent!=ROOT or not target.exists():self.send(404,'Not found','text/plain');return
  typ='text/css; charset=utf-8' if target.suffix=='.css' else 'application/javascript; charset=utf-8' if target.suffix=='.js' else 'application/octet-stream';self.send(200,target.read_bytes(),typ)
 def do_POST(self):
  p=urlparse(self.path).path;x=self.body()
  if p in ('/api/register','/api/login'):
   with connect() as d:
    if p.endswith('register'):
     name=str(x.get('name','')).strip()[:80];email=str(x.get('email','')).strip().lower()[:120];phone=str(x.get('phone','')).strip()[:32];password=str(x.get('password',''))
     if not name or '@' not in email or len(password)<8:self.send(400,{'error':'Enter your name, valid email, and a password of at least 8 characters.'});return
     salt=secrets.token_hex(16)
     try:cur=d.execute('INSERT INTO users(name,email,phone,role,password_hash,salt) VALUES(?,?,?,\'buyer\',?,?)',(name,email,phone,hash_pw(password,salt),salt))
     except sqlite3.IntegrityError:self.send(409,{'error':'An account already uses that email.'});return
     self.send(201,{'id':cur.lastrowid,'name':name,'email':email,'phone':phone,'role':'buyer'});return
    email=str(x.get('email','')).lower().strip();pw=str(x.get('password',''));row=d.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
    if not row or not secrets.compare_digest(hash_pw(pw,row['salt']),row['password_hash']):self.send(401,{'error':'Email or password did not match.'});return
    self.send(200,{k:row[k] for k in ('id','name','email','phone','role')});return
  if p=='/api/listings':
   u=self.require()
   if not u:self.send(401,{'error':'Sign in to create a listing.'});return
   try:price=round(float(x.get('price',0)),2)
   except:price=0
   title=str(x.get('title','')).strip()[:100];category=str(x.get('category','')).strip()[:50];description=str(x.get('description','')).strip()[:1000];image=str(x.get('image','photo-1516035069371-29a1b244cc32')).strip()[:100];condition=str(x.get('condition','Good'));location=str(x.get('location','')).strip()[:80]
   if not title or not category or not description or price<=0 or not location:self.send(400,{'error':'Complete the title, category, description, price, and location.'});return
   with connect() as d:cur=d.execute('INSERT INTO listings(title,category,description,image,price,condition,location,seller_id) VALUES(?,?,?,?,?,?,?,?)',(title,category,description,image,price,condition,location,u['id']));self.send(201,{'id':cur.lastrowid});return
  if p=='/api/favorites':
   u=self.require()
   if not u:self.send(401,{'error':'Sign in to save favorites.'});return
   lid=int(x.get('listing_id',0))
   with connect() as d:
    exists=d.execute('SELECT 1 FROM favorites WHERE user_id=? AND listing_id=?',(u['id'],lid)).fetchone()
    if exists:d.execute('DELETE FROM favorites WHERE user_id=? AND listing_id=?',(u['id'],lid));saved=False
    else:d.execute('INSERT OR IGNORE INTO favorites(user_id,listing_id) VALUES(?,?)',(u['id'],lid));saved=True
   self.send(200,{'saved':saved});return
  if p=='/api/orders':
   u=self.require()
   if not u or u['role']=='admin':self.send(401,{'error':'Sign in with a buyer account to purchase.'});return
   lid=int(x.get('listing_id',0))
   with connect() as d:
    l=d.execute('SELECT * FROM listings WHERE id=? AND active=1',(lid,)).fetchone()
    if not l or l['seller_id']==u['id']:self.send(400,{'error':'This item is not available to buy.'});return
    code='RN-'+secrets.token_hex(3).upper();cur=d.execute('INSERT INTO orders(order_code,buyer_id,listing_id,price) VALUES(?,?,?,?)',(code,u['id'],lid,l['price']));d.execute('UPDATE listings SET active=0 WHERE id=?',(lid,));d.execute('INSERT INTO notifications(user_id,message) VALUES(?,?)',(u['id'],f'Your order {code} for {l["title"]} is confirmed.'));self.send(201,{'code':code,'listing':l['title']});return
  if p=='/api/offers':
   u=self.require()
   if not u or u['role']=='admin':self.send(401,{'error':'Sign in as a buyer to make an offer.'});return
   lid=int(x.get('listing_id',0))
   try:amount=round(float(x.get('amount',0)),2)
   except:amount=0
   with connect() as d:
    l=d.execute('SELECT * FROM listings WHERE id=? AND active=1',(lid,)).fetchone()
    if not l or l['seller_id']==u['id'] or amount<=0:self.send(400,{'error':'Enter a valid offer for an available item.'});return
    d.execute('INSERT INTO offers(listing_id,buyer_id,amount,message) VALUES(?,?,?,?)',(lid,u['id'],amount,str(x.get('message',''))[:500]));
    if l['seller_id']:d.execute('INSERT INTO notifications(user_id,message) VALUES(?,?)',(l['seller_id'],f'{u["name"]} made an offer of ${amount:.2f} on {l["title"]}.'))
   self.send(201,{'ok':True});return
  if p=='/api/admin/users':
   u=self.require(['admin'])
   if not u:self.send(403,{'error':'Administrator access required.'});return
   name=str(x.get('name','')).strip();email=str(x.get('email','')).strip().lower();password=str(x.get('password',''));role=x.get('role','buyer')
   if not name or '@' not in email or len(password)<8 or role not in ('buyer','admin'):self.send(400,{'error':'Enter name, email, password (8+ characters), and role.'});return
   salt=secrets.token_hex(16)
   try:
    with connect() as d:d.execute('INSERT INTO users(name,email,role,password_hash,salt) VALUES(?,?,?,?,?)',(name,email,role,hash_pw(password,salt),salt))
   except sqlite3.IntegrityError:self.send(409,{'error':'That email already has an account.'});return
   self.send(201,{'ok':True});return
  if p=='/api/feedback':
   u=self.require()
   if not u:self.send(401,{'error':'Sign in to leave feedback.'});return
   oid=int(x.get('order_id',0));rating=max(1,min(5,int(x.get('rating',5))));comment=str(x.get('comment',''))[:500]
   with connect() as d:
    o=d.execute('SELECT * FROM orders WHERE id=? AND buyer_id=? AND status="Received"',(oid,u['id'])).fetchone()
    if not o:self.send(400,{'error':'Feedback is available after the order is received.'});return
    l=d.execute('SELECT seller_id FROM listings WHERE id=?',(o['listing_id'],)).fetchone();to=l['seller_id'] or u['id'];d.execute('INSERT INTO feedback(order_id,from_user,to_user,rating,comment) VALUES(?,?,?,?,?)',(oid,u['id'],to,rating,comment));self.send(201,{'ok':True});return
  if p=='/api/categories':
   u=self.require(['admin'])
   if not u:self.send(403,{'error':'Administrator access required.'});return
   name=str(x.get('name','')).strip()[:50];icon=str(x.get('icon','✳'))[:5]
   if not name:self.send(400,{'error':'Enter a category name.'});return
   try:
    with connect() as d:d.execute('INSERT INTO categories(name,icon) VALUES(?,?)',(name,icon))
   except sqlite3.IntegrityError:self.send(409,{'error':'That category already exists.'});return
   self.send(201,{'ok':True});return
  self.send(404,{'error':'Not found'})
 def do_PUT(self):
  p=urlparse(self.path).path;x=self.body();u=self.me()
  if p=='/api/me':
   if not u:self.send(401,{'error':'Sign in first.'});return
   name=str(x.get('name','')).strip()[:80];email=str(x.get('email','')).strip().lower()[:120];phone=str(x.get('phone','')).strip()[:32]
   try:
    with connect() as d:d.execute('UPDATE users SET name=?,email=?,phone=? WHERE id=?',(name,email,phone,u['id']))
   except sqlite3.IntegrityError:self.send(409,{'error':'That email is already in use.'});return
   self.send(200,{'id':u['id'],'name':name,'email':email,'phone':phone,'role':u['role']});return
  if p.startswith('/api/users/'):
   if not u or u['role']!='admin':self.send(403,{'error':'Administrator access required.'});return
   uid=int(p.rsplit('/',1)[-1]);name=str(x.get('name','')).strip()[:80];email=str(x.get('email','')).strip().lower()[:120];phone=str(x.get('phone','')).strip()[:32];role=x.get('role','buyer')
   if not name or '@' not in email or role not in ('buyer','admin'):self.send(400,{'error':'Enter a valid name, email, and role.'});return
   try:
    with connect() as d:d.execute('UPDATE users SET name=?,email=?,phone=?,role=? WHERE id=?',(name,email,phone,role,uid))
   except sqlite3.IntegrityError:self.send(409,{'error':'That email is already used.'});return
   self.send(200,{'ok':True});return
  if p.startswith('/api/listings/'):
   lid=int(p.rsplit('/',1)[-1]);allowed=u and (u['role']=='admin')
   with connect() as d:
    if not allowed:allowed=bool(u and d.execute('SELECT 1 FROM listings WHERE id=? AND seller_id=?',(lid,u['id'])).fetchone())
    if not allowed:self.send(403,{'error':'Only the seller or an administrator can edit this listing.'});return
    fields=[];vals=[]
    for k in ('title','category','description','image','price','condition','location'):
     if k in x:fields.append(k+'=?');vals.append(float(x[k]) if k=='price' else str(x[k]))
    if not fields:self.send(400,{'error':'No listing changes were provided.'});return
    vals.append(lid);d.execute('UPDATE listings SET '+','.join(fields)+' WHERE id=?',vals);self.send(200,{'ok':True});return
  if p.startswith('/api/orders/'):
   if not u or u['role']!='admin':self.send(403,{'error':'Administrator access required.'});return
   oid=int(p.rsplit('/',1)[-1]);status=x.get('status');logistics=x.get('logistics')
   with connect() as d:
    if status and status not in ('Confirmed','Shipped','Received','Cancelled'):self.send(400,{'error':'Invalid status.'});return
    if status:d.execute('UPDATE orders SET status=? WHERE id=?',(status,oid))
    if logistics:d.execute('UPDATE orders SET logistics=? WHERE id=?',(str(logistics)[:100],oid))
    row=d.execute('SELECT buyer_id,order_code,status FROM orders WHERE id=?',(oid,)).fetchone()
    if row and status:d.execute('INSERT INTO notifications(user_id,message) VALUES(?,?)',(row['buyer_id'],f'Order {row["order_code"]} update: {status}.'))
   self.send(200,{'ok':True});return
  if p.startswith('/api/offers/'):
   oid=int(p.rsplit('/',1)[-1]);status=str(x.get('status','Countered'));amount=x.get('amount');
   with connect() as d:
    row=d.execute('SELECT f.*,l.seller_id,l.title FROM offers f JOIN listings l ON l.id=f.listing_id WHERE f.id=?',(oid,)).fetchone()
    if not row or not u or (u['id']!=row['seller_id'] and u['role']!='admin'):self.send(403,{'error':'Only the seller can respond to this offer.'});return
    if status not in ('Accepted','Declined','Countered'):self.send(400,{'error':'Invalid offer response.'});return
    if status=='Countered':
     try:amount=round(float(amount),2)
     except:self.send(400,{'error':'Enter a counter-offer amount.'});return
     if amount<=0:self.send(400,{'error':'Enter a valid counter-offer amount.'});return
     d.execute('UPDATE offers SET status=?,amount=? WHERE id=?',(status,amount,oid))
    else:d.execute('UPDATE offers SET status=? WHERE id=?',(status,oid))
    d.execute('INSERT INTO notifications(user_id,message) VALUES(?,?)',(row['buyer_id'],f'Your offer on {row["title"]} was {status.lower()}.'))
   self.send(200,{'ok':True});return
  self.send(404,{'error':'Not found'})
 def do_DELETE(self):
  p=urlparse(self.path).path;u=self.me()
  if p.startswith('/api/listings/'):
   lid=int(p.rsplit('/',1)[-1])
   with connect() as d:
    row=d.execute('SELECT seller_id FROM listings WHERE id=?',(lid,)).fetchone()
    if not row or not u or (u['role']!='admin' and row['seller_id']!=u['id']):self.send(403,{'error':'Only the seller or an administrator can remove this listing.'});return
    d.execute('UPDATE listings SET active=0 WHERE id=?',(lid,))
   self.send(200,{'ok':True});return
  if not u or u['role']!='admin':self.send(403,{'error':'Administrator access required.'});return
  with connect() as d:
   if p.startswith('/api/categories/'):
    cid=int(p.rsplit('/',1)[-1]);cat=d.execute('SELECT name FROM categories WHERE id=?',(cid,)).fetchone()
    if cat and d.execute('SELECT COUNT(*) FROM listings WHERE category=? AND active=1',(cat['name'],)).fetchone()[0]:self.send(409,{'error':'Move or remove active listings in this category first.'});return
    d.execute('DELETE FROM categories WHERE id=?',(cid,));self.send(200,{'ok':True});return
   if p.startswith('/api/users/'):
    uid=int(p.rsplit('/',1)[-1])
    if uid==u['id']:self.send(400,{'error':'You cannot delete the account currently in use.'});return
    d.execute('DELETE FROM feedback WHERE from_user=? OR to_user=?',(uid,uid));d.execute('DELETE FROM offers WHERE buyer_id=?',(uid,));d.execute('DELETE FROM notifications WHERE user_id=?',(uid,));d.execute('DELETE FROM orders WHERE buyer_id=?',(uid,));d.execute('UPDATE listings SET seller_id=NULL WHERE seller_id=?',(uid,));d.execute('DELETE FROM favorites WHERE user_id=?',(uid,));d.execute('DELETE FROM users WHERE id=?',(uid,));self.send(200,{'ok':True});return
   if p.startswith('/api/orders/'):
    d.execute('DELETE FROM feedback WHERE order_id=?',(int(p.rsplit('/',1)[-1]),));d.execute('DELETE FROM orders WHERE id=?',(int(p.rsplit('/',1)[-1]),));self.send(200,{'ok':True});return
  self.send(404,{'error':'Not found'})
if __name__=='__main__':
 init();print(f'ReNewMarket is running at http://localhost:{PORT}');ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
