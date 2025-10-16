import os
from datetime import datetime
from flask import Flask, request, jsonify
from database_service import DatabaseService
from validation_service import ValidationService

import logging
logging.basicConfig(level=logging.INFO)
logging.info("זה יופיע בלוגים של Render")

validator = ValidationService()

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

db_path = r"pbx_system.db"

db = DatabaseService(db_path)
call_data = {}

@app.route('/login', methods=['GET'])
def login():
    call_id = request.args.get('PBXcallId', '')
    data = call_data.setdefault(call_id, {})
    tryings = data.setdefault('count', 0)
    phone = request.args.get('PBXphone', '')
    customer = db.get_customer_by_phone(phone)
    if not customer:
        return jsonify({
                    "type": "simpleMenu",
                    "name": "no_customer_login",
                    "times": 1,
                    "timeout": 5,
                    "enabledKeys": "",
                     "setMusic": "no",
                    "extensionChange": "1664",
                    "files": [{"text": "אינכם רשומים למערכת. הינכם מועברים להרשמה"}]
                    }
                    )
    # קבלת קלט מהמשתמש - הערך האחרון
    items = [_ for _ in request.args.items() if _[0] == "password"]
    if len(keys) <= 0:
        return jsonify({
                "type": "getDTMF",
                "name": "password",
                "max": 10,
                "min": 4,
                "timeout": 5,
                "confirmType": "no",
                "files":[{"text": "לכניסה למערכת נא הקש את הסיסמה"}]
                }
                )
    key = items[-1][0]
    value = items[-1][1]

    # אימות סיסמה
    if key == 'password':
        if db.verify_password(phone, value):
            # ניתוב לתפריט לקוחות קיימים
            return jsonify({
                    "type": "extensionChange",
                    "extensionIdChange": "1668"
                }
                )
        else:
            if tryings > 3:
                # מספר נסיונות שגויים גדול מ 4 - הודעת שגיאה
                return jsonify({
                    "type": "simpleMenu",
                    "name": "error_password",
                    "times": 1,
                    "timeout": 5,
                    "enabledKeys": "",
                     "setMusic": "no",
                    "extensionChange": "",
                    "files":[{"text": "יותר מדי נסיונות שגויים. נסו שוב מאוחר יותר"}]
                    }
                    )
            # אם לא - העלה את מונה הנסיונות והמשך לניסיון הבא
            tryings = data['count'] + 1
            return jsonify({
                "type": "getDTMF",
                "name": "password",
                "max": 10,
                "min": 4,
                "timeout": 5,
                "confirmType": "no",
                "files": [{"text": "הסיסמה שגויה. לכניסה למערכת נא הקש את הסיסמה"}]
                }
                )
    else:
        

@app.route('/sign', methods=['GET'])
def sign():
    """
    הפרטים הנדרשים להרשמה:
    טלפון
    שם
    תעודת זהות בעל העסק
    סיסמה
    שם העסק
    תאריך הקמת העסק
    תחום עיסוק
    """
    phone = request.args.get('PBXphone', '')
    call_id = request.args.get('PBXcallId', '')
    data = call_data.setdefault(call_id, {})
    sign_detailes = data.setdefault('sign_detailes', {})

    def fix_sign():
        password = sign_detailes['password']
        name = sign_detailes['name']
        tz = sign_detailes['tz']
        compeny_name = sign_detailes['compeny_name']
        open_compeny = sign_detailes['open_compeny']
        category = sign_detailes['category']
        if all([password, name, tz, compeny_name, open_compeny, category]):
            try:
                db.create_customer(phone, password, name, tz)
                return jsonify(
                    {
                      "type": "simpleMenu",
                      "name": "fix_sign",
                      "times": 1,
                      "timeout": 5,
                      "enabledKeys": "0",
                       "setMusic": "no",
                      "extensionChange": "1664",
                      "files": [{"text": "ההרשמה הושלמה בהצלחה! הנכם מועברים לתפריט הראשי"}]
                    }
                    )
            except Exception as e:
                return jsonify(
                    {
                      "type": "simpleMenu",
                      "name": "error_sign",
                      "times": 1,
                      "timeout": 5,
                      "enabledKeys": "",
                       "setMusic": "no",
                      "extensionChange": "1663",
                      "files": [{"text": "שגיאה בתהליך ההרשמה"}]
                    }
                    )
        else:
            return jsonify(
                    {
                      "type": "simpleMenu",
                      "name": "error_sign",
                      "times": 1,
                      "timeout": 5,
                      "enabledKeys": "",
                       "setMusic": "no",
                      "extensionChange": "1663",
                      "files": [{"text": "שגיאה בתהליך ההרשמה"}]
                    }
                    )
    # קבלת קלט מהמשתמש - הערך האחרון
    for key in ['password', 'category', 'open_compeny', 'compeny_name', 'tz', 'name']:
        if key not in request.args.keys():
            continue
        logging.info(f"===== the key is {key} =====")
        value = request.args[key]
        if key == 'name' and value:
            sign_detailes['name'] = value
            return jsonify({
                    "type": "getDTMF",
                    "name": "tz",
                    "max": 9,
                    "min": 9,
                    "timeout": 5,
                    "confirmType": "no",
                    "files": [{"text": "נא הקש את מספר תעודת הזהות של בעל העסק"}]
                    }
                    )
        elif key == "tz" and value:
            if validator.validate_israeli_id(value):
                sign_detailes['tz'] = value
                return jsonify({
                    "type": "stt",
                    "name": "compeny_name",
                    "max": 4,
                    "min": 1,
                    "fileName": f"compeny_name_{phone}",
                    "files": [{"text": "אמרו בקול ברור את שם העסק"}]
                    }
                    )
            else:
                return jsonify({
                    "type": "getDTMF",
                    "name": "tz",
                    "max": 9,
                    "min": 9,
                    "timeout": 5,
                    "confirmType": "no",
                    "files": [{"text": "מספר תעודת הזהות שהוקש אינו תקין. נא הקש את תעודת הזהות של בעל העסק"}]
                    }
                    )
        elif key == "compeny_name" and value:
            sign_detailes['compeny_name'] = value
            return jsonify({
                    "type": "getDTMF",
                    "name": "open_compeny",
                    "max": 4,
                    "min": 4,
                    "timeout": 5,
                    "confirmType": "digits",
                "files": [{"text": "נא הקש בארבע ספרות את שנת פתיחת העסק"}]
                    }
                    )
        elif key == 'open_compeny' and value:
            if int(datetime.now().year) >= int(value) >= 2000:
                sign_detailes['open_compeny'] = value
                return jsonify({
                    "type": "stt",
                    "name": "category",
                    "max": 4,
                    "min": 2,
                    "fileName": f"compeny_name_{phone}",
                    "files": [{"text": "אמרו בקול ברור את תחום העיסוק"}]
                    }
                    )
            else:
                return jsonify({
                    "type": "getDTMF",
                    "name": "open_compeny",
                    "max": 4,
                    "min": 4,
                    "timeout": 5,
                    "confirmType": "digits",
                    "files": [{"text": "השנה שנבחרה לא תקינה. נא להקיש בארבע ספרות את שנת פתיחת העסק"}]
                    }
                    )
        elif key == 'category' and value:
            sign_detailes['category'] = value
            return jsonify({
                    "type": "getDTMF",
                    "name": "password",
                    "max": 8,
                    "min": 4,
                    "timeout": 5,
                    "confirmType": "digits",
                    "files": [{"text": "נא בחר סיסמה להתחברות למערכת. הסיסמה צריכה להיות באורך של ארבע עד שמונה ספרות"}]
                    }
                    )
        elif key == 'password' and value:
            sign_detailes['password'] = value
            return fix_sign()
    
        elif key == 'fix_sign' and value == '0':
            # הפניה להתחברות לקוח
            return jsonify({
                "type": "extensionChange",
                "extensionIdChange": "1663"
                }
                )
    
       
    return jsonify({
            "type": "stt",
            "name": "name",
            "max": 4,
            "min": 2,
            "fileName": f"name_{phone}",
            "files": [{"text": "אמרו בקול ברור את שם בעל העסק"}]
            }
            )
@app.route('/create_recpt', methods=['GET'])
def create_recpt():
    """
    פרטים נדרשים להוצאת קבלה:
    שם איש קשר
    סכום
    תיאור
    """
    phone = request.args.get('PBXphone', '')
    contact_name = None
    amout = None
    detailes = None
    key = list(request.args.keys())[-1]
    value = request.args[key]
    def send_and_create():
        return jsonify(
                    {
                      "type": "simpleMenu",
                      "name": "fix_create_recpt",
                      "times": 1,
                      "timeout": 5,
                      "enabledKeys": "0",
                       "setMusic": "no",
                      "extensionChange": "",
                      "files": [{"text": "הקבלה הופקה בהצלחה! לחץ אפס לחזרה לתפריט הראשי"
                    }]
                    }

                    )
    if key == 'contact_name' and value:
        contact_name = value
        return jsonify({
                "type": "getDTMF",
                "name": "amout",
                "max": 5,
                "min": 1,
                "timeout": 5,
                "confirmType": "number",
                "files": [{"text": "נא הקש את סכום הקבלה, לנקודה עשרונית לחץ כוכבית"
                }]
        }
                )
    elif key == 'amout' and value:
        amout = eval(value)
        return jsonify({
                "type": "stt",
                "name": "detailes",
                "max": 4,
                "min": 1,
                "fileName": f'detailes {phone}',
                "files": [{"text": "אמרו את תיאור השירות או המוצר"
                }]
        }
                )
    elif key == 'detailes' and value:
        detailes = value
        return jsonify(
                    {
                      "type": "simpleMenu",
                      "name": "show_recpt_detailes",
                      "times": 1,
                      "timeout": 5,
                      "enabledKeys": "1,2",
                       "setMusic": "no",
                      "extensionChange": "",
                      "files": [{"text": f"ביקשתם להפיק קבלה עבור {contact_name}, בסכום של {amout}. תיאור: {detailes}. לאישור הקישו אחת, לתיקון הקישו שתים"
                    }]
                    }

                    )
    elif key == 'show_recpt_detailes':
        if value == '1':
            send_and_create()
        elif value == '2':
            return jsonify({
                    "type": "extensionChange",
                    "extensionIdChange": "create_recpt"
                    }
                    )
    elif key == 'fix_create_recpt' and value == '0':
        # ניתוב לתפריט לקוחות קיימים
        return jsonify({
                "type": "extensionChange",
                "extensionIdChange": "1665"
                }
                )

@app.route('/cancel_recpt', methods=['GET'])
def cancel_recpt():
    pass

@app.route('/add_child', methods=['GET'])
def add_child():
    pass

@app.route('/edit_child', methods=['GET'])
def edit_child():
    pass

@app.route('/get_detailes', methods=['GET'])
def get_detailes():
    pass

@app.route('/edit_profile', methods=['GET'])
def edit_profile():
    pass

@app.route('/end_account', methods=['GET'])
def end_account():
    pass

@app.route('/rights', methods=['GET'])
def rigths():
    pass


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # ברירת מחדל 5000 לוקאלית
    app.run(host="0.0.0.0", port=port)











































