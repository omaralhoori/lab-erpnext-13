import time
import sqlite3
from os import path
import re
import json
import requests

def results_service_process():
    # If not exists create results db
    create_results_db()
    create_orders_db()
    while True:
        result_messages = read_results_from_db()
        for res_msg in result_messages:
            is_sent = parse_result_message(message=res_msg[1], machine_type=res_msg[2])
            if is_sent: mark_result_message(result_id=res_msg[0])
            time.sleep(1)
        time.sleep(60)


#------------------------------------results db---------------------------
"""
    DB Results table
     0. result_id
     1. result_msg
     2. machine_type
     3. is_sent
     4. result_date
"""


def create_results_db(db_path='results.db'):
    if path.exists(db_path): return
    print("Creating DB")
    conn = sqlite3.connect(db_path) 
    c = conn.cursor()

    c.execute('''
            CREATE TABLE IF NOT EXISTS results
            (result_id INTEGER PRIMARY KEY AUTOINCREMENT, 
            result_msg TEXT,
            machine_type Text,
            is_sent INTEGER DEFAULT 0,
            result_date TEXT
             )
            ''')    
    conn.commit()
    conn.close()


"""
    DB Orders table
     0. order_id
     1. id
     2. msg
     3. machine
     4. is_sent
     5. result_date
"""

def create_orders_db(db_path='orders.db'):
    if path.exists(db_path): return
    print("Creating DB")
    conn = sqlite3.connect(db_path) 
    c = conn.cursor()

    c.execute('''
            CREATE TABLE IF NOT EXISTS orders
            (order_id INTEGER PRIMARY KEY AUTOINCREMENT, 
            id TEXT,
            msg TEXT,
            machine Text,
            is_sent INTEGER DEFAULT 0,
            result_date TEXT
             )
            ''')    
    conn.commit()
    conn.close()

def connect_db():
    conn = sqlite3.connect("results.db")
    return conn

def read_results_from_db():
    conn= connect_db()
    results = conn.execute(f"""
        SELECT * FROM results WHERE is_sent=0;
    """)
    #result_messages = [{result.name} for result in results]
    result_messages = results.fetchall()
    #result_names = result_messages.keys()
    conn.close()
    return  result_messages#results.fetchall()#, results.keys#.description

def insert_db_result_message(message, machine):
    conn = connect_db()
    conn.execute(f"""
        INSERT INTO results(result_msg, machine_type, result_date)
        VALUES('{message}', "{machine}", datetime('now'))
    """)
    conn.commit()
    conn.close()

def mark_result_message(result_id):
    print("marking results")
    conn = connect_db()
    conn.execute(f"""
       UPDATE results SET is_sent=1
        WHERE result_id={result_id}
    """)
    conn.commit()
    conn.close()


#-----------------------------------------Parsing Messages-------------------------------
def parse_result_message(message, machine_type):
    if machine_type == 'Infinity':
        return parse_infinity_message(message)
    if machine_type == 'sysmex XN':
        return parse_sysmexxn_message(message)
    if machine_type == 'sysmex XP 300':
        return parse_sysmexxp_message(message)
    if machine_type == 'Liaison XL':
        return parse_liaisonxl_message(message)
    if machine_type == 'Ruby CD':
        return parse_rubycd_message(message)

def get_url(site):
    print("sent results to ", site)
    if site == "embassy":
        return "direct-embassy.erp:8085"
    elif site == "lab":
        return "direct-lab.erp:8085"
    else: return site


def is_embassy_order(order):
    return order[0] == "E"


#------------------------------Infinity Parsing-------------------------------------------------------------
def parse_infinity_message(message):
    try:
        results, embassy_results = get_patient_results_infinty(message.encode())
        print(results)
        if len(results) > 0:
            requests.post(f"http://{get_url('lab')}/api/method/erpnext.healthcare.doctype.lab_test.lab_test.receive_infinty_results", data=json.dumps(results))
        if len(embassy_results) > 0:
            requests.post(f"http://{get_url('embassy')}/api/method/erpnext.healthcare.doctype.lab_test.lab_test.receive_infinty_results", data=json.dumps(embassy_results))
        return True
    except:
        print("Cannot Parse Infinity Message: ", message)
        return False


def patient_info_infinty(result, p):
    p_start = result.find(f"P|{p}|")
    if p_start < 0 : return False
    p_end=result.find("||||",p_start)
    if p_end < 0: return False
    patient_data = result[p_start + 4: p_end].split("|")
    if len(patient_data) < 2: return False
    n_p_start = result.find(f"P|{p+1}|")
    return patient_data[0], patient_data[1], p_end,n_p_start

def results_info_infinty(result, p_end, n_p_start):
    res_no = 1
    results = []
    while True:
        if n_p_start > 0:
            r_start = result.find(f"R|{res_no}|",p_end, n_p_start)
        else: r_start = result.find(f"R|{res_no}|",p_end)
        if r_start < 0: break
        r_end = result.find("|||",r_start)
        if r_end < 0: break
        result_data = result[r_start + 4: r_end].split("|")
        if len(result_data) < 2: break
       
        res = {"code": result_data[-2].split("^")[-1], "result": result_data[-1]}
        results.append(res)
        res_no += 1
        if res_no == 200: return []
    return results

def get_patient_results_infinty(res_msg):
    res_msg = re.sub(b'\x17..\r\n\x02.', b'', res_msg)
    res_msg = res_msg.decode()
    p = 1
    results, embassy_results = [], []
    while True:
        res = patient_info_infinty(res_msg, p)
        if not res or res[2] < 0: break
        test_reuslts = results_info_infinty(res_msg, res[2], res[3])
        p += 1
        if len(test_reuslts) == 0: continue
        if is_embassy_order(res[0]):
            embassy_results.append({"order_id": res[0], "file_no": res[1], "results": test_reuslts})
        else:
            results.append({"order_id": res[0], "file_no": res[1], "results": test_reuslts})
        if p == 300:
            return []
    return results, embassy_results


#-----------------------------------Sysmex Parsing----------------------------------------------------------
def parse_sysmexxn_message(message):
    try:
        results, embassy_results = parse_sysmex_msg(message.encode())
        if len(results) > 0:
            requests.post(f"http://{get_url('lab')}/api/method/erpnext.healthcare.doctype.lab_test.lab_test.receive_sysmexxn_results", data=json.dumps(results))
        if len(embassy_results) > 0:
            requests.post(f"http://{get_url('embassy')}/api/method/erpnext.healthcare.doctype.lab_test.lab_test.receive_sysmexxn_results", data=json.dumps(embassy_results))
        return True
    except:
        print("Cannot Parse Sysmexxn Message: ", message)
        return False

def parse_sysmexxp_message(message):
    try:
        results, embassy_results = parse_sysmex_msg(message.encode())
        if len(results) > 0:
            requests.post(f"http://{get_url('lab')}/api/method/erpnext.healthcare.doctype.lab_test.lab_test.receive_sysmexxp_results", data=json.dumps(results))
        if len(embassy_results) > 0:
            requests.post(f"http://{get_url('embassy')}/api/method/erpnext.healthcare.doctype.lab_test.lab_test.receive_sysmexxp_results", data=json.dumps(embassy_results))
        return True
    except:
        print("Cannot Parse Sysmexxp Message: ", message)
        return False


def get_sysmex_order(res_msg, o):
    o_start = res_msg.find(f"O|{o}|")
    if o_start < 0: return False
    o_second_start =  res_msg.find(f"O|{o+1}|")
    o_end = res_msg.find("^B|", o_start)
    if o_end < 0 : return False
    order = res_msg[o_start:o_end ].split("^")[-1].strip()
    return order, o_end, o_second_start

def get_sysmex_results(res_msg, order_start, second_order):
    r = 1
    results = []
    while True:
        if second_order > 0:
            r_start = res_msg.find(f"R|{r}|", order_start, second_order)
        else:
            r_start = res_msg.find(f"R|{r}|", order_start)
        if r_start < 0: break
        result_code = res_msg[r_start: r_start + 30].split("|")
        r += 1
        if len(result_code) < 4: continue
        code = result_code[2].split("^")[4]
        result = result_code[3]
        if result: result = result.replace(" ", "").replace("\n", "")
        results.append({"code": code, "result": result})
        
    return results

def parse_sysmex_msg(res_msg):
    o = 1
    res_msg = res_msg.decode()
    parsed_results = []
    embassy_results = []
    while True:
        order_info = get_sysmex_order(res_msg, o)
        if not order_info: break
        order, o_end, o_second_start = order_info
        results = get_sysmex_results(res_msg,o_end,o_second_start)
        o += 1
        if len(results) == 0: continue
        if is_embassy_order(order):
            embassy_results.append({"order_id": order, "results": results })
        else:
            parsed_results.append({"order_id": order, "results": results })
    print(parsed_results, embassy_results)
    return parsed_results, embassy_results

#----------------------------Liaison Parsing-------------------------------------
def parse_liaisonxl_message(message):
    try:
        results, embassy_results = get_results_liaison(message.encode())
        print("results-----------------------------")
        print(results)
        if len(results) > 0:
            requests.post(f"http://{get_url('lab')}/api/method/erpnext.healthcare.doctype.lab_test.lab_test.receive_lision_results", data=json.dumps(results))
        if len(embassy_results) > 0:
            requests.post(f"http://{get_url('embassy')}/api/method/erpnext.healthcare.doctype.lab_test.lab_test.receive_lision_results", data=json.dumps(embassy_results))
        return True
    except:
        print("Cannot Parse Liaisonxl Message: ", message)
        return False


def get_results_liaison(liason_msg):
    formated_result = []
    embassy_result = []
    result_list = []
    result_msg_list = liason_msg.split(b'\x02')
    result = {}
    found = False
    for res in result_msg_list:
        if len(res) > 1 and res[1] == 79:
            result['order'] = res
            found = True
        if len(res) > 1 and res[1] == 82 and found:
            found = False
            result['result'] = res
            result_list.append(result)
            result = {}
    for result in result_list:
        res = {}
        order_list = result['order'].split(b"|")
        if len(order_list)> 4:
            res['order_id'] = order_list[2].decode()
            test_list =  order_list[4].split(b"^")
            if len(test_list) < 2:
                continue
            res['code'] = test_list[-2].decode()
        else: continue
        res_list = result['result'].split(b"|")
        if len(res_list) > 3:
            res['result'] = res_list[3].decode()
            if is_embassy_order(res.get('order_id')):
                embassy_result.append(res)
            else:
                formated_result.append(res)
    return formated_result, embassy_result


#-----------------------------------Ruby CD----------------------------------------------------------
def parse_rubycd_message(message):
    try:
        results, embassy_results = parse_ruby_cd_msg(message.encode())
        if len(results) > 0:
            requests.post(f"http://{get_url('lab')}/api/method/erpnext.healthcare.doctype.lab_test.lab_test.receive_rubycd_results", data=json.dumps(results))
        if len(embassy_results) > 0:
            requests.post(f"http://{get_url('embassy')}/api/method/erpnext.healthcare.doctype.lab_test.lab_test.receive_rubycd_results", data=json.dumps(embassy_results))
        return True
    except:
        print("Cannot Parse CD Ruby Message: ", message)
        return False

def parse_ruby_cd_msg(msg):
    order_start = 1
    results, embassy_results = [], []
    while True:
        result_start = 1
        order_msg_start = msg.find(f"O|{order_start}|".encode())
        order_msg_end = msg.find(f"O|{order_start+1}|".encode())
        order_msg = msg[order_msg_start:order_msg_end]
        order_id_start = len(f"O|{order_start}|")
        order_id_end = order_msg[order_id_start:].find(b"|")
        order_id = order_msg[order_id_start: order_id_start+order_id_end]
        order_delimiter_index = order_id.find(b"^")
        if order_delimiter_index >= 0:
            order_id = order_id[:order_delimiter_index]
        order_dict = {
            "order_id": order_id.decode(),
            "results": []
        }

        while True:
            result_msg_start = order_msg.find(f"R|{result_start}|".encode())
            result_msg_end = order_msg.find(f"R|{result_start+1}|".encode())
            result_msg = order_msg[result_msg_start:result_msg_end]

            test_result = parse_ruby_cd_result_msg(result_msg, result_start)
            if test_result:
                order_dict['results'].append(test_result)
            result_start += 1
            if result_msg_end == -1: break
        order_start += 1
        if order_id:
            if is_embassy_order(order_id.decode()):
                embassy_results.append(order_dict)
            else:
                results.append(order_dict)
        if order_msg_end == -1: break
    return results, embassy_results

def parse_ruby_cd_result_msg(result_msg, result_num):
    result_id_start = len(f"R|{result_num}|")
    result_msg = result_msg[result_id_start:]
    result_id_end = result_msg.find(b"|")
    result_id = result_msg[:result_id_end]
    result_msg= result_msg[result_id_end + 1:]
    test_name_start = result_id.rfind(b"^")
    test_name = result_id[test_name_start+1:]
    result_end = result_msg.find(b"|")
    result = result_msg[:result_end]
    
    if test_name:
        return {"code":test_name.decode(), "result":result.decode()}