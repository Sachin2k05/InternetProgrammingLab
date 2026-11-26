"""AgriMart local classroom storefront. Run with: python server.py"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sqlite3, json, secrets, hashlib, time, re, mimetypes
from urllib.parse import urlparse

ROOT=Path(__file__).parent
DB=ROOT/'agrimart.db'
def conn():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c
def init():
    with conn() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, phone TEXT DEFAULT '', password TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('customer','farmer')), wallet REAL NOT NULL DEFAULT 10000, active INTEGER NOT NULL DEFAULT 1, created TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, farmer_id INTEGER NOT NULL REFERENCES users(id), name TEXT NOT NULL, category TEXT NOT NULL, description TEXT NOT NULL, price REAL NOT NULL, unit TEXT NOT NULL DEFAULT 'each', stock INTEGER NOT NULL DEFAULT 0, image TEXT DEFAULT '', created TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS addresses(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), label TEXT NOT NULL, address TEXT NOT NULL, city TEXT NOT NULL, postal TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS carts(user_id INTEGER NOT NULL REFERENCES users(id), product_id INTEGER NOT NULL REFERENCES products(id), quantity INTEGER NOT NULL, PRIMARY KEY(user_id,product_id));
        CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), address_id INTEGER REFERENCES addresses(id), total REAL NOT NULL, status TEXT NOT NULL DEFAULT 'Placed', created TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS order_items(id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id), product_id INTEGER NOT NULL REFERENCES products(id), product_name TEXT NOT NULL, price REAL NOT NULL, quantity INTEGER NOT NULL, shipping TEXT NOT NULL DEFAULT 'Preparing');
        CREATE TABLE IF NOT EXISTS otp(email TEXT PRIMARY KEY, code TEXT NOT NULL, expires INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), expires INTEGER NOT NULL);
        ''')
        if not c.execute('SELECT id FROM users WHERE email=?',('farmer@agrimart.test',)).fetchone():
            f=c.execute('INSERT INTO users(name,email,phone,password,role) VALUES(?,?,?,?,?)',('Green Valley Farm','farmer@agrimart.test','555-0101',hashlib.sha256(b'farm12345').hexdigest(),'farmer')).lastrowid
            c.execute('INSERT INTO users(name,email,phone,password,role) VALUES(?,?,?,?,?)',('Avery Customer','customer@agrimart.test','555-0102',hashlib.sha256(b'shop12345').hexdigest(),'customer'))
            samples=[('Heirloom Tomato Seeds','Seeds','Open-pollinated tomato seeds for a productive garden season.',6.50,'packet',120,'🌱'),('Organic Compost Blend','Fertilizers','Nutrient-rich compost blend for beds, pots, and field rows.',18.00,'bag',45,'♻️'),('Precision Drip Irrigation Kit','Equipment','Water-saving starter kit with tubing and adjustable emitters.',42.00,'kit',18,'💧'),('Neem Garden Spray','Pest control','Plant-based neem solution for routine garden care.',12.75,'bottle',30,'🌿'),('Hand Pruning Shears','Tools','Comfortable bypass shears for everyday pruning tasks.',21.50,'each',24,'✂️'),('Golden Field Wheat Seed','Seeds','Reliable wheat seed selected for consistent germination.',34.00,'bag',32,'🌾')]
            for p in samples:c.execute('INSERT INTO products(farmer_id,name,category,description,price,unit,stock,image) VALUES(?,?,?,?,?,?,?,?)',(f,*p))
        if not c.execute('SELECT id FROM addresses WHERE user_id=(SELECT id FROM users WHERE email=?)',('customer@agrimart.test',)).fetchone():
            c.execute('INSERT INTO addresses(user_id,label,address,city,postal) VALUES((SELECT id FROM users WHERE email=?),?,?,?,?)',('customer@agrimart.test','Farmhouse','42 Meadow Lane','Springfield','01104'))

def body(h):
    n=int(h.headers.get('Content-Length','0')); return json.loads(h.rfile.read(n) or b'{}')
def pack(r): return dict(r) if r else None
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def send(self,status,obj):
        data=json.dumps(obj).encode(); self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(data))); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers(); self.wfile.write(data)
    def auth(self,c,role=None):
        token=self.headers.get('Authorization','').replace('Bearer ',''); u=c.execute('SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>? AND u.active=1',(token,int(time.time()))).fetchone()
        if not u: raise ValueError('Please sign in to continue.')
        if role and u['role']!=role: raise ValueError('This action is only available to '+role+' accounts.')
        return u
    def do_OPTIONS(self): self.send_response(204); self.send_header('Access-Control-Allow-Origin','*'); self.send_header('Access-Control-Allow-Headers','Content-Type, Authorization'); self.send_header('Access-Control-Allow-Methods','GET, POST, PUT, DELETE, OPTIONS'); self.end_headers()
    def do_GET(self):
        path=urlparse(self.path).path
        if path in ('/','/index.html'):
            b=(ROOT/'index.html').read_bytes(); self.send_response(200); self.send_header('Content-Type','text/html'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b); return
        if path in ('/styles.css','/script.js'):
            b=(ROOT/path[1:]).read_bytes(); self.send_response(200); self.send_header('Content-Type',mimetypes.guess_type(path)[0] or 'text/plain'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b); return
        with conn() as c:
            try:
                if path=='/api/products':
                    from urllib.parse import parse_qs
                    q=parse_qs(urlparse(self.path).query); terms=q.get('q',[''])[0].strip(); cat=q.get('category',[''])[0]
                    sql='SELECT p.*,u.name farmer FROM products p JOIN users u ON u.id=p.farmer_id WHERE p.stock>0'; args=[]
                    if terms: sql+=' AND (p.name LIKE ? OR p.description LIKE ? OR p.category LIKE ?)'; args += [f'%{terms}%']*3
                    if cat and cat!='All': sql+=' AND p.category=?'; args.append(cat)
                    sql+=' ORDER BY p.created DESC'; rows=c.execute(sql,args).fetchall(); self.send(200,[pack(r) for r in rows]); return
                if path=='/api/me':
                    u=self.auth(c); self.send(200,{k:u[k] for k in ('id','name','email','phone','role','wallet')}); return
                if path in ('/api/cart','/api/orders','/api/addresses','/api/farmer/products','/api/farmer/orders'):
                    u=self.auth(c)
                    if path=='/api/cart': rows=c.execute('SELECT p.*,ca.quantity,u.name farmer FROM carts ca JOIN products p ON p.id=ca.product_id JOIN users u ON u.id=p.farmer_id WHERE ca.user_id=?',(u['id'],)).fetchall()
                    elif path=='/api/orders': rows=c.execute('SELECT o.*, (SELECT COUNT(*) FROM order_items i WHERE i.order_id=o.id) item_count FROM orders o WHERE o.user_id=? ORDER BY o.id DESC',(u['id'],)).fetchall()
                    elif path=='/api/addresses': rows=c.execute('SELECT * FROM addresses WHERE user_id=?',(u['id'],)).fetchall()
                    elif path=='/api/farmer/products': self.auth(c,'farmer'); rows=c.execute('SELECT * FROM products WHERE farmer_id=? ORDER BY id DESC',(u['id'],)).fetchall()
                    else:
                        self.auth(c,'farmer'); rows=c.execute('SELECT DISTINCT o.*, (SELECT COUNT(*) FROM order_items i JOIN products p2 ON p2.id=i.product_id WHERE i.order_id=o.id AND p2.farmer_id=?) item_count FROM orders o JOIN order_items i ON i.order_id=o.id JOIN products p ON p.id=i.product_id WHERE p.farmer_id=? ORDER BY o.id DESC',(u['id'],u['id'])).fetchall()
                    self.send(200,[pack(r) for r in rows]); return
                if path.startswith('/api/orders/'):
                    u=self.auth(c); oid=int(path.rsplit('/',1)[-1]); o=c.execute('SELECT * FROM orders WHERE id=? AND user_id=?',(oid,u['id'])).fetchone()
                    if not o:self.send(404,{'error':'Order not found'});return
                    self.send(200,{'order':pack(o),'items':[pack(i) for i in c.execute('SELECT * FROM order_items WHERE order_id=?',(oid,)).fetchall()]});return
                self.send(404,{'error':'Not found'})
            except ValueError as e:self.send(401,{'error':str(e)})
    def do_POST(self): self.handle('POST')
    def do_PUT(self): self.handle('PUT')
    def do_DELETE(self): self.handle('DELETE')
    def handle(self,method):
        path=urlparse(self.path).path
        try:
            d=body(self) if method!='DELETE' else {}
            with conn() as c:
                if path=='/api/register' and method=='POST':
                    name=d.get('name','').strip(); email=d.get('email','').lower().strip(); pw=d.get('password',''); role=d.get('role','customer')
                    if not name or '@' not in email or len(pw)<8 or role not in ('customer','farmer'):self.send(400,{'error':'Enter a name, valid email, password of at least 8 characters, and account type.'});return
                    try:c.execute('INSERT INTO users(name,email,phone,password,role) VALUES(?,?,?,?,?)',(name,email,d.get('phone',''),hashlib.sha256(pw.encode()).hexdigest(),role))
                    except sqlite3.IntegrityError:self.send(409,{'error':'That email already has an account.'});return
                    self.send(201,{'message':'Account created. You can sign in now.'});return
                if path=='/api/login' and method=='POST':
                    u=c.execute('SELECT * FROM users WHERE email=? AND password=? AND active=1',(d.get('email','').lower().strip(),hashlib.sha256(d.get('password','').encode()).hexdigest())).fetchone()
                    if not u:self.send(401,{'error':'Email or password was not recognized.'});return
                    code=f'{secrets.randbelow(1000000):06d}'; c.execute('INSERT OR REPLACE INTO otp(email,code,expires) VALUES(?,?,?)',(u['email'],code,int(time.time())+300)); self.send(200,{'message':'Demo verification code created.','demo_otp':code});return
                if path=='/api/verify' and method=='POST':
                    row=c.execute('SELECT * FROM otp WHERE email=? AND code=? AND expires>?',(d.get('email','').lower().strip(),d.get('otp',''),int(time.time()))).fetchone()
                    if not row:self.send(401,{'error':'Code is invalid or expired.'});return
                    c.execute('DELETE FROM otp WHERE email=?',(row['email'],)); u=c.execute('SELECT * FROM users WHERE email=?',(row['email'],)).fetchone(); token=secrets.token_urlsafe(32); c.execute('INSERT INTO sessions VALUES(?,?,?)',(token,u['id'],int(time.time())+86400)); self.send(200,{'token':token,'user':{k:u[k] for k in ('id','name','email','phone','role','wallet')}});return
                if path=='/api/logout':
                    c.execute('DELETE FROM sessions WHERE token=?',(self.headers.get('Authorization','').replace('Bearer ',''),)); self.send(200,{'ok':True});return
                if path=='/api/cart' and method=='POST':
                    u=self.auth(c,'customer'); p=c.execute('SELECT * FROM products WHERE id=? AND stock>0',(d.get('product_id'),)).fetchone()
                    if not p:self.send(404,{'error':'Product is unavailable.'});return
                    qty=max(1,min(99,int(d.get('quantity',1)))); old=c.execute('SELECT quantity FROM carts WHERE user_id=? AND product_id=?',(u['id'],p['id'])).fetchone(); qty+=old['quantity'] if old else 0; qty=min(qty,p['stock']); c.execute('INSERT OR REPLACE INTO carts VALUES(?,?,?)',(u['id'],p['id'],qty)); self.send(200,{'ok':True});return
                if path.startswith('/api/cart/') and method in ('PUT','DELETE'):
                    u=self.auth(c,'customer'); pid=int(path.rsplit('/',1)[-1])
                    if method=='DELETE':c.execute('DELETE FROM carts WHERE user_id=? AND product_id=?',(u['id'],pid))
                    else:
                        p=c.execute('SELECT stock FROM products WHERE id=?',(pid,)).fetchone(); qty=max(1,min(int(d.get('quantity',1)),p['stock'] if p else 1)); c.execute('UPDATE carts SET quantity=? WHERE user_id=? AND product_id=?',(qty,u['id'],pid))
                    self.send(200,{'ok':True});return
                if path=='/api/addresses' and method=='POST':
                    u=self.auth(c,'customer'); aid=c.execute('INSERT INTO addresses(user_id,label,address,city,postal) VALUES(?,?,?,?,?)',(u['id'],d.get('label','Home'),d.get('address',''),d.get('city',''),d.get('postal',''))).lastrowid; self.send(201,{'id':aid});return
                if path=='/api/checkout' and method=='POST':
                    u=self.auth(c,'customer'); items=c.execute('SELECT p.*,ca.quantity FROM carts ca JOIN products p ON p.id=ca.product_id WHERE ca.user_id=?',(u['id'],)).fetchall()
                    if not items:self.send(400,{'error':'Your cart is empty.'});return
                    for p in items:
                        if p['stock']<p['quantity']:self.send(400,{'error':p['name']+' does not have enough stock.'});return
                    addr=c.execute('SELECT * FROM addresses WHERE id=? AND user_id=?',(d.get('address_id'),u['id'])).fetchone()
                    if not addr:self.send(400,{'error':'Choose a shipping address first.'});return
                    total=sum(p['price']*p['quantity'] for p in items)
                    if u['wallet']<total:self.send(400,{'error':'Wallet balance is too low for this demo checkout.'});return
                    oid=c.execute('INSERT INTO orders(user_id,address_id,total) VALUES(?,?,?)',(u['id'],addr['id'],total)).lastrowid
                    for p in items:c.execute('INSERT INTO order_items(order_id,product_id,product_name,price,quantity) VALUES(?,?,?,?,?)',(oid,p['id'],p['name'],p['price'],p['quantity'])); c.execute('UPDATE products SET stock=stock-? WHERE id=?',(p['quantity'],p['id']))
                    c.execute('UPDATE users SET wallet=wallet-? WHERE id=?',(total,u['id'])); c.execute('DELETE FROM carts WHERE user_id=?',(u['id'],)); self.send(201,{'order_id':oid,'total':total});return
                if path=='/api/wallet' and method=='POST':
                    u=self.auth(c,'customer'); amount=float(d.get('amount',0))
                    if not 1<=amount<=100000:self.send(400,{'error':'Choose a top-up amount from $1 to $100,000.'});return
                    c.execute('UPDATE users SET wallet=wallet+? WHERE id=?',(amount,u['id'])); self.send(200,{'wallet':u['wallet']+amount});return
                if path=='/api/farmer/products' and method=='POST':
                    u=self.auth(c,'farmer'); self.product(c,u,d);return
                if path.startswith('/api/farmer/products/'):
                    u=self.auth(c,'farmer'); pid=int(path.rsplit('/',1)[-1]); p=c.execute('SELECT * FROM products WHERE id=? AND farmer_id=?',(pid,u['id'])).fetchone()
                    if not p:self.send(404,{'error':'Product not found in your listings.'});return
                    if method=='DELETE':c.execute('DELETE FROM products WHERE id=?',(pid,)); self.send(200,{'ok':True});return
                    if method=='PUT':self.product(c,u,d,pid);return
                if path.startswith('/api/farmer/orders/') and method=='PUT':
                    u=self.auth(c,'farmer'); oid=int(path.rsplit('/',1)[-1]); status=d.get('status')
                    if status not in ('Preparing','Shipped','Delivered','Cancelled'):self.send(400,{'error':'Choose a valid shipping status.'});return
                    owned=c.execute('SELECT DISTINCT o.id FROM orders o JOIN order_items i ON i.order_id=o.id JOIN products p ON p.id=i.product_id WHERE o.id=? AND p.farmer_id=?',(oid,u['id'])).fetchone()
                    if not owned:self.send(404,{'error':'Order not found.'});return
                    c.execute('UPDATE order_items SET shipping=? WHERE order_id=? AND product_id IN (SELECT id FROM products WHERE farmer_id=?)',(status,oid,u['id'])); c.execute('UPDATE orders SET status=? WHERE id=?',(status,oid)); self.send(200,{'ok':True});return
                self.send(404,{'error':'Not found'})
        except ValueError as e:self.send(401,{'error':str(e)})
        except Exception as e:self.send(400,{'error':str(e)})
    def product(self,c,u,d,pid=None):
        name=d.get('name','').strip(); category=d.get('category','Seeds'); desc=d.get('description','').strip(); price=float(d.get('price',0)); stock=max(0,int(d.get('stock',0))); unit=d.get('unit','each'); image=d.get('image','')
        if not name or not desc or price<=0:self.send(400,{'error':'Enter product name, description, and a price above zero.'});return
        if image.startswith('data:') and len(image)>1500000:self.send(400,{'error':'Image must be under 1.5 MB.'});return
        if pid:c.execute('UPDATE products SET name=?,category=?,description=?,price=?,unit=?,stock=?,image=? WHERE id=? AND farmer_id=?',(name,category,desc,price,unit,stock,image,pid,u['id']))
        else:c.execute('INSERT INTO products(farmer_id,name,category,description,price,unit,stock,image) VALUES(?,?,?,?,?,?,?,?)',(u['id'],name,category,desc,price,unit,stock,image))
        self.send(200,{'ok':True})

if __name__=='__main__':
    init(); print('AgriMart running at http://localhost:8007'); ThreadingHTTPServer(('127.0.0.1',8007),Handler).serve_forever()
