import os
from flask import Flask, request, jsonify
from database_service import DatabaseService
from validation_service import ValidationService

validator = ValidationService()

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

db_path = r"pbx_system.db"

db = DatabaseService(db_path)


@app.route('/new_call', methods=['GET', 'POST'])
def new_call():
    # הדפס את כל הפרמטרים שמגיעים
    print("=== API CALL DEBUG ===")
    print(f"Method: {request.method}")
    print(f"Args: {dict(request.args)}")
    print(f"Form: {dict(request.form)}")
    print(f"Headers: {dict(request.headers)}")
    
    call_id = request.args.get('PBXcallId', '') or request.form.get('PBXcallId', '')
    phone = request.args.get('PBXphone', '') or request.form.get('PBXphone', '')
    
    print(f"Extracted - call_id: '{call_id}', phone: '{phone}'")
    
    # בדוק אם הטלפון בכלל מגיע
    if not phone:
        print("ERROR: No phone number received!")
        return jsonify({"error": "No phone parameter"}), 400
    
    # בדוק את בסיס הנתונים
    customer = db.get_customer_by_phone(phone)
    print(f"Customer lookup result: {customer}")
    
    if customer:
        response = {
                    "type": "simpleMenu",
                    "name": "error_password",
                    "times": 1,
                    "timeout": 0.1,
                    "enabledKeys": "",
                     "setMusic": "no",
                    "extensionChange": "1663",
                    "files":[{"text": ""}]
                    }
                    
        print(f"Sending response for existing customer: {response}")
        return jsonify(response)
    else:
        response = {
                    "type": "simpleMenu",
                    "name": "error_password",
                    "times": 1,
                    "timeout": 0.1,
                    "enabledKeys": "",
                     "setMusic": "no",
                    "extensionChange": "1664",
                    "files":[{"text": ""}]
                    }
        print(f"Sending response for new customer: {response}")
        return jsonify(response)
# @app.route('/new_call', methods=['GET', 'POST'])
# def new_call():
    # # חילוץ פרמטרים
    # call_id = request.args.get('PBXcallId', '')
    # phone = request.args.get('PBXphone', '')
    # # בדיקה אם לקוח קיים לפי מספר טלפון
    # if db.get_customer_by_phone(phone):
    #     # הפניה להתחברות לקוח
    #     return jsonify({
    #         "type": "extensionChange",
    #         "extensionIdChange": "1663"
    #     }
    #     )

    # else:
    #     # ניתוב לתפריט הרשמה
    #     return jsonify({
    #         "type": "extensionChange",
    #         "extensionIdChange": "1664"
    #     }
    #     )


@app.route('/login', methods=['GET']) # מזהה שלוחה 1663
def login():
    count = 0
    phone = request.args.get('PBXphone', '')
    # קבלת קלט מהמשתמש - הערך האחרון
    key = list(request.args.keys())[-1]
    value = request.args[key]

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
            if count > 4:
                # מספר נסיונות שגויים גדול מ 4 - הודעת שגיאה
                return jsonify({
                    "type": "simpleMenu",
                    "name": "error_password",
                    "times": 1,
                    "timeout": 5,
                    "enabledKeys": "",
                     "setMusic": "no",
                    "extensionChange": "",
                    "files":[{"text": "יותר מדי נסיונות שגויים"}]
                    }
                    )
            # אם לא - העלה את מונה הנסיונות והמשך לניסיון הבא
            count += 1
            return jsonify({
                "type": "getDTMF",
                "name": "password",
                "max": 10,
                "min": 4,
                "timeout": 5,
                "enabledKeys": "0,1,2,3,4,5,6,7,8,9,#",
                "confirmType": "no",
                "files": [{"text": "הסיסמה שגויה. לכניסה למערכת נא הקש את הסיסמה"
                }]
            }
                )
    else:
        return jsonify({
                "type": "getDTMF",
                "name": "password",
                "max": 10,
                "min": 4,
                "timeout": 5,
                "enabledKeys": "0,1,2,3,4,5,6,7,8,9,#",
                "confirmType": "no",
                "files": [{"text": "לכניסה למערכת נא הקש את הסיסמה"
                }]
        }
                )

@app.route('/sign', methods=['GET']) # מזהה שלוחה 1664
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
    password = None
    name = None
    tz = None
    compeny_name = None
    open_compeny = None
    category = None

    def fix_sign():
        if all(_ is not None for _ in [password, name, tz, compeny_name, open_compeny, category]):
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
                      "extensionChange": "",
                      "files": [{"text": "ההרשמה הושלמה בהצלחה! לחץ 0 למעבר לתפריט הראשי"
                    }]
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
                      "extensionChange": "",
                      "files": [{"text": "שגיאה בתהליך ההרשמה"
                    }]
                    }

                    )
    # קבלת קלט מהמשתמש - הערך האחרון
    key = list(request.args.keys())[-1]
    value = request.args[key]
    if key == 'name' and value:
        name = value
        return jsonify({
                "type": "getDTMF",
                "name": "tz",
                "max": 9,
                "min": 9,
                "timeout": 5,
                "confirmType": "no",
                "files": [{"text": "נא הקש את תעודת הזהות של בעל העסק"
                }]
        }
                )
    elif key == "tz" and value:
        if validator.validate_israeli_id(value):
            tz = value
            return jsonify({
                "type": "stt",
                "name": "compeny_name",
                "max": 4,
                "min": 1,
                "fileName": f'compeny_name {phone}',
                "files": [{"text": "אמרו בקול ברור את שם העסק"
                }]
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
                "files": [{"text": "מספר תעודת הזהות שהוקש אינו תקין. נא הקש את תעודת הזהות של בעל העסק"
                }]
            }
                )
    elif key == "compeny_name" and value:
        compeny_name = value
        return jsonify({
                "type": "getDTMF",
                "name": "open_compeny",
                "max": 4,
                "min": 4,
                "timeout": 5,
                "confirmType": "digits",
                "files": [{"text": "נא הקש את תאריך פתיחת העסק בארבע ספרות, שתי ספרות עבור החודש, ושתי ספרות עבור השנה"
                }]
        }
                )
    elif key == 'open_compeny' and value:
        month, year = value[:2], value[2:]
        if 1 <= int(month) <= 12:
            open_compeny = f"{month}/{year}"
            return jsonify({
                "type": "stt",
                "name": "category",
                "max": 4,
                "min": 1,
                "fileName": f'compeny_name {phone}',
                "files": [{"text": "אמרו בקול ברור את תחום העיסוק"
                }]
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
                "files": [{"text": "התאריך שהוקש לא תקין. נא הקש את תאריך פתיחת העסק בארבע ספרות, שתי ספרות עבור החודש, ושתי ספרות עבור השנה"
                }]
            }
                )
    elif key == 'category' and value:
        category = value
        return jsonify({
                "type": "getDTMF",
                "name": "password",
                "max": 8,
                "min": 4,
                "timeout": 5,
                "confirmType": "digits",
                "files": [{"text": "נא בחר סיסמה להתחברות למערכת. הסיסמה צריכה להיות באורך של ארבע עד שמונה ספרות"
                }]
        }
                )
    elif key == 'password' and value:
        password = value
        return fix_sign()

    elif key == 'fix_sign' and value == '0':
        # הפניה להתחברות לקוח
        return jsonify({
            "type": "extensionChange",
            "extensionIdChange": "1663"
            }
            )

    else:
        return jsonify({
                "type": "stt",
                "name": "name",
                "max": 4,
                "min": 1,
                "fileName": f'name {phone}',
                "files": [{"text": "אמרו בקול ברור את שם בעל העסק"
                }]
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






















