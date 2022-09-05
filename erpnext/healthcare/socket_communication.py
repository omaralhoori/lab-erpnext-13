from ipaddress import ip_address
import socket, errno
from time import sleep

import frappe
import requests
import re, json

import time
import sqlite3

def start_socket():
    print( "------------------------------------------------------------------")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("10.123.4.150", 9090))
        print("Binded")
        s.listen()
        while True:
            try:
                conn, addr = s.accept()
                print("accept")
                with conn:
                    print(f"Connected by {addr}")
                    msg = b''
                    while True:
                        data = conn.recv(1024)
                        msg += data
                        print("msg_received-----------------------------------------------------------------")
                        print(msg)
                        if data == tcode("ENQ"):
                            s.sendall(tcode("ACK"))
                        elif  tcode("EOT") in data:
                            parsed = parse_result_message(msg)
                            msg = b''
                            if not parsed:
                                s.sendall(tcode("NAK"))
                            else:
                                s.sendall(tcode("ACK"))
                        else:
                            s.sendall(tcode("ACK"))
                        if not data:
                            break
                        
            except socket.error as e:
                print(e)
                continue
    except socket.error as e:
        if e.errno == errno.EADDRINUSE:
            print("Port is already in use")
        else:
            print(e)
            start_socket()


def parse_result_message(result_msg):
    print("Parssing===============================")
    result_msg = result_msg.decode()
    p_info = patient_info(result_msg)
    if not p_info : return False
    results = results_info(result_msg)
    if len(results) == 0: return False
    frappe.init(site='lab.erp')
    frappe.connect()
    for test in results:
        query = """ UPDATE `tabNormal Test Result` as ntr 
            INNER JOIN `tabLab Test` as lt ON lt.name=ntr.parent
            INNER JOIN `tabSample Collection` as sc ON sc.name=lt.sample
            INNER JOIN `tabPatient` as p ON p.name=lt.patient
            SET ntr.secondary_uom_result='{result}'
            WHERE sc.collection_serial LIKE '%{order_id}' AND p.patient_number='{file_no}' AND ntr.host_code='{test_code}'
                            """.format(result=test['result'], test_code=test['code'], order_id=p_info[0], file_no=p_info[1])
        frappe.db.sql(query)
    frappe.db.commit()
    frappe.clear_cache()
    frappe.db.close()
    frappe.destroy()

def patient_info(result):
    p_start = result.find("P|1|")
    if p_start < 0 : return False
    p_end=result.find("||||",p_start)
    if p_end < 0: return False
    patient_data = result[p_start + 4: p_end].split("|")
    if len(patient_data) < 2: return False
    return patient_data[0], patient_data[1]

def results_info(result):
    res_no = 1
    results = []
    while True:
        r_start = result.find(f"R|{res_no}|")
        if r_start < 0: break
        r_end = result.find("|||",r_start)
        if r_end < 0: break
        result_data = result[r_start + 4: r_end].split("|")
        if len(result_data) < 2: break
        res = {"code": result_data[0].split("^")[-1], "result": result_data[1]}
        results.append(res)
        res_no += 1
        if res_no == 200: return []
    return results

def bstr(string):
    return string.encode("ascii")

def tcode(symbol):
    if symbol == "ENQ":
        return chr(5).encode("ascii")
    elif symbol == "ACK":
        return chr(6).encode("ascii")
    elif symbol == "EOT":
        return chr(4).encode("ascii")
    elif symbol == "STX":
        return chr(2).encode("ascii")
    elif symbol == "CR":
        return chr(13).encode("ascii")
    elif symbol == "ETX":
        return chr(3).encode("ascii")
    elif symbol == "LF":
        return chr(10).encode("ascii")
    elif symbol == "NAK":
        return chr(15).encode("ascii")

def map_test_code(test_code):
    return '^^^' + test_code


def getCheckSumValue(frame):	
    upper:str = "00"
    num:int = 0
    num1:int = 0
    flag:bool = False
    num2:int = 0
    while num2 < len(frame) :
        num = int.from_bytes(frame[num2].encode(), "big")
        num3: int = num

        if num3 == 2:
            num1 = 0

        elif num3 == 3:
            num1 += num
            flag = True
					
        else:
            if num3 == 23:
                num1 += num
                flag = True
            else:
                num1 += num
					
				
        if not flag:
            num2 +=1
        else:
            break

    if num1 > 0:
        upper = hex(num1 % 256)
        upper = upper[2:].upper()
    
    return "0" + upper if len(upper) == 1   else upper


def send_infinty_msg_order(file_no, dob, gender, sample_id, sample_date, tests, host_code):
    try:
        tests_joined = "\\".join(list(map(map_test_code, tests)))
        msg = tcode("ENQ") + get_msg(file_no, dob, gender, sample_id, sample_date, tests_joined) + tcode("EOT")
        print("receiving msg")
        print(msg)
        db_insert_msg(sample_id, msg.decode(), "infinity")
        return True
    except:
        frappe.msgprint("Unable to receive order")
        return False


def send_infinty_msg_order_old(file_no, dob, gender, sample_id, sample_date, tests, host_code):
    # res = frappe.db.get_value("Host Machine", {"machine_code": host_code}, ["ip_address", "port_no"])
    # if not res:
    #     frappe.throw("Host Machine not defined")
    ip_address, port_no = "127.0.0.1", 9990 # "10.123.4.12", 9091 #
    print("Order receivig")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((ip_address, port_no))
            s.send(tcode("ENQ"))
            data = s.recv(1024)
            print("data recv:" , data)
            tests_joined = "\\".join(list(map(map_test_code, tests)))
            msg = get_msg(file_no, dob, gender, sample_id, sample_date, tests_joined)
            s.sendall(msg)
            # data = s.recv(1024)
            # print("data recv:" , data)
            # data = s.recv(1024)
            # print("data recv:" , data)
            # data = s.recv(1024)
            # print("data recv:" , data)
            s.sendall(tcode("EOT"))
            #recv_msg = s.recv(1024)
            #time.sleep(1)
            recv_msg=data
            s.shutdown(socket.SHUT_RDWR)
            s.close()
            if recv_msg.endswith(tcode('ACK')) :#== tcode('ACK'):
                frappe.msgprint("Order received")
                print("order received")
                return True
            else:
                frappe.msgprint("Unable to receive order")
                print("Unable to send order")
                return False
        except:
            frappe.msgprint("Unable to receive order")
            False

def get_msg(file_no,dob, gender,sample_id, sample_date, tests):
    msg = """H|\\^&|||ASTM-Host|||||PSM||P||18991230000000""".encode()

    msg = tcode("STX") + b"1" + msg + tcode("CR") + tcode("ETX")

    checksum = getCheckSumValue(msg.decode())
    #print(msg.decode())
    msg += checksum.encode()
    msg += tcode("CR") + tcode("LF")

    msg2 = tcode("STX") + f'2P|1||{file_no}||||{dob}|{gender}||||||||||||||||||||||||'.encode() + tcode("CR") + tcode("ETX")

    checksum = getCheckSumValue(msg2.decode())
    msg2 += checksum.encode()
    msg2 += tcode("CR") + tcode("LF")

    msg3 = tcode("STX") + f'3O|1|{sample_id}||{tests}||{sample_date}|{sample_date}||||A||||||||||||||||O'.encode() + tcode("CR") + tcode("ETX")
    checksum = getCheckSumValue(msg3.decode())
    msg3 += checksum.encode()
    msg3 += tcode("CR") + tcode("LF")

    msg4 = tcode("STX") + b'4L|1|F' + tcode("CR") + tcode("ETX")
    checksum = getCheckSumValue(msg4.decode())
    msg4 += checksum.encode()
    msg4 += tcode("CR") + tcode("LF")

    msg = msg + msg2 + msg3 + msg4
    return msg

def prepare_infinty_msg(file_no, dob, gender, sample_id, sample_date, tests):
    msg = """H|\\^&|||ASTM-Host|||||PSM||P||18991230000000"""
    msg= bstr(msg)

    msg = tcode("STX") + b"1" + msg + tcode("CR") + tcode("ETX")

    checksum = getCheckSumValue(msg.decode())
    #print(msg.decode())
    msg += checksum.encode()
    msg += tcode("CR") + tcode("LF")

    msg2 = tcode("STX") + b'2P|1||' + file_no[3:].encode() + b'||||' + dob.encode() + b'|'+ gender.encode() + b'||||||||||||||||||||||||' + tcode("CR") + tcode("ETX")

    checksum = getCheckSumValue(msg2.decode())
    msg2 += checksum.encode()
    msg2 += tcode("CR") + tcode("LF")

    tests_joined = "\\".join(list(map(map_test_code, tests)))

    msg3 = tcode("STX") + b'3O|1|'+ sample_id.encode() + b'||' +  tests_joined.encode() + b'||' + sample_date.encode() + b'|' + sample_date.encode() + b'||||A||||||||||||||||O' + tcode("CR") + tcode("ETX")
    checksum = getCheckSumValue(msg3.decode())
    msg3 += checksum.encode()
    msg3 += tcode("CR") + tcode("LF")

    msg4 = tcode("STX") + b'4L|1|F' + tcode("CR") + tcode("ETX")
    checksum = getCheckSumValue(msg4.decode())
    msg4 += checksum.encode()
    msg4 += tcode("CR") + tcode("LF")

    msg = msg + msg2 + msg3 + msg4
    print(msg)
    return msg

#-----------------------------------Listeners---------------------------------

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

def is_embassy_order(order):
    return order[0] == "E"

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

def start_infinty_listener(ip_address, port):
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((ip_address, port))
                print("listening")
                log_result("infinty", "listening")
                s.listen()
                conn, addr = s.accept()
                with conn:
                    print(f"Connected by {addr}")
                    log_result("infinty",str(addr))
                    msg = b""
                    while True:
                        data = conn.recv(63000)
                        print("data received-------------------------------------------------------")
                        print(data)
                        log_result("infinty",str(data))
                        if not data:
                            break
                        msg += data
                        if data.endswith(chr(4).encode()):                    
                            results, embassy_results = get_patient_results_infinty(msg)
                            if len(results) > 0:
                                requests.post(f"http://{get_url('lab')}/api/method/erpnext.healthcare.doctype.lab_test.lab_test.receive_infinty_results", data=json.dumps(results))
                            if len(embassy_results) > 0:
                                requests.post(f"http://{get_url('embassy')}/api/method/erpnext.healthcare.doctype.lab_test.lab_test.receive_infinty_results", data=json.dumps(embassy_results))
                            msg = b""
                        conn.sendall(chr(6).encode())
        except socket.error:
            print("Socket cannot connect")
            log_result("infinty", "Socket cannot connect")
            sleep(5)
            continue

def get_url(site):
    print("sent results to ", site)
    if site == "embassy":
        return "josante-emb.erp:8002"
    elif site == "lab":
        return "josante-outpatient.erp:8085"
    else: return site

def log_result(log,msg):
    with open(log + "-log.txt", "a") as f:
        f.write(msg + "\n")
        f.close()

#------------------------Read order DB--------------
def connect_db():
    conn = sqlite3.connect("orders.db")
    return conn

def read_orders_from_db(machine):
    conn= connect_db()
    orders = conn.execute(f"""
        SELECT * FROM orders WHERE machine='{machine}' AND is_sent=0;
    """)
    result = [order for order in orders]
    conn.close()
    return result

def db_insert_msg(sample_id, msg, machine):
    conn = connect_db()
    conn.execute(f"""
        INSERT INTO orders(id, msg, machine)
        VALUES("{sample_id}", "{msg}", "{machine}")
    """)
    conn.commit()
    conn.close()

def delete_or_mark_order(order_id, machine):
    conn = connect_db()
    conn.execute(f"""
        UPDATE orders SET is_sent=1 WHERE id='{order_id}' AND machine='{machine}';
    """)
    conn.commit()
    conn.close()

#------------------------infinty orders-------------------
def start_infinty_order_listener(ip_address, port, local_ip, local_port):
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                print(f"Connecting client to {ip_address}:{port}---------------------------")
                log_result("infinty_order",f"Connecting client to {ip_address}:{port}---------------------------")
                try:
                    s.connect((ip_address, port))
                    print(f"Connected")
                    while True:
                        orders = read_orders_from_db("infinity")
                        print(orders)
                        for order in orders:
                            msg = order[1]
                            if msg:
                                log_result("infinty_order",msg)
                                s.sendall(msg.encode())
                                result = s.recv(1024)
                                print("recvvvv--------")
                                print(result)
                                if result.endswith(tcode("ACK")):
                                    print("DELETE ------------------", order[0])
                                    delete_or_mark_order(order[0], 'infinity')
                                    time.sleep(2)
                        time.sleep(60)

                except socket.error:
                    print('Unable to connect')
                    log_result("infinty_order",'Unable to connect')
                    time.sleep(10)
                    pass
        except:
            continue

def start_infinty_order_listener_old(ip_address, port, local_ip, local_port):
    # res = frappe.db.get_value("Host Machine", {"machine_code": host_code}, ["ip_address", "port_no"])
    # if not res:
    #     frappe.throw("Host Machine not defined")
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                print(f"Connecting client to {ip_address}:{port}---------------------------")
                log_result("infinty_order",f"Connecting client to {ip_address}:{port}---------------------------")
                try:
                    s.connect((ip_address, port))
                    print(f"Connected")
                    print(f"Binding server to {local_ip}:{local_port}---------------------------")
                    log_result("infinty_order",f"Binding server to {local_ip}:{local_port}---------------------------")
                    while True:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as rcv_s:
                            try:
                                rcv_s.bind((local_ip, local_port))
                                rcv_s.listen()
                                print("listening to inner socket")
                                log_result("infinty_order","listening to inner socket")
                                conn, addr = rcv_s.accept()
                                with conn:
                                    print(f"Connected inner by {addr}")
                                    log_result("infinty_order",f"Connected inner by {addr}")
                                    msg = b''
                                    while True:
                                        print("Data receiving")
                                        data = conn.recv(63000)
                                        print("Data Received-----------------------------------------------")
                                        log_result("infinty_order","Data Received-----------------------------------------------")
                                        msg += data
                                        conn.sendall(chr(6).encode())
                                        print(msg)
                                        if msg.endswith(tcode("EOT")):
                                            print("data sent-------------------")
                                            s.sendall(msg)
                                            msg = b''
                                        if not data:
                                            break
                            except:
                                print('Unable to connect inner socket')
                                log_result("infinty_order",'Unable to connect inner socket')
                            finally:
                                rcv_s.shutdown(socket.SHUT_RDWR)
                                rcv_s.close()
                except socket.error:
                    print('Unable to connect')
                    log_result("infinty_order",'Unable to connect')
                    time.sleep(10)
                    pass
        except:
            continue

#--------------------------------sysmex------------------------
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
    return parsed_results, embassy_results

def start_sysmex_listener(ip_address, port):
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((ip_address, port))
                s.listen()
                print("listening")
                log_result("sysmex", "listening")

                conn, addr = s.accept()
                with conn:
                    print(f"Connected by {addr}")
                    log_result("sysmex", "Connected by " + str(addr))

                    msg = b""
                    while True:
                        data = conn.recv(63000)
                        print("Data Received-----------------------------------------------")
                        log_result("sysmex", "data received---------------------")
                        log_result("sysmex",str(data))
                        msg += data
                        if not data:
                            break
                        if msg.endswith(b'L|1|N\r'):
                            results, embassy_results = parse_sysmex_msg(msg)
                            msg = b''
                            print(results)
                            log_result("sysmex", "Result " + json.dumps(results))
                            if len(results) > 0:
                                requests.post(f"http://{get_url('lab')}/api/method/erpnext.healthcare.doctype.lab_test.lab_test.receive_sysmex_results", data=json.dumps(results))
                            if len(embassy_results) > 0:
                                requests.post(f"http://{get_url('embassy')}/api/method/erpnext.healthcare.doctype.lab_test.lab_test.receive_sysmex_results", data=json.dumps(embassy_results))
                        conn.sendall(chr(6).encode())
            except socket.error:
                print("Socket cannot connect")
                log_result("sysmex", "Socket cannot connect to:" + ip_address +":" + str(port))
                sleep(5)
                continue
