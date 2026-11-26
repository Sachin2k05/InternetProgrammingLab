# Campus Library — Internet Programming Lab

A responsive Library Management System built with **HTML, CSS and vanilla JavaScript**. It runs directly in a browser and requires no server or package installation.

## Run the project
1. Extract `library_management_system.zip`.
2. Open `index.html` in Chrome, Edge, or Firefox.
3. Click **Login** to enter the demo admin account, or register a student account.

### Demo librarian login
- Email: `admin@library.demo`
- Password: `admin123`
- Choose **Librarian admin** in the login role dropdown.

## Features included
### Public website
- Search catalog by title, author, category or ISBN
- Filter by category and availability
- View book details and shelf location
- Register and log in
- Study materials filter by year and semester
- Download demo notes as `.txt` files
- Contact form demo

### Librarian admin dashboard
- Add, edit and delete books
- Track total and available copies
- Issue books to registered student accounts
- Record returns and update availability
- Calculate overdue fines at ₹5 per day
- Mark fine records as paid (demo)
- Add and delete year/semester study materials
- Overview of users, inventory, active loans and overdue loans

### Student dashboard
- Search catalog
- View borrowing history with issue date and expected return date
- Check fines
- Download study materials
- Update profile name

## Important limitations
This is a **front-end lab demo**, not a production library system. Data is saved in the current browser using `localStorage`, and the signed-in session uses `sessionStorage`. Passwords are stored in plain text and are not secure. Different browsers/devices do not share data. The contact form stores a local demo record and does not send email. Downloaded resources are generated from text entered in the demo; this is not a real PDF/document upload system.

For a real deployment, use a backend, a database, server-side authentication, hashed passwords, authorization checks, and secure file storage.

## Reset demo data
In the browser developer console, run:
```js
localStorage.removeItem("campusLibraryDataV1");
sessionStorage.removeItem("campusLibraryUser");
location.reload();
```

## Suggested lab demonstration
1. Open the home page and search for “Python”.
2. Register a new student.
3. Log in as the admin in another browser profile or after logging out.
4. Add a book and issue it to the student.
5. Log back in as the student to view borrowing history.
6. Add a study material as admin and download it as student.
7. Return the book as admin and inspect fine status if overdue.
