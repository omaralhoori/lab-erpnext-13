from ipaddress import ip_address
import socket, errno

import frappe

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


def send_msg_order(file_no, dob, gender, sample_id, sample_date, tests, host_code):
    res = frappe.db.get_value("Host Machine", {"machine_code": host_code}, ["ip_address", "port_no"])
    if not res:
        frappe.throw("Host Machine not defined")
    ip_address, port_no = res
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        #try:
        s.connect((ip_address, port_no))
        s.sendall(tcode("ENQ"))
        msg = prepare_infinty_msg(file_no, dob, gender, sample_id, sample_date, tests)
        s.sendall(msg)
        s.sendall(tcode("EOT"))
        recv_msg = s.recv(1024)
        if recv_msg == tcode('ACK'):
            frappe.msgprint("Order received")
            return True
        else:
            frappe.throw("Unable to receive order")
        # except:
        #     frappe.throw("Enable to connect to machine")

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