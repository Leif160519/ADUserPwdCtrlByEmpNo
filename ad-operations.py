#!/bin/python3

# ldapsearch命令查询出来的关键字：
# employeeID: 工号
# sAMAccountName: 账号
# mail: 邮箱
# cn: cn姓名(需要base64 -d解码)
# displayName: 显示名称
# memberOf： 安全组路径(多行)
# department: 所属部门(需要base64 -d解码)
# company: 所属公司(需要base64 -d解码)
# title: 职位(需要base64 -d解码)
# logonCount: 登录次数
# manager: 上级领导(取逗号分隔第一个)
# mobile: 手机号
# userAccountControl: 启用状态：512/66080/66048为启用，514/66050为禁用

import re
from flask import Flask, render_template, request, redirect, url_for, jsonify
from ldap3 import Server, Connection, ALL, MODIFY_REPLACE
import base64
import logging
import os

app = Flask(__name__)

# 检查并创建logs目录
if not os.path.exists('logs'):
    os.makedirs('logs')
# 配置日志记录
logging.basicConfig(filename='logs/ad-operations.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def decode_base64_field(field_value):
    return field_value if field_value else ""

def get_ad_user_info(employeeID):
    server = Server('your-ad-ip-address', get_info=ALL)
    conn = Connection(server, 'cn=administrator,cn=users,dc=domain,dc=com',
                      'your-ad-password', auto_bind=True)
    search_bases = [
        'OU=Users,gDC=domain,DC=com',
        'OU=Disabled Accounts,DC=domain,DC=com' # 禁用账号
    ]
    for search_base in search_bases:
        search_filter = f'(employeeID={employeeID})'
        attributes = ["employeeID", "sAMAccountName", "mail", "cn", "displayName", "memberOf", "department", "company",
                      "title", "logonCount", "manager", "mobile", "userAccountControl"]
        conn.search(search_base, search_filter, attributes=attributes)
        if conn.entries:
            entry = conn.entries[0]
            user_info = {
                "employeeID": entry.employeeID.value if hasattr(entry, 'employeeID') else None,
                "sAMAccountName": entry.sAMAccountName.value if hasattr(entry,'sAMAccountName') else None,
                "mail": entry.mail.value if hasattr(entry,'mail') else None,
                "displayName": entry.displayName.value if hasattr(entry, 'displayName') else None,
                "memberOf": entry.memberOf.values if hasattr(entry,'memberOf') else [],
                "logonCount": entry.logonCount.value if hasattr(entry, 'logonCount') else None,
                "mobile": entry.mobile.value if hasattr(entry,'mobile') else None
            }
            raw_info = {}

            if hasattr(entry, 'cn'):
                cn_raw_values = entry.cn.raw_values
                if cn_raw_values:
                    last_cn_value = cn_raw_values[-1]
                    try:
                        if isinstance(last_cn_value, bytes):
                            last_cn_value = last_cn_value.decode('utf - 8')
                        if last_cn_value.endswith('::'):
                            user_info["cn"] = base64.b64decode(last_cn_value[: - 2]).decode('utf - 8')
                        else:
                            user_info["cn"] = last_cn_value
                    except Exception as e:
                        logging.error(f"Error processing cn value {last_cn_value}: {e}")
                        user_info["cn"] = ""
                    raw_info["cn"] = cn_raw_values
                else:
                    user_info["cn"] = ""
                    raw_info["cn"] = None
            else:
                user_info["cn"] = ""
                raw_info["cn"] = None

            # 其他属性处理部分保持不变
            if hasattr(entry, 'department'):
                department_value = entry.department.value
                raw_info["department"] = department_value
                if isinstance(department_value, list) and department_value:
                    department_value = department_value[0]
                user_info["department"] = decode_base64_field(department_value)
            else:
                user_info["department"] = ""
                raw_info["department"] = None

            if hasattr(entry, 'company'):
                company_value = entry.company.value
                raw_info["company"] = company_value
                if company_value is not None:
                    if isinstance(company_value, list) and company_value:
                        company_value = company_value[0]
                    if company_value.endswith(':'):
                        company_value = company_value[: - 1]
                    user_info["company"] = decode_base64_field(company_value)
                else:
                    user_info["company"] = ""
                    raw_info["company"] = None
            else:
                user_info["company"] = ""
                raw_info["company"] = None

            if hasattr(entry, 'title'):
                title_value = entry.title.value
                raw_info["title"] = title_value
                if isinstance(title_value, list) and title_value:
                    title_value = title_value[0]
                user_info["title"] = decode_base64_field(title_value)
            else:
                user_info["title"] = ""
                raw_info["title"] = None

            if hasattr(entry,'manager'):
                manager_value = entry.manager.value
                raw_info["manager"] = manager_value
                if manager_value is not None:
                    manager_value = manager_value.split(',')[0]
                    if manager_value.startswith('CN='):
                        user_info["manager"] = manager_value[3:]
                    else:
                        user_info["manager"] = manager_value
                else:
                    user_info["manager"] = ""
                    raw_info["manager"] = None
            else:
                user_info["manager"] = ""
                raw_info["manager"] = None

            if hasattr(entry, 'userAccountControl'):
                control_value = entry.userAccountControl.value
                raw_info["userAccountControl"] = control_value
                if control_value in [512, 66080, 66048]:
                    user_info["启用状态"] = "启用"
                elif control_value in [514, 66050]:
                    user_info["启用状态"] = "禁用"
                else:
                    user_info["启用状态"] = "未知"
            else:
                user_info["启用状态"] = "未获取到"
                raw_info["userAccountControl"] = None

            # 打印原始信息
            print("AD查询的用户原始信息:")
            for key, value in raw_info.items():
                print(f"{key}: {value}")

            # 打印加工后的信息
            print("AD查询的用户加工后的信息:")
            for key, value in user_info.items():
                print(f"{key}: {value}")

            logging.info(f"查询到的用户处理后信息: {user_info}")
            logging.info(f"查询到的用户原始信息: {raw_info}")
            return user_info
    logging.info(f"未找到员工编号为 {employeeID} 的用户信息")
    return None

def update_ad_password(employeeID, new_password, force_password_change):
#    server = Server('your-ad-ip-address', get_info=ALL)
    # 修改密码需要ssl
    server = Server('your-ad-ip-address', port = 636, get_info = ALL, use_ssl = True, validator=False)
    conn = Connection(server, 'cn=administrator,cn=users,dc=domain,dc=com',
                      'your-ad-password', auto_bind=True)
    search_bases = [
        'OU=Users,gDC=domain,DC=com',
        'OU=Users,OU=YINFAN NANJING,OU=DOMAIN GROUP,DC=domain,DC=com'
    ]
    for search_base in search_bases:
        search_filter = f'(employeeID={employeeID})'
        conn.search(search_base, search_filter)
        if conn.entries:
            user_dn = conn.entries[0].entry_dn
            print(f"查询的user_dn信息:{user_dn}")
            # 构建修改密码的操作字典
#            changes = {
#                'unicodePwd': [(MODIFY_REPLACE, [new_password.encode('utf-16le')])]
#            }
            try:
                # 这个方法适用于ldap,如果用这种方法修改ad密码会提示:{'result': 53, 'description': 'unwillingToPerform', 'dn': '', 'message': '0000001F: SvcErr: DSID-031A1254, problem 5003 (WILL_NOT_PERFORM), data 0\n\x00', 'referrals': None, 'type': 'modifyResponse'}
                # 参考：https://blog.csdn.net/weixin_42196667/article/details/118907086
                # result = conn.modify(user_dn, changes)
                # 这个方法适用于Microsoft active directory
                result = conn.extend.microsoft.modify_password(user_dn,new_password)
                if result:
                    if force_password_change:
                        # 设置用户下次登录时需修改密码
                        conn.modify(user_dn, {'pwdLastSet': [(MODIFY_REPLACE, [0])]})
                    logging.info(f"Password updated successfully for employeeID: {employeeID}")
                    print(f"密码修改成功:{conn.result}")
                    return True
                else:
                    logging.error(f"Password updated unsuccessfully for employeeID: {employeeID}")
                    print(f"密码修改失败：{conn.result}")
                    return False
            except Exception as e:
                logging.error(f"Error updating password for employeeID {employeeID}: {str(e)}")
                return False
        logging.error(f"User not found for employeeID: {employeeID}")
        return False

def validate_password(user_info, new_password):
    if not user_info or not new_password:
        return False, "用户信息或新密码为空"
    # 1. 不能包含用户的帐户名，不能包含用户姓名中超过两个连续字符的部分
    account_name = user_info['sAMAccountName'] if user_info.get('sAMAccountName') else ''
    cn_name = user_info['cn'] if user_info.get('cn') else ''
    if account_name in new_password:
        return False, "密码包含用户帐户名"
    if cn_name:
        for i in range(len(cn_name) - 2):
            if cn_name[i:i + 3] in new_password:
                return False, "密码包含用户姓名中超过两个连续字符的部分"

    # 2. 至少有八个字符长度
    if len(new_password) < 8:
        return False, "密码长度不足8位"

    # 3. 不能使用之前设置过的密码 （这里假设没有历史密码记录，暂不实现）

    # 4. 包含以下四类字符中的三类字符
    has_upper = bool(re.search(r'[A-Z]', new_password))
    has_lower = bool(re.search(r'[a-z]', new_password))
    has_digit = bool(re.search(r'\d', new_password))
    has_special = bool(re.search(r'[!$#%]', new_password))
    char_type_count = sum([has_upper, has_lower, has_digit, has_special])
    if char_type_count < 3:
        missing_types = []
        if not has_upper:
            missing_types.append('大写字母')
        if not has_lower:
            missing_types.append('小写字母')
        if not has_digit:
            missing_types.append('数字')
        if not has_special:
            missing_types.append('特殊字符(!$#%)')
        return False, f"密码复杂度不够，缺少{', '.join(missing_types)}"

    return True, "密码验证通过"

@app.route('/')
def index():
    return redirect(url_for('search'))


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        employeeID = request.form.get('employeeID')
        user_info = get_ad_user_info(employeeID)
        if user_info:
            return render_template('result.html', user_info=user_info)
        else:
            return "User not found"
    return render_template('search.html')

@app.route('/update_password', methods=['POST'])
def update_password():
    employeeID = request.form.get('employeeID')
    new_password = request.form.get('new_password')
    force_password_change = request.form.get('force_password_change') is not None
    if not employeeID or not new_password:
        print("未能正确获取工号或密码")
        return jsonify({"success": False, "message": "Failed to get employeeID or password"})
    user_info = get_ad_user_info(employeeID)
    if not user_info:
        print(f"未能获取工号为 {employeeID} 的用户信息")
        return jsonify({"success": False, "message": "Failed to get user information"})
    is_valid, error_msg = validate_password(user_info, new_password)
    if not is_valid:
        print(f"工号 {employeeID}，密码 {new_password} 验证失败: {error_msg}")
        return jsonify({"success": False, "message": "Password does not meet requirements: " + error_msg})
    if update_ad_password(employeeID, new_password,force_password_change):
        print(f"工号 {employeeID}，密码 {new_password} 更新成功")
        return jsonify({"success": True, "message": "Password updated successfully"})
    else:
        print(f"工号 {employeeID}，密码 {new_password} 更新失败")
        return jsonify({"success": False, "message": "Failed to update password"})

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')
