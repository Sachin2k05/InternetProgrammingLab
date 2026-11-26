"""BlossomGifts local demo server. Run with: python server.py"""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import hashlib,json,secrets,sqlite3
ROOT=Path(__file__).resolve().parent;DB=ROOT/'blossomgifts.db';PORT=8002
SEED=[
 {'id':1,'name':'The Sunday Stems','category':'Flowers','occasion':'Just Because','price':58,'label':'BESTSELLER','image':'photo-1490750967868-88aa4486c946','description':'A joyful, seasonal mix of fresh blooms in soft blush and creamy whites.','color':'#efd6d6'},
 {'id':2,'name':'A Little Sunshine','category':'Flowers','occasion':'Birthday','price':72,'label':'FAN FAVORITE','image':'photo-1525310072745-f49212b5ac6d','description':'Bright, happy stems picked to bring a little sunshine to their day.','color':'#f1e5be'},
 {'id':3,'name':'The Cozy Morning Basket','category':'Gift Baskets','occasion':'Thank You','price':86,'label':'THOUGHTFUL PICK','image':'photo-1549465220-1a8b9238cd48','description':'A gentle morning ritual: small-batch tea, honey, and something sweet.','color':'#e5dfcd'},
 {'id':4,'name':'Petals & Prosecco','category':'Flowers','occasion':'Anniversary','price':98,'label':'CELEBRATE','image':'photo-1508610048659-a06b669e3321','description':'Elegant roses and delicate seasonal details for a moment worth celebrating.','color':'#ead7df'},
 {'id':5,'name':'Little Wildflower Posy','category':'Flowers','occasion':'Just Because','price':42,'label':'EASY JOY','image':'photo-1494972308805-463bc619d34e','description':'A sweet, loose handful of garden-inspired blooms, gathered with care.','color':'#e4ebd6'},
 {'id':6,'name':'The Slow Sunday Box','category':'Gift Baskets','occasion':'Thank You','price':64,'label':'SLOW DOWN','image':'photo-1608571423902-eed4a5ad8108','description':'A little self-care bundle with nourishing treats and a candle for later.','color':'#e7e0d7'},
 {'id':7,'name':'Your Words, Their Keepsake','category':'Personalized','occasion':'Birthday','price':39,'label':'MADE PERSONAL','image':'photo-1513201099705-a9746e1e201f','description':'A personalized keepsake with your own message, made just for them.','color':'#e1e7ed'},
 {'id':8,'name':'The Forever Garden','category':'Plants','occasion':'Housewarming','price':55,'label':'GROWING LOVE','image':'photo-1485955900006-10f4d324d411','description':'An easy-care green friend in a beautiful pot, ready for a new home.','color':'#dfe9d8'}
]
def con():
 d=sqlite3.connect(DB);d.row_factory=sqlite3.Row;d.execute('PRAGMA foreign_keys=ON');return d
def init():
 with con() as d:
  d.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,phone TEXT DEFAULT '',password_hash TEXT NOT NULL,salt TEXT NOT NULL,role TEXT DEFAULT 'customer',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,name TEXT NOT NULL,category TEXT NOT NULL,occasion TEXT NOT NULL,price REAL NOT NULL,label TEXT DEFAULT 'NEW',image TEXT NOT NULL,description TEXT NOT NULL,color TEXT DEFAULT '#efe5dc',active INTEGER DEFAULT 1);
  CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY,order_code TEXT UNIQUE NOT NULL,user_id INTEGER REFERENCES users(id),customer_name TEXT NOT NULL,email TEXT NOT NULL,phone TEXT DEFAULT '',address TEXT NOT NULL,delivery_date TEXT NOT NULL,delivery_time TEXT NOT NULL,occasion TEXT DEFAULT '',note TEXT DEFAULT '',total REAL NOT NULL,status TEXT DEFAULT 'Confirmed',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS order_items(id INTEGER PRIMARY KEY,order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,product_id INTEGER,name TEXT NOT NULL,price REAL NOT NULL,quantity INTEGER NOT NULL);
  CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY,order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,channel TEXT NOT NULL,recipient TEXT NOT NULL,message TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);''')
  if not d.execute('SELECT 1 FROM products LIMIT 1').fetchone():
   for p in SEED:d.execute('INSERT INTO products(id,name,category,occasion,price,label,image,description,color) VALUES(?,?,?,?,?,?,?,?,?)',(p['id'],p['name'],p['category'],p['occasion'],p['price'],p['label'],p['image'],p['description'],p['color']))
  if not d.execute("SELECT 1 FROM users WHERE email='hello@blossomgifts.test'").fetchone():
   salt=secrets.token_hex(16);pw=hashlib.pbkdf2_hmac('sha256',b'flowers123',salt.encode(),180000).hex();d.execute("INSERT INTO users(name,email,password_hash,salt,role) VALUES('Blossom Admin','hello@blossomgifts.test',?,?,'admin')",(pw,salt))
class H(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def out(self,s,obj,typ='application/json; charset=utf-8'):
  b=obj if isinstance(obj,bytes) else (json.dumps(obj).encode() if typ.startswith('application/json') else obj.encode());self.send_response(s);self.send_header('Content-Type',typ);self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def body(self):
  try:return json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))) or b'{}')
  except:return {}
 def me(self):
  try:uid=int(self.headers.get('X-User','0'))
  except:uid=0
  with con() as d:return d.execute('SELECT id,name,email,phone,role FROM users WHERE id=?',(uid,)).fetchone()
 def do_GET(self):
  p=urlparse(self.path).path;u=self.me()
  if p=='/api/products':
   with con() as d:self.out(200,[dict(x) for x in d.execute('SELECT * FROM products WHERE active=1 ORDER BY id')]);return
  if p=='/api/me':self.out(200,dict(u) if u else {});return
  if p.startswith('/api/track/'):
   code=p.rsplit('/',1)[-1].upper()
   with con() as d:
    r=d.execute('SELECT order_code,status,delivery_date,delivery_time,total,customer_name FROM orders WHERE order_code=?',(code,)).fetchone()
    if not r:self.out(404,{'error':'We could not find an order with that code.'});return
    result=dict(r);result['items']=[dict(a) for a in d.execute('SELECT name,price,quantity FROM order_items WHERE order_id=(SELECT id FROM orders WHERE order_code=?)',(code,))];self.out(200,result);return
  if p=='/api/orders':
   if not u:self.out(401,{'error':'Please sign in to view orders.'});return
   with con() as d:
    q='SELECT * FROM orders';rows=d.execute(q+' WHERE user_id=? ORDER BY id DESC',(u['id'],)).fetchall() if u['role']=='customer' else d.execute(q+' ORDER BY id DESC').fetchall();result=[]
    for r in rows:
     x=dict(r);x['items']=[dict(a) for a in d.execute('SELECT name,price,quantity FROM order_items WHERE order_id=?',(r['id'],))];result.append(x)
    self.out(200,result);return
  if p=='/api/customers':
   if not u or u['role']!='admin':self.out(403,{'error':'Admin access required.'});return
   with con() as d:self.out(200,[dict(x) for x in d.execute('SELECT u.id,u.name,u.email,u.phone,u.created_at,COUNT(o.id) order_count,COALESCE(SUM(o.total),0) spent FROM users u LEFT JOIN orders o ON o.user_id=u.id WHERE u.role="customer" GROUP BY u.id ORDER BY u.id DESC')]);return
  if p=='/':self.out(200,(ROOT/'index.html').read_bytes(),'text/html; charset=utf-8');return
  target=(ROOT/p.lstrip('/')).resolve()
  if target.parent!=ROOT or not target.exists():self.out(404,'Not found','text/plain');return
  typ='text/css; charset=utf-8' if target.suffix=='.css' else 'application/javascript; charset=utf-8' if target.suffix=='.js' else 'application/octet-stream';self.out(200,target.read_bytes(),typ)
 def do_POST(self):
  p=urlparse(self.path).path;x=self.body()
  if p in ('/api/register','/api/login'):
   with con() as d:
    if p.endswith('register'):
     name=str(x.get('name','')).strip()[:80];email=str(x.get('email','')).strip().lower()[:120];phone=str(x.get('phone','')).strip()[:30];password=str(x.get('password',''))
     if not name or '@' not in email or len(password)<8:self.out(400,{'error':'Enter your name, email, and a password with at least 8 characters.'});return
     salt=secrets.token_hex(16);pw=hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),180000).hex()
     try:cur=d.execute('INSERT INTO users(name,email,phone,password_hash,salt) VALUES(?,?,?,?,?)',(name,email,phone,pw,salt))
     except sqlite3.IntegrityError:self.out(409,{'error':'An account already uses this email.'});return
     self.out(201,{'id':cur.lastrowid,'name':name,'email':email,'phone':phone,'role':'customer'});return
    email=str(x.get('email','')).lower().strip();password=str(x.get('password',''));u=d.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
    if not u or not secrets.compare_digest(hashlib.pbkdf2_hmac('sha256',password.encode(),u['salt'].encode(),180000).hex(),u['password_hash']):self.out(401,{'error':'Email or password did not match.'});return
    self.out(200,{'id':u['id'],'name':u['name'],'email':u['email'],'phone':u['phone'],'role':u['role']});return
  if p=='/api/orders':
   items=x.get('items',[]);name=str(x.get('name','')).strip()[:80];email=str(x.get('email','')).strip().lower()[:120];phone=str(x.get('phone','')).strip()[:30];address=str(x.get('address','')).strip()[:250];date=str(x.get('date',''));time=str(x.get('time',''));u=self.me()
   if not items or not name or '@' not in email or len(address)<8 or not date or not time:self.out(400,{'error':'Complete your contact, delivery, and cart details.'});return
   with con() as d:
    clean=[];subtotal=0
    for it in items:
     try:pid=int(it['id']);qty=max(1,min(20,int(it.get('qty',1))))
     except:self.out(400,{'error':'One item in your bag is invalid.'});return
     pr=d.execute('SELECT id,name,price FROM products WHERE id=? AND active=1',(pid,)).fetchone()
     if not pr:self.out(400,{'error':'An item in your bag is no longer available.'});return
     clean.append((pr['id'],pr['name'],pr['price'],qty));subtotal+=pr['price']*qty
    discount=round(subtotal*.15,2) if str(x.get('promo','')).upper()=='BLOOM15' else 0;total=round(subtotal-discount,2)
    code='BG-'+secrets.token_hex(3).upper();cur=d.execute('INSERT INTO orders(order_code,user_id,customer_name,email,phone,address,delivery_date,delivery_time,occasion,note,total) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(code,u['id'] if u else None,name,email,phone,address,date,time,str(x.get('occasion',''))[:80],str(x.get('note',''))[:500],total));oid=cur.lastrowid
    for row in clean:d.execute('INSERT INTO order_items(order_id,product_id,name,price,quantity) VALUES(?,?,?,?,?)',(oid,*row))
    msg=f"BlossomGifts order {code} confirmed for {date} ({time}). Thanks for sending something lovely!";d.execute("INSERT INTO messages(order_id,channel,recipient,message) VALUES(?,?,?,?)",(oid,'Email demo',email,msg))
    if phone:d.execute("INSERT INTO messages(order_id,channel,recipient,message) VALUES(?,?,?,?)",(oid,'SMS demo',phone,msg))
    self.out(201,{'id':oid,'code':code,'subtotal':subtotal,'discount':discount,'total':total,'message':msg});return
  u=self.me()
  if not u or u['role']!='admin':self.out(403,{'error':'Admin access required.'});return
  with con() as d:
   if p=='/api/products':
    name=str(x.get('name','')).strip()[:100];category=str(x.get('category','')).strip()[:50];occasion=str(x.get('occasion','Just Because')).strip()[:50];desc=str(x.get('description','')).strip()[:500];img=str(x.get('image','photo-1490750967868-88aa4486c946')).strip()[:100]
    try:price=round(float(x.get('price',0)),2)
    except:price=0
    if not name or not category or not desc or price<=0:self.out(400,{'error':'Add a name, category, description, and a price above zero.'});return
    cur=d.execute('INSERT INTO products(name,category,occasion,price,label,image,description,color) VALUES(?,?,?,?,?,?,?,?)',(name,category,occasion,price,str(x.get('label','NEW'))[:32],img,desc,str(x.get('color','#efe5dc'))[:20]));self.out(201,{'id':cur.lastrowid});return
  self.out(404,{'error':'Not found'})
 def do_PUT(self):
  p=urlparse(self.path).path;x=self.body();u=self.me()
  if p=='/api/me':
   if not u:self.out(401,{'error':'Please sign in first.'});return
   name=str(x.get('name','')).strip()[:80];email=str(x.get('email','')).strip().lower()[:120];phone=str(x.get('phone','')).strip()[:30]
   if not name or '@' not in email:self.out(400,{'error':'Enter your name and a valid email.'});return
   try:
    with con() as d:d.execute('UPDATE users SET name=?,email=?,phone=? WHERE id=?',(name,email,phone,u['id']))
   except sqlite3.IntegrityError:self.out(409,{'error':'That email is already in use.'});return
   self.out(200,{'id':u['id'],'name':name,'email':email,'phone':phone,'role':u['role']});return
  if not u or u['role']!='admin':self.out(403,{'error':'Admin access required.'});return
  with con() as d:
   if p.startswith('/api/products/'):
    pid=int(p.split('/')[-1]);fields=[];vals=[]
    for key,col in [('name','name'),('category','category'),('occasion','occasion'),('description','description'),('image','image'),('price','price')]:
     if key in x:fields.append(col+'=?');vals.append(float(x[key]) if key=='price' else str(x[key]))
    if not fields:self.out(400,{'error':'Nothing to update.'});return
    vals.append(pid);cur=d.execute('UPDATE products SET '+','.join(fields)+' WHERE id=?',vals);self.out(200,{'ok':cur.rowcount>0});return
   if p.startswith('/api/orders/'):
    status=str(x.get('status','Confirmed'))
    if status not in ('Confirmed','Preparing','Out for delivery','Delivered','Cancelled'):self.out(400,{'error':'Invalid order status.'});return
    d.execute('UPDATE orders SET status=? WHERE id=?',(status,int(p.split('/')[-1])));self.out(200,{'ok':True});return
  self.out(404,{'error':'Not found'})
 def do_DELETE(self):
  u=self.me()
  if urlparse(self.path).path=='/api/me':
   if not u or u['role']!='customer':self.out(403,{'error':'Customer access required.'});return
   with con() as d:d.execute('UPDATE orders SET user_id=NULL WHERE user_id=?',(u['id'],));d.execute('DELETE FROM users WHERE id=?',(u['id'],))
   self.out(200,{'ok':True});return
  if not u or u['role']!='admin':self.out(403,{'error':'Admin access required.'});return
  p=urlparse(self.path).path
  if p.startswith('/api/products/'):
   with con() as d:d.execute('UPDATE products SET active=0 WHERE id=?',(int(p.split('/')[-1]),))
   self.out(200,{'ok':True});return
  self.out(404,{'error':'Not found'})
if __name__=='__main__':
 init();print(f'BlossomGifts is running at http://localhost:{PORT}');ThreadingHTTPServer(('127.0.0.1',PORT),H).serve_forever()
