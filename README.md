# Refinery-Project-Management-System

## Overview

**Refinery-Project-Management-System** is a Python-based desktop application developed for managing refinery engineering and maintenance project data. The application provides a graphical user interface (GUI) built with Tkinter and communicates with a Microsoft SQL Server database through ODBC.

The system implements a modular architecture in which each database table is managed through its own dedicated form. It supports efficient data entry, modification, retrieval, and maintenance while providing a user-friendly interface suitable for engineering and maintenance departments.

---

## Features

- Desktop GUI developed with Tkinter
- Microsoft SQL Server integration
- ODBC database connectivity using pyodbc
- Modular form-based architecture
- Complete CRUD operations
  - Create
  - Read
  - Update
  - Delete
- Data validation
- Treeview-based record browsing
- Automatic form population after record selection
- Transaction management
- Error handling and validation
- Clean separation between database layer and presentation layer

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Programming Language | Python 3 |
| GUI Framework | Tkinter |
| Database | Microsoft SQL Server |
| Database Driver | pyodbc |
| Version Control | Git |
| Repository Hosting | GitHub |

---

## Project Structure

```
Refinery_Project_Python/
│
├── main.py
├── db_connection.py
│
├── projects_form.py
├── equipment_form.py
├── materials_form.py
├── vendors_form.py
├── ...
│
├── requirements.txt
└── README.md
```

Each form manages one database table independently, making the application scalable and easy to maintain.

---

## Database

The application connects to a Microsoft SQL Server database named:

```
Refinery_Project
```

Example tables include:

- PROJECTT
- EQUIPMENT
- MATERIALS
- VENDORS
- WBS_ACTIVITIES

The database is normalized and designed for refinery project management.

---

## Architecture

```
Tkinter GUI
       │
       ▼
Application Logic
       │
       ▼
Database Layer (pyodbc)
       │
       ▼
Microsoft SQL Server
```

This layered architecture separates the presentation, business logic, and data access components.

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/sardaromrani1/Refinery_Project_Python.git

cd Refinery_Project_Python
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
```

Activate it:

Windows

```bash
venv\Scripts\activate
```

Linux/macOS

```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Configure Database Connection

Edit `db_connection.py` and configure your SQL Server instance.

Example:

```python
conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=YOUR_SERVER;"
    "DATABASE=Refinery_Project;"
    "Trusted_Connection=yes;"
)
```

Or use SQL Server Authentication if required.

---

## Running the Application

```bash
python main.py
```

The main menu provides access to all available database forms.

---

## Current Functionality

✔ Add new records

✔ Update existing records

✔ Delete records

✔ View all records

✔ Select records from Treeview

✔ Automatic field population

✔ Database validation

---

## Planned Features

Future enhancements include:

- Advanced search
- Dynamic filtering
- Multi-column sorting
- Export to Excel
- Export to CSV
- PDF reporting
- Dashboard
- Charts
- User authentication
- Role-based authorization
- Audit logging
- Backup and restore
- Dark mode
- Pagination
- Printing
- Advanced validation
- Logging framework

---

## Error Handling

The application includes exception handling for:

- Database connection failures
- SQL execution errors
- Invalid user input
- Missing required fields
- Transaction rollback
- Unexpected runtime exceptions

---

## Development Principles

- Modular design
- Maintainable code
- Reusable components
- Separation of concerns
- Database normalization
- Simple and intuitive GUI
- Extensible architecture

---

## Requirements

- Python 3.10+
- Microsoft SQL Server
- ODBC Driver 17 or newer
- pyodbc
- Tkinter

---

## Future Roadmap

- MVC architecture
- SQLAlchemy integration
- REST API
- Web version (Django/FastAPI)
- Authentication system
- Reporting module
- Unit testing
- CI/CD pipeline
- Docker support
- Cloud deployment

---

## Author

**Sardar Omrani**

Database Engineer

Specializing in:

- Microsoft SQL Server
- Python
- Database Design
- Industrial Maintenance Systems
- Refinery Information Systems

GitHub:
https://github.com/sardaromrani1

LinkedIn:
https://www.linkedin.com/in/sardar-omrani-41882694/

---

## License

This project is released under the MIT License.

---

## Acknowledgements

This project was developed as part of a refinery engineering database management initiative to simplify project administration, improve data integrity, and provide an efficient desktop interface for SQL Server databases.
