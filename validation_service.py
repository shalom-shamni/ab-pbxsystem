
# ============================================================================
# 7. services/validation_service.py - שירות validation
# ============================================================================

import re
from datetime import datetime
from typing import Dict, List, Tuple

class ValidationResult:
    def __init__(self, is_valid: bool, message: str = ""):
        self.is_valid = is_valid
        self.message = message

class ValidationService:
    """שירותי validation שונים"""

    @staticmethod
    def validate_israeli_id(tz: str) -> ValidationResult:
        """בדיקת תקינות ת.ז ישראלי"""
        if not tz.isdigit() or len(tz) != 9:
            return ValidationResult(False, "ת.ז חייב להכיל 9 ספרות")

        # בדיקת ספרת ביקורת
        total = 0
        for i, digit in enumerate(tz[:8]):
            weight = 2 if i % 2 == 1 else 1
            product = int(digit) * weight
            total += product if product < 10 else product - 9

        check_digit = (10 - (total % 10)) % 10
        if check_digit != int(tz[8]):
            return ValidationResult(False, "ת.ז לא תקין")

        return ValidationResult(True)

    @staticmethod
    def validate_name(name: str) -> ValidationResult:
        """בדיקת תקינות שם"""
        name = name.strip()

        if len(name) < 2:
            return ValidationResult(False, "שם קצר מדי")

        if len(name) > 50:
            return ValidationResult(False, "שם ארוך מדי")

        if not re.fullmatch(r"[א-תa-zA-Z ]+", name):
            return ValidationResult(False, "שם יכול להכיל רק אותיות ורווחים")

        return ValidationResult(True)

    @staticmethod
    def validate_password(password: str) -> ValidationResult:
        """בדיקת תקינות סיסמה"""
        if not password.isdigit():
            return ValidationResult(False, "סיסמה חייבת להכיל רק ספרות")

        if not (4 <= len(password) <= 8):
            return ValidationResult(False, "סיסמה חייבת להיות באורך 4-8 ספרות")

        return ValidationResult(True)

    @staticmethod
    def validate_amount(amount: str) -> ValidationResult:
        """בדיקת תקינות סכום"""
        try:
            amount_int = int(amount)
            if amount_int <= 0:
                return ValidationResult(False, "סכום חייב להיות חיובי")
            if amount_int > 999999:
                return ValidationResult(False, "סכום גבוה מדי")
            return ValidationResult(True)
        except ValueError:
            return ValidationResult(False, "סכום לא תקין")

    @staticmethod
    def validate_birth_year(year: str) -> ValidationResult:
        """בדיקת תקינות שנת לידה"""
        try:
            year_int = int(year)
            current_year = datetime.now().year
            if year_int < current_year - 50 or year_int > current_year:
                return ValidationResult(False, "שנת לידה לא סבירה")
            return ValidationResult(True)
        except ValueError:
            return ValidationResult(False, "שנת לידה לא תקינה")
