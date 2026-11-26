/* Campus Library demo. Uses localStorage; do not use for real credentials or production data. */
(() => {
  const $ = (s, root=document) => root.querySelector(s);
  const $$ = (s, root=document) => [...root.querySelectorAll(s)];
  const KEY = "campusLibraryDataV1";
  const COLORS = ["cover-purple","cover-peach","cover-green","cover-blue","cover-yellow","cover-pink"];
  const initial = {
    users: [{id:"admin-1",name:"Library Admin",email:"admin@library.demo",password:"admin123",role:"admin"}],
    books: [
      {id:"b1",title:"Introduction to Algorithms",author:"Thomas H. Cormen",isbn:"9780262046305",category:"Computer Science",copies:4,shelf:"A-01"},
      {id:"b2",title:"Clean Code",author:"Robert C. Martin",isbn:"9780132350884",category:"Software Engineering",copies:3,shelf:"A-02"},
      {id:"b3",title:"Database System Concepts",author:"Abraham Silberschatz",isbn:"9780078022159",category:"Database",copies:5,shelf:"B-01"},
      {id:"b4",title:"Artificial Intelligence: A Modern Approach",author:"Stuart Russell",isbn:"9780134610993",category:"Artificial Intelligence",copies:2,shelf:"A-03"},
      {id:"b5",title:"The Pragmatic Programmer",author:"David Thomas",isbn:"9780135957059",category:"Software Engineering",copies:3,shelf:"A-04"},
      {id:"b6",title:"Python Crash Course",author:"Eric Matthes",isbn:"9781718502703",category:"Programming",copies:4,shelf:"C-01"},
      {id:"b7",title:"Hands-On Machine Learning",author:"Aurélien Géron",isbn:"9781098125974",category:"Machine Learning",copies:2,shelf:"C-02"},
      {id:"b8",title:"Operating System Concepts",author:"Abraham Silberschatz",isbn:"9781119800361",category:"Operating Systems",copies:3,shelf:"B-02"}
    ],
    loans: [],
    materials: [
      {id:"m1",title:"Programming Fundamentals — Unit 1",subject:"Programming",year:"1",semester:"1",content:"Programming fundamentals\\n\\n1. Algorithms and flowcharts\\n2. Variables and data types\\n3. Operators and expressions\\n4. Control statements\\n\\nUse this note as a starter guide and add your class material."},
      {id:"m2",title:"Database Management — Revision Notes",subject:"DBMS",year:"2",semester:"3",content:"DBMS revision notes\\n\\n1. Relational model\\n2. Keys and constraints\\n3. SQL operations\\n4. Normalization\\n5. Transactions and ACID properties"},
      {id:"m3",title:"Data Structures — Quick Reference",subject:"Data Structures",year:"2",semester:"4",content:"Data structures quick reference\\n\\nArrays, linked lists, stacks, queues, trees, graphs, hashing, searching and sorting."},
      {id:"m4",title:"Machine Learning — Unit 1",subject:"Machine Learning",year:"3",semester:"5",content:"Machine Learning introduction\\n\\nSupervised learning, unsupervised learning, classification, regression, training/test split and evaluation metrics."},
      {id:"m5",title:"AI — Search Algorithms",subject:"Artificial Intelligence",year:"3",semester:"6",content:"Search algorithms\\n\\nBreadth-first search, depth-first search, uniform-cost search, greedy best-first search and A* search."},
      {id:"m6",title:"Project Documentation Template",subject:"Project Work",year:"4",semester:"7",content:"Project report outline\\n\\nAbstract, introduction, problem statement, objectives, literature review, system design, implementation, testing, results, conclusion and references."}
    ],
    messages: []
  };
  let db = loadDB(), toastTimer;
  function loadDB(){ try { const d=JSON.parse(localStorage.getItem(KEY)); return d && d.users && d.books && d.materials ? d : structuredClone(initial); } catch { return structuredClone(initial); } }
  function saveDB(){ localStorage.setItem(KEY, JSON.stringify(db)); }
  function currentUser(){ try { const id=sessionStorage.getItem("campusLibraryUser"); return db.users.find(u=>u.id===id)||null; } catch { return null; } }
  function isAdmin(){ return currentUser()?.role==="admin"; }
  function uid(prefix="id"){ return prefix+"-"+Date.now().toString(36)+"-"+Math.random().toString(36).slice(2,7); }
  function esc(s=""){ return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
  function fmtDate(v){ if(!v)return "—"; return new Date(v+"T00:00:00").toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"}); }
  function iso(d=new Date()){return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;}
  function addDays(date,days){const d=new Date(date+"T00:00:00");d.setDate(d.getDate()+Number(days));return iso(d);}
  function dayDiff(due, from=iso()){return Math.max(0,Math.floor((new Date(from+"T00:00:00")-new Date(due+"T00:00:00"))/86400000));}
  function fineFor(loan){return dayDiff(loan.dueDate,loan.returnedDate||iso())*5;}
  function available(book){return book.copies-db.loans.filter(l=>l.bookId===book.id&&!l.returnedDate).length;}
  function toast(msg){const el=$("#toast");if(!el)return;el.textContent=msg;el.classList.add("show");clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove("show"),3200);}
  function status(text){const c=text.toLowerCase().replace(/\s/g,"-");return `<span class="status ${c}">${esc(text)}</span>`;}
  function bookById(id){return db.books.find(b=>b.id===id);}
  function userById(id){return db.users.find(u=>u.id===id);}
  function userLoans(userId){return db.loans.filter(l=>l.userId===userId);}
  function bookIcon(category){const c=(category||"").toLowerCase();if(c.includes("computer")||c.includes("program"))return "💻";if(c.includes("artificial")||c.includes("machine"))return "🧠";if(c.includes("database"))return "🗄️";if(c.includes("software"))return "⚙️";if(c.includes("operating"))return "🖥️";return "📘";}
  function fillCategory(select,books){if(!select)return;const old=select.value;const cats=[...new Set(books.map(b=>b.category))].sort();select.innerHTML='<option value="">All categories</option>'+cats.map(c=>`<option>${esc(c)}</option>`).join("");select.value=cats.includes(old)?old:"";}
  function renderPublicBooks(){
    const grid=$("#bookGrid"); if(!grid)return;
    const q=($("#bookSearch")?.value||"").toLowerCase(),cat=$("#categoryFilter")?.value||"",avail=$("#availabilityFilter")?.value||"";
    const filtered=db.books.filter(b=>[b.title,b.author,b.category,b.isbn].join(" ").toLowerCase().includes(q)&&(!cat||b.category===cat)&&(!avail||(avail==="Available"?available(b)>0:available(b)===0)));
    $("#statBooks").textContent=db.books.length;$("#statMaterials").textContent=db.materials.length;$("#bookCount").textContent=`${filtered.length} book${filtered.length===1?"":"s"}`;
    grid.innerHTML=filtered.map((b,i)=>`<article class="book-card"><div class="book-cover ${COLORS[i%COLORS.length]}"><span class="cover-icon">${bookIcon(b.category)}</span></div><div class="book-info"><span class="book-category">${esc(b.category)}</span><h3>${esc(b.title)}</h3><div class="book-author">by ${esc(b.author)}</div><div class="book-meta"><span>${available(b)} of ${b.copies} available</span>${status(available(b)>0?"Available":"Issued")}</div><button class="card-action" data-book-detail="${b.id}">View book details →</button></div></article>`).join("");
    $("#noBooks")?.classList.toggle("hidden",filtered.length>0);
    fillCategory($("#categoryFilter"),db.books);
  }
  function renderMaterials(target,yearSel,semSel){
    const grid=$(target);if(!grid)return;
    const y=$(yearSel)?.value||"",s=$(semSel)?.value||"";
    const ms=db.materials.filter(m=>(!y||m.year===y)&&(!s||m.semester===s));
    grid.innerHTML=ms.map(m=>`<article class="material-card"><div class="material-icon">📄</div><div><h3>${esc(m.title)}</h3><p>${esc(m.subject)} · Year ${esc(m.year)} · Semester ${esc(m.semester)}</p><span class="material-tag">YEAR ${esc(m.year)} · SEM ${esc(m.semester)}</span><br><a class="download-link" href="#" data-download-material="${m.id}">↓ Download notes</a></div></article>`).join("")||'<p class="muted">No materials found for this year and semester.</p>';
  }
  function showAuth(mode="login"){
    const modal=$("#authModal");if(!modal)return;
    modal.classList.remove("hidden");setAuthMode(mode);
  }
  function setAuthMode(mode){
    $$(".auth-tab").forEach(b=>b.classList.toggle("active",b.dataset.mode===mode));
    $("#authTitle").textContent=mode==="login"?"Login to your account":"Create a student account";
    $("#authSubtitle").textContent=mode==="login"?"Access your books and study materials.":"Register to search books and manage your reading history.";
    $("#nameField").classList.toggle("hidden",mode!=="register");$("#roleField").classList.toggle("hidden",mode==="register");
    $("#authName").required=mode==="register";$("#authRole").value="student";$("#authSubmit").textContent=mode==="login"?"Login →":"Create account →";
    $("#authPassword").autocomplete=mode==="login"?"current-password":"new-password";
  }
  function authSubmit(e){
    e.preventDefault();const mode=$(".auth-tab.active")?.dataset.mode||"login",email=$("#authEmail").value.trim().toLowerCase(),password=$("#authPassword").value;
    if(mode==="register"){
      const name=$("#authName").value.trim();if(!name){toast("Enter your full name.");return;}
      if(db.users.some(u=>u.email.toLowerCase()===email)){toast("An account with this email already exists.");return;}
      const u={id:uid("student"),name,email,password,role:"student"};db.users.push(u);saveDB();sessionStorage.setItem("campusLibraryUser",u.id);location.href="dashboard.html";return;
    }
    const role=$("#authRole").value;const u=db.users.find(u=>u.email.toLowerCase()===email&&u.password===password&&u.role===role);
    if(!u){toast("Login failed. Check your email, password and role.");return;}
    sessionStorage.setItem("campusLibraryUser",u.id);location.href="dashboard.html";
  }
  function renderPublicDetail(id){
    const b=bookById(id);if(!b)return;
    $("#bookDetailContent").innerHTML=`<div class="detail-cover ${COLORS[db.books.indexOf(b)%COLORS.length]}">${bookIcon(b.category)}</div><span class="eyebrow">BOOK DETAILS</span><h2>${esc(b.title)}</h2><p class="muted">Written by ${esc(b.author)}</p><div class="detail-grid"><div class="detail-item"><span>Category</span><strong>${esc(b.category)}</strong></div><div class="detail-item"><span>ISBN</span><strong>${esc(b.isbn)}</strong></div><div class="detail-item"><span>Availability</span><strong>${available(b)} / ${b.copies} copies</strong></div><div class="detail-item"><span>Shelf location</span><strong>${esc(b.shelf||"Ask librarian")}</strong></div></div><p class="muted">To borrow this book, sign in and ask the librarian to issue it to your account.</p><button class="btn btn-primary full-width" id="detailLogin">Login to your account →</button>`;
    $("#bookModal").classList.remove("hidden");$("#detailLogin").onclick=()=>{ $("#bookModal").classList.add("hidden");showAuth("login");};
  }
  function initPublic(){
    if(!$("#bookGrid"))return;
    $("#yearNow").textContent=new Date().getFullYear();
    $("#bookSearch").addEventListener("input",renderPublicBooks);$("#categoryFilter").addEventListener("change",renderPublicBooks);$("#availabilityFilter").addEventListener("change",renderPublicBooks);
    $("#yearFilter").addEventListener("change",()=>renderMaterials("#materialGrid","#yearFilter","#semesterFilter"));$("#semesterFilter").addEventListener("change",()=>renderMaterials("#materialGrid","#yearFilter","#semesterFilter"));
    $("#loginNav").onclick=()=>showAuth("login");$("#heroLogin").onclick=()=>showAuth("login");$("#registerNav").onclick=()=>showAuth("register");
    $("#closeAuth").onclick=()=>$("#authModal").classList.add("hidden");$("#closeBook").onclick=()=>$("#bookModal").classList.add("hidden");
    $$(".auth-tab").forEach(b=>b.onclick=()=>setAuthMode(b.dataset.mode));$("#authForm").addEventListener("submit",authSubmit);
    $("#contactForm").addEventListener("submit",e=>{e.preventDefault();db.messages.push({id:uid("msg"),...Object.fromEntries(new FormData(e.currentTarget).entries()),date:iso()});saveDB();e.currentTarget.reset();toast("Message saved in this demo. Thank you!");});
    renderPublicBooks();renderMaterials("#materialGrid","#yearFilter","#semesterFilter");
  }
  function renderDashboard(){
    const u=currentUser();if(!u){location.href="index.html";return;}
    document.body.classList.toggle("is-admin",u.role==="admin");
    $("#welcomeUser").textContent=`${u.name} · ${u.role==="admin"?"Librarian admin":"Student"}`;
    $("#todayLabel").textContent=new Date().toLocaleDateString("en-IN",{weekday:"short",day:"numeric",month:"short",year:"numeric"});
    $$(".admin-only").forEach(el=>el.classList.toggle("hidden",u.role!=="admin"));
    fillCategory($("#dashCategory"),db.books);
    renderOverview();renderDashCatalog();renderManageBooks();renderIssues();renderHistory();renderFines();renderMaterials("#dashMaterialGrid","#dashYear","#dashSemester");renderMaterials("#manageMaterialGrid","#__noneYear","#__noneSemester");renderProfile();
    $("#dashBookSearch").oninput=renderDashCatalog;$("#dashCategory").onchange=renderDashCatalog;
    $("#dashYear").onchange=()=>renderMaterials("#dashMaterialGrid","#dashYear","#dashSemester");$("#dashSemester").onchange=()=>renderMaterials("#dashMaterialGrid","#dashYear","#dashSemester");
    $$(".side-link").forEach(btn=>btn.addEventListener("click",()=>showPage(btn.dataset.page)));
    $$("[data-jump]").forEach(btn=>btn.addEventListener("click",()=>showPage(btn.dataset.jump)));
    $("#logoutBtn").onclick=()=>{sessionStorage.removeItem("campusLibraryUser");location.href="index.html";};
    $("#bookForm").onsubmit=saveBookForm;$("#cancelBookEdit").onclick=resetBookForm;$("#issueForm").onsubmit=issueBook;
    $("#materialForm").onsubmit=addMaterial;$("#profileForm").onsubmit=saveProfile;
  }
  function showPage(page){
    if(["manageBooks","issues","manageMaterials"].includes(page)&&!isAdmin()){toast("This section is for the librarian admin.");return;}
    $$(".dash-page").forEach(p=>p.classList.toggle("hidden",p.id!=="page-"+page));
    $$(".side-link").forEach(b=>b.classList.toggle("active",b.dataset.page===page));
    const names={overview:"Overview",catalog:"Book catalog",manageBooks:"Manage books",issues:"Issue / return books",myBooks:"My borrow history",fines:"Fine status",materials:"Study materials",manageMaterials:"Manage materials",profile:"My profile"};
    $("#dashboardHeading").textContent=names[page]||"Overview";
    $("#dashboardSub").textContent=page==="overview"?"A quick view of your library activity.":`Manage your ${names[page]?.toLowerCase()||"library"} information here.`;
    if(page==="manageBooks")renderManageBooks();if(page==="issues")renderIssues();if(page==="myBooks")renderHistory();if(page==="fines")renderFines();if(page==="catalog")renderDashCatalog();if(page==="materials")renderMaterials("#dashMaterialGrid","#dashYear","#dashSemester");
  }
  function renderOverview(){
    const u=currentUser(),admin=u.role==="admin",loans=admin?db.loans:userLoans(u.id),active=loans.filter(l=>!l.returnedDate),overdue=active.filter(l=>l.dueDate<iso());
    const cards=admin?[["Books in catalog",db.books.length,"▤","All listed titles"],["Registered users",db.users.filter(x=>x.role==="student").length,"♙","Student accounts"],["Currently issued",active.length,"⇄","Active loans"],["Overdue loans",overdue.length,"!","Need attention"]]:[["Books borrowed",loans.length,"▤","Total borrowing records"],["Currently reading",active.length,"◷","Books not yet returned"],["Outstanding fine","₹"+loans.filter(l=>!l.paid).reduce((s,l)=>s+fineFor(l),0),"₹","Calculated at ₹5/day"],["Study materials",db.materials.length,"▧","Resources available"]];
    $("#metrics").innerHTML=cards.map(c=>`<div class="metric-card"><div class="metric-top"><span>${c[0]}</span><span class="metric-icon">${c[2]}</span></div><strong>${c[1]}</strong><small>${c[3]}</small></div>`).join("");
    const recent=[...loans].sort((a,b)=>b.issueDate.localeCompare(a.issueDate)).slice(0,5);
    $("#recentActivity").innerHTML=recent.length?recent.map(l=>{const b=bookById(l.bookId);return `<div class="activity-row"><span class="activity-icon">📘</span><div class="activity-text"><strong>${esc(b?.title||"Deleted book")}</strong><span>${l.returnedDate?"Returned":"Issued"} · ${admin?esc(userById(l.userId)?.name||"Student"):esc(u.name)}</span></div><span class="activity-date">${fmtDate(l.issueDate)}</span></div>`}).join(""):'<p class="muted">No borrowing activity yet. Search the catalog to get started.</p>';
  }
  function renderDashCatalog(){
    const body=$("#dashCatalogRows");if(!body)return;const q=($("#dashBookSearch")?.value||"").toLowerCase(),cat=$("#dashCategory")?.value||"";
    const list=db.books.filter(b=>[b.title,b.author,b.isbn,b.category].join(" ").toLowerCase().includes(q)&&(!cat||b.category===cat));
    body.innerHTML=list.map(b=>`<tr><td><strong>${esc(b.title)}</strong><br><span class="muted">${esc(b.isbn)}</span></td><td>${esc(b.author)}</td><td>${esc(b.category)}</td><td>${b.copies}</td><td>${status(available(b)>0?"Available":"Issued")}</td><td><button class="btn btn-light btn-small" data-view-dash-book="${b.id}">Details</button></td></tr>`).join("")||'<tr><td colspan="6" class="table-empty">No books found.</td></tr>';
  }
  function renderManageBooks(){
    const body=$("#manageBookRows");if(!body)return;
    body.innerHTML=db.books.map(b=>`<tr><td><strong>${esc(b.title)}</strong></td><td>${esc(b.author)}</td><td>${esc(b.isbn)}</td><td>${b.copies}</td><td>${available(b)}</td><td><div class="inline-actions"><button class="btn btn-light" data-edit-book="${b.id}">Edit</button><button class="btn btn-danger" data-delete-book="${b.id}">Delete</button></div></td></tr>`).join("")||'<tr><td colspan="6" class="table-empty">No books added.</td></tr>';
  }
  function saveBookForm(e){
    e.preventDefault();if(!isAdmin())return;
    const id=$("#editBookId").value,book={title:$("#bookTitle").value.trim(),author:$("#bookAuthor").value.trim(),isbn:$("#bookIsbn").value.trim(),category:$("#bookCategory").value.trim(),copies:Number($("#bookCopies").value),shelf:$("#bookShelf").value.trim()};
    if(!book.copies||book.copies<1){toast("Copies must be at least 1.");return;}
    if(id){const old=bookById(id),active=db.loans.filter(l=>l.bookId===id&&!l.returnedDate).length;if(book.copies<active){toast(`Copies cannot be lower than active loans (${active}).`);return;}Object.assign(old,book);toast("Book updated.");}
    else{if(db.books.some(b=>b.isbn===book.isbn)){toast("A book with this ISBN already exists.");return;}db.books.push({id:uid("book"),...book});toast("Book added to inventory.");}
    saveDB();resetBookForm();renderManageBooks();renderDashCatalog();renderOverview();renderPublicBooks();
  }
  function resetBookForm(){if(!$("#bookForm"))return;$("#bookForm").reset();$("#editBookId").value="";$("#bookFormTitle").textContent="Add a book";$("#cancelBookEdit").classList.add("hidden");$("#bookCopies").value=1;}
  function editBook(id){
    const b=bookById(id);if(!b)return;$("#editBookId").value=b.id;$("#bookTitle").value=b.title;$("#bookAuthor").value=b.author;$("#bookIsbn").value=b.isbn;$("#bookCategory").value=b.category;$("#bookCopies").value=b.copies;$("#bookShelf").value=b.shelf||"";$("#bookFormTitle").textContent="Update book";$("#cancelBookEdit").classList.remove("hidden");$("#bookTitle").focus();window.scrollTo({top:0,behavior:"smooth"});
  }
  function deleteBook(id){
    const b=bookById(id);if(!b)return;if(db.loans.some(l=>l.bookId===id&&!l.returnedDate)){toast("Return all active copies before deleting this book.");return;}if(!confirm(`Delete "${b.title}" from the catalog?`))return;
    db.books=db.books.filter(x=>x.id!==id);saveDB();renderManageBooks();renderDashCatalog();renderOverview();renderPublicBooks();toast("Book deleted.");
  }
  function renderIssues(){
    if(!$("#issueRows"))return;
    const students=db.users.filter(u=>u.role==="student");$("#issueStudent").innerHTML=students.map(u=>`<option value="${u.id}">${esc(u.name)} (${esc(u.email)})</option>`).join("")||'<option value="">No students registered</option>';
    const borrowable=db.books.filter(b=>available(b)>0);$("#issueBook").innerHTML=borrowable.map(b=>`<option value="${b.id}">${esc(b.title)} (${available(b)} available)</option>`).join("")||'<option value="">No books available</option>';
    const list=[...db.loans].sort((a,b)=>b.issueDate.localeCompare(a.issueDate));
    $("#issueRows").innerHTML=list.map(l=>{const b=bookById(l.bookId),u=userById(l.userId),fine=fineFor(l);return `<tr><td><strong>${esc(u?.name||"Unknown user")}</strong><br><span class="muted">${esc(u?.email||"")}</span></td><td>${esc(b?.title||"Deleted book")}</td><td>${fmtDate(l.issueDate)}</td><td>${fmtDate(l.dueDate)}</td><td>₹${fine}${l.paid?" · paid":""}</td><td>${l.returnedDate?status("Returned"):`${status(l.dueDate<iso()?"Overdue":"Issued")} <div class="inline-actions"><button class="btn btn-primary" data-return-loan="${l.id}">Return</button><button class="btn btn-light" data-pay-fine="${l.id}">Mark fine paid</button></div>`}</td></tr>`}).join("")||'<tr><td colspan="6" class="table-empty">No books have been issued yet.</td></tr>';
  }
  function issueBook(e){
    e.preventDefault();if(!isAdmin())return;const userId=$("#issueStudent").value,bookId=$("#issueBook").value,days=Number($("#loanDays").value);
    if(!userById(userId)||!bookById(bookId)){toast("Select a registered student and an available book.");return;}
    if(!Number.isInteger(days)||days<1||days>60){toast("Loan period must be 1–60 days.");return;}
    if(available(bookById(bookId))<1){toast("No copies available.");return;}
    db.loans.push({id:uid("loan"),userId,bookId,issueDate:iso(),dueDate:addDays(iso(),days),returnedDate:null,paid:false});saveDB();renderIssues();renderOverview();renderDashCatalog();renderManageBooks();renderHistory();renderFines();renderPublicBooks();toast("Book issued successfully.");
  }
  function returnLoan(id){
    const l=db.loans.find(x=>x.id===id);if(!l||l.returnedDate)return;l.returnedDate=iso();const fine=fineFor(l);saveDB();renderIssues();renderOverview();renderDashCatalog();renderManageBooks();renderHistory();renderFines();renderPublicBooks();toast(fine?`Book returned. Fine due: ₹${fine}.`:"Book returned successfully.");
  }
  function payFine(id){const l=db.loans.find(x=>x.id===id);if(!l)return;if(fineFor(l)===0){l.paid=true;saveDB();renderIssues();renderFines();toast("No fine is due.");return;}l.paid=true;saveDB();renderIssues();renderFines();toast("Fine marked as paid in this demo.");}
  function renderHistory(){
    const body=$("#historyRows");if(!body)return;const u=currentUser(),list=userLoans(u.id).sort((a,b)=>b.issueDate.localeCompare(a.issueDate));
    body.innerHTML=list.map(l=>{const b=bookById(l.bookId),fine=fineFor(l);return `<tr><td><strong>${esc(b?.title||"Deleted book")}</strong></td><td>${fmtDate(l.issueDate)}</td><td>${fmtDate(l.dueDate)}</td><td>${fmtDate(l.returnedDate)}</td><td>₹${fine}${l.paid?" · paid":""}</td><td>${status(l.returnedDate?"Returned":l.dueDate<iso()?"Overdue":"Issued")}</td></tr>`}).join("")||'<tr><td colspan="6" class="table-empty">Your borrowing history will appear here.</td></tr>';
  }
  function renderFines(){
    const u=currentUser();if(!u||!$("#fineRows"))return;const list=(isAdmin()?db.loans:userLoans(u.id)).filter(l=>fineFor(l)>0);
    const total=list.filter(l=>!l.paid).reduce((s,l)=>s+fineFor(l),0),paid=list.filter(l=>l.paid).reduce((s,l)=>s+fineFor(l),0),count=list.filter(l=>!l.paid).length;
    $("#fineMetrics").innerHTML=[["Outstanding fine","₹"+total,"Unpaid overdue charges"],["Fines recorded",list.length,"Loans with overdue days"],["Marked paid","₹"+paid,"Paid records in this demo"]].map((c,i)=>`<div class="metric-card"><div class="metric-top"><span>${c[0]}</span><span class="metric-icon">${["₹","!","✓"][i]}</span></div><strong>${c[1]}</strong><small>${c[2]}</small></div>`).join("");
    $("#fineRows").innerHTML=list.map(l=>{const b=bookById(l.bookId),days=dayDiff(l.dueDate,l.returnedDate||iso());return `<tr><td><strong>${esc(b?.title||"Deleted book")}</strong></td><td>${fmtDate(l.dueDate)}</td><td>${days}</td><td>₹${fineFor(l)}</td><td>${status(l.paid?"Paid":"Unpaid")}</td></tr>`}).join("")||'<tr><td colspan="5" class="table-empty">No overdue fines. Great job!</td></tr>';
  }
  function addMaterial(e){
    e.preventDefault();if(!isAdmin())return;const m={id:uid("material"),title:$("#materialTitle").value.trim(),subject:$("#materialSubject").value.trim(),year:$("#materialYear").value,semester:$("#materialSemester").value,content:$("#materialContent").value.trim()};
    db.materials.unshift(m);saveDB();e.currentTarget.reset();renderMaterials("#dashMaterialGrid","#dashYear","#dashSemester");renderMaterials("#manageMaterialGrid","#__noneYear","#__noneSemester");renderPublicMaterialsIfVisible();toast("Study material added.");
  }
  function renderPublicMaterialsIfVisible(){renderMaterials("#materialGrid","#yearFilter","#semesterFilter");$("#statMaterials")&&($("#statMaterials").textContent=db.materials.length);}
  function downloadMaterial(id){
    const m=db.materials.find(x=>x.id===id);if(!m)return;const content=`${m.title}\nSubject: ${m.subject}\nYear: ${m.year}\nSemester: ${m.semester}\n\n${m.content}\n\nDownloaded from Campus Library demo.`;
    const blob=new Blob([content],{type:"text/plain;charset=utf-8"}),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=m.title.replace(/[^a-z0-9-_]+/gi,"_")+".txt";document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);toast("Material download started.");
  }
  function deleteMaterial(id){if(!isAdmin())return;if(!confirm("Delete this study material?"))return;db.materials=db.materials.filter(m=>m.id!==id);saveDB();renderMaterials("#dashMaterialGrid","#dashYear","#dashSemester");renderMaterials("#manageMaterialGrid","#__noneYear","#__noneSemester");renderPublicMaterialsIfVisible();toast("Material deleted.");}
  function renderProfile(){const u=currentUser();if(!u||!$("#profileForm"))return;$("#profileName").value=u.name;$("#profileEmail").value=u.email;$("#profileRole").value=u.role==="admin"?"Librarian admin":"Student";$("#profileId").value=u.id;$("#profileAvatar").textContent=u.name.trim().charAt(0).toUpperCase();}
  function saveProfile(e){e.preventDefault();const u=currentUser();u.name=$("#profileName").value.trim();saveDB();$("#welcomeUser").textContent=`${u.name} · ${u.role==="admin"?"Librarian admin":"Student"}`;renderProfile();renderOverview();toast("Profile updated.");}
  function handleDelegated(e){
    const t=e.target.closest("button,a");if(!t)return;
    if(t.dataset.bookDetail)renderPublicDetail(t.dataset.bookDetail);
    if(t.dataset.viewDashBook){const b=bookById(t.dataset.viewDashBook);if(b)toast(`${b.title} · ${available(b)} copies available · Shelf ${b.shelf||"not assigned"}`);}
    if(t.dataset.editBook){if(!isAdmin())return;editBook(t.dataset.editBook);}
    if(t.dataset.deleteBook){deleteBook(t.dataset.deleteBook);}
    if(t.dataset.returnLoan){returnLoan(t.dataset.returnLoan);}
    if(t.dataset.payFine){payFine(t.dataset.payFine);}
    if(t.dataset.downloadMaterial){e.preventDefault();downloadMaterial(t.dataset.downloadMaterial);}
    if(t.dataset.deleteMaterial){deleteMaterial(t.dataset.deleteMaterial);}
  }
  document.addEventListener("click",handleDelegated);
  if($("#bookGrid"))initPublic();
  if($("#page-overview"))renderDashboard();
})();