# FastAPI Library Management System

A modern web-based library management system built with FastAPI.  
Features include user registration and authentication, book catalog management, book assignment and return, email notifications, password reset, user roles (admin, librarian, member), categories, tags, and advanced search/filtering.  
Easily extensible, production-ready, and fully Dockerized for quick deployment.

## Features

- **User Authentication**
  - Registration and login with JWT
  - Email verification and password reset (with email code)
  - User roles: admin, librarian, member
- **Book Management**
  - Add, update, and delete books
  - Assign and return books
  - Track borrowing history and due dates
- **Categories & Tags**
  - Manage categories and tags
  - Assign categories and tags to books
  - Filter/search books by author, category, tag, and availability
- **Notifications**
  - Email reminders for due/overdue books
- **Admin Tools**
  - Change user roles
  - Manage users, categories, and tags
- **Dockerized**
  - Easy deployment with Docker

## Project Structure

```bash
.
├── app
│   ├── crud/                # Database CRUD logic
│   ├── models/              # SQLAlchemy models (User, Book, Category, Tag, etc.)
│   ├── schemas/             # Pydantic schemas for API
│   ├── utils/               # Utility functions (email, reminders, etc.)
│   ├── config/              # Configuration (email, JWT, etc.)
│   └── main.py              # FastAPI entry point
├── env/                     # Virtual environment (not tracked)
├── requirements.txt         # Python dependencies
├── Dockerfile               # Dockerfile for containerization
└── README.md                # Project README file
```

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone git@github.com:cyhssin/library_management.git
   cd library_management
   ```

2. **Install dependencies:**
   ```bash
   python -m venv .env
   source .env/bin/activate
   pip install -r requirements.txt
   ```

3. **Set up your `.env` file:**  
   Copy `.env.example` to `.env` and fill in your secrets (JWT, email, etc).

4. **Initialize the database:**  
   (If using SQLite, tables will be created automatically on first run. For migrations, use Alembic.)

5. **Run the development server:**
   ```bash
   uvicorn app.main:app --reload
   ```

6. **Access the API docs:**  
   [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Docker Setup

1. **Build the Docker image:**
   ```bash
   docker build -t library_management .
   ```

2. **Run the Docker container:**
   ```bash
   docker run -d -p 8000:8000 --env-file .env library_management
   ```

3. **Access the API docs:**  
   [http://localhost:8000/docs](http://localhost:8000/docs)

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

---

Developed by [cyhssin](https://github.com/cyhssin)