
# ============================================================================
# 4. services/database_service.py - שירות מסד נתונים מסודר
# ============================================================================

import sqlite3
from typing import Optional, Dict, List
from contextlib import contextmanager
import bcrypt
from datetime import datetime, timedelta
import json

class DatabaseService:
    """שירות גישה למסד נתונים"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()

    @contextmanager
    def get_connection(self):
        """חיבור למסד נתונים עם context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_database(self):
        """אתחול טבלאות"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # טבלת לקוחות
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_number TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    name TEXT,
                    tz TEXT,
                    compny_name TEXT,
                    open_compeny DATE,
                    subscription_start_date DATE,
                    subscription_end_date DATE,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    -- פרטים נוספים לחישוב זכויות
                    num_children INTEGER DEFAULT 0,
                    children_birth_years TEXT, -- JSON array
                    spouse1_workplaces INTEGER DEFAULT 0,
                    spouse2_workplaces INTEGER DEFAULT 0
                )
            """)

            # טבלת אנשי קשר
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    tz TEXT,
                    email TEXT,
                    phone_number TEXT,
                    company_name TEXT,
                    address TEXT,
                    notes TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers (id)
                )
            """)

            # טבלת ילדים
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS children (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    birth_year INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers (id)
                )
            """)

            # טבלת שיחות
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    call_id TEXT UNIQUE NOT NULL,
                    customer_id INTEGER,
                    phone_number TEXT,
                    pbx_data TEXT, -- JSON של כל נתוני המרכזייה
                    call_data TEXT, -- JSON של נתוני השיחה
                    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    ended_at DATETIME,
                    FOREIGN KEY (customer_id) REFERENCES customers (id)
                )
            """)

            # טבלת קבלות - מעודכנת עם חיבור לאנשי קשר
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS receipts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    contact_id INTEGER,
                    call_id TEXT,
                    amount INTEGER NOT NULL,
                    description TEXT,
                    icount_doc_id TEXT,
                    icount_doc_num TEXT,
                    icount_response TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers (id),
                    FOREIGN KEY (contact_id) REFERENCES contacts (id)
                )
            """)

            # טבלת הודעות
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    call_id TEXT,
                    message_text TEXT,
                    message_file TEXT,
                    duration INTEGER,
                    status TEXT DEFAULT 'new',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers (id)
                )
            """)

            conn.commit()

    # פונקציות לקוחות
    def get_customer_by_phone(self, phone_number: str) -> Optional[Dict]:
        """קבלת לקוח לפי טלפון"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM customers WHERE phone_number = ?', (phone_number,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def verify_password(self, phone_number: str, password: str) -> bool:
        """אימות סיסמה"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT password FROM customers WHERE phone_number = ?', (phone_number,))
            row = cursor.fetchone()

            if not row:
                return False

            stored_hash = row['password']
            return bcrypt.checkpw(password.encode(), stored_hash.encode())

    def create_customer(self, phone_number: str, password: str, name: str, tz: str) -> int:
        """יצירת לקוח חדש"""
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO customers 
                (phone_number, password, name, tz, subscription_start_date, subscription_end_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                phone_number, hashed, name, tz,
                datetime.now().strftime('%Y-%m-%d'),
                (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
            ))
            conn.commit()
            return cursor.lastrowid

    def is_subscription_active(self, customer: Dict) -> bool:
        """בדיקת תוקף מנוי"""
        if not customer or not customer.get('subscription_end_date'):
            return False
        end_date = datetime.strptime(customer['subscription_end_date'], '%Y-%m-%d').date()
        return end_date >= datetime.now().date()

    # פונקציות אנשי קשר
    def create_contact(self, customer_id: int, name: str, tz: str = None,
                      email: str = None, phone_number: str = None,
                      company_name: str = None, address: str = None, notes: str = None) -> int:
        """יצירת איש קשר חדש"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO contacts 
                (customer_id, name, tz, email, phone_number, company_name, address, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (customer_id, name, tz, email, phone_number, company_name, address, notes))
            conn.commit()
            return cursor.lastrowid

    def get_customer_contacts(self, customer_id: int) -> List[Dict]:
        """שליפת כל אנשי הקשר של לקוח מסוים"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM contacts 
                WHERE customer_id = ? AND is_active = 1 
                ORDER BY name
            ''', (customer_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_contact_by_id(self, contact_id: int) -> Optional[Dict]:
        """קבלת איש קשר לפי ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM contacts WHERE id = ? AND is_active = 1', (contact_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_contact_by_name(self, name: str) -> Optional[Dict]:
        """קבלת איש קשר לפי ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM contacts WHERE name = ? AND is_active = 1', (name,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_receipts_by_contact(self, contact_id: int) -> List[Dict]:
        """חיפוש קבלות לפי איש קשר מסוים"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.*, c.name as contact_name, c.company_name
                FROM receipts r
                JOIN contacts c ON r.contact_id = c.id
                WHERE r.contact_id = ?
                ORDER BY r.created_at DESC
            ''', (contact_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    # פונקציות ילדים
    def create_child(self, customer_id: int, name: str, birth_year: int) -> int:
        """יצירת רשומת ילד חדשה"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO children (customer_id, name, birth_year)
                VALUES (?, ?, ?)
            ''', (customer_id, name, birth_year))
            conn.commit()
            return cursor.lastrowid

    def get_customer_children(self, customer_id: int) -> List[Dict]:
        """שליפת כל הילדים של לקוח מסוים"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM children 
                WHERE customer_id = ? AND is_active = 1 
                ORDER BY birth_year DESC
            ''', (customer_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_children_ages(self, customer_id: int, reference_year: int = None) -> List[Dict]:
        """החזרת גילאי כל הילדים בשנה הנוכחית (או שנה מסוימת)"""
        if reference_year is None:
            reference_year = datetime.now().year

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, birth_year, 
                       (? - birth_year) as age
                FROM children 
                WHERE customer_id = ? AND is_active = 1 
                ORDER BY birth_year DESC
            ''', (reference_year, customer_id))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def update_contact(self, contact_id: int, **kwargs) -> bool:
        """עדכון פרטי איש קשר"""
        valid_fields = ['name', 'tz', 'email', 'phone_number', 'company_name', 'address', 'notes']
        updates = {k: v for k, v in kwargs.items() if k in valid_fields}

        if not updates:
            return False

        updates['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [contact_id]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'UPDATE contacts SET {set_clause} WHERE id = ?', values)
            conn.commit()
            return cursor.rowcount > 0

    def deactivate_contact(self, contact_id: int) -> bool:
        """השבתת איש קשר (מחיקה רכה)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE contacts SET is_active = 0 WHERE id = ?', (contact_id,))
            conn.commit()
            return cursor.rowcount > 0

    def update_child(self, child_id: int, name: str = None, birth_year: int = None) -> bool:
        """עדכון פרטי ילד"""
        updates = {}
        if name is not None:
            updates['name'] = name
        if birth_year is not None:
            updates['birth_year'] = birth_year

        if not updates:
            return False

        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [child_id]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'UPDATE children SET {set_clause} WHERE id = ?', values)
            conn.commit()
            return cursor.rowcount > 0

    def deactivate_child(self, child_id: int) -> bool:
        """השבתת ילד (מחיקה רכה)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE children SET is_active = 0 WHERE id = ?', (child_id,))
            conn.commit()
            return cursor.rowcount > 0


# הוספת הפונקציות החסרות ל-DatabaseService
# יש להוסיף את הפונקציות האלה לקובץ database_service_updated.py הקיים

    # פונקציות נוספות לאנשי קשר (להוסיף לקובץ הקיים)

    def get_customer_contacts_with_receipts_count(self, customer_id: int) -> List[Dict]:
        """שליפת כל אנשי הקשר של לקוח מסויים עם מספר קבלות לכל איש קשר"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT c.*, 
                       COUNT(r.id) as receipts_count,
                       COALESCE(SUM(r.amount), 0) as total_amount
                FROM contacts c
                LEFT JOIN receipts r ON c.id = r.contact_id
                WHERE c.customer_id = ? AND c.is_active = 1 
                GROUP BY c.id
                ORDER BY c.name
            ''', (customer_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def search_contacts_by_name(self, customer_id: int, search_term: str) -> List[Dict]:
        """חיפוש אנשי קשר לפי שם"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM contacts 
                WHERE customer_id = ? AND is_active = 1 
                AND (name LIKE ? OR company_name LIKE ?)
                ORDER BY name
            ''', (customer_id, f'%{search_term}%', f'%{search_term}%'))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_contact_with_receipts_summary(self, contact_id: int) -> Optional[Dict]:
        """קבלת איש קשר עם סיכום קבלות"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT c.*,
                       COUNT(r.id) as total_receipts,
                       COALESCE(SUM(r.amount), 0) as total_amount,
                       MAX(r.created_at) as last_receipt_date
                FROM contacts c
                LEFT JOIN receipts r ON c.id = r.contact_id
                WHERE c.id = ? AND c.is_active = 1
                GROUP BY c.id
            ''', (contact_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_receipt_for_contact(self, customer_id: int, contact_id: int, amount: int,
                                 description: str = None, call_id: str = None) -> int:
        """יצירת קבלה חדשה לאיש קשר"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO receipts (customer_id, contact_id, call_id, amount, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (customer_id, contact_id, call_id, amount, description))
            conn.commit()
            return cursor.lastrowid

    def get_receipts_by_contact_detailed(self, contact_id: int, limit: int = 10) -> List[Dict]:
        """החזרת קבלות מפורטות של איש קשר מסוים עם פרטי הקשר"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.*, 
                       c.name as contact_name, 
                       c.company_name,
                       c.phone_number as contact_phone,
                       CASE 
                           WHEN r.amount >= 1000 THEN CAST(r.amount/100.0 AS TEXT) || ' ש"ח'
                           ELSE CAST(r.amount AS TEXT) || ' אגורות'
                       END as amount_formatted,
                       DATE(r.created_at) as receipt_date
                FROM receipts r
                JOIN contacts c ON r.contact_id = c.id
                WHERE r.contact_id = ?
                ORDER BY r.created_at DESC
                LIMIT ?
            ''', (contact_id, limit))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    # פונקציה לעדכון הקובץ הקיים
    def backup_contact(self, contact_id: int) -> Optional[Dict]:
        """גיבוי נתוני איש קשר לפני עדכון"""
        return self.get_contact_by_id(contact_id)

    def restore_contact(self, contact_id: int, backup_data: Dict) -> bool:
        """שחזור נתוני איש קשר מגיבוי"""
        if not backup_data:
            return False

        return self.update_contact(
            contact_id,
            name=backup_data.get('name'),
            tz=backup_data.get('tz'),
            email=backup_data.get('email'),
            phone_number=backup_data.get('phone_number'),
            company_name=backup_data.get('company_name'),
            address=backup_data.get('address'),
            notes=backup_data.get('notes')
        )

    def validate_contact_ownership(self, customer_id: int, contact_id: int) -> bool:
        """בדיקה שאיש הקשר שייך ללקוח"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 1 FROM contacts 
                WHERE id = ? AND customer_id = ? AND is_active = 1
            ''', (contact_id, customer_id))
            return cursor.fetchone() is not None

