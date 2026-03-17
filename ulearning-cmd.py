import sys
import requests
import json
from time import sleep
from time import time
from http.cookies import SimpleCookie
from urllib.parse import unquote
import traceback
import copy
from concurrent.futures import ThreadPoolExecutor


def printObj(obj):
    print(json.dumps(obj, indent=4, ensure_ascii=False))


def printPrettyJSON(s):
    try:
        print(json.dumps(json.loads(s), indent=4, ensure_ascii=False))
    except:
        print(s)


def makeHeadersFromTxt(txt):
    hDict = {}
    for line in txt.replace(':\n', ':').splitlines():
        if (':' in line):
            hDict[line.split(':')[0]] = line.split(':')[1]
    return hDict


def loadCfg():
    try:
        with open('ulearning-cmd.json') as f:
            cfg = json.load(f)

        global users
        # 加载用户列表（新版）
        if 'users' in cfg:
            users = cfg['users']

        # 如果没有用户列表，则尝试导入旧版的用户信息
        else:
            users[cfg['username']] = {}
            users[cfg['username']]['password'] = cfg.get('password')
            users[cfg['username']]['headers'] = cfg.get('auth', '')
            users[cfg['username']]['userID'] = cfg.get('userID', 0)
            users[cfg['username']]['roleId'] = cfg.get('roleId', 0)
            users[cfg['username']]['deviceInfo'] = cfg.get('deviceInfo', " ulearning-cmd ")
            users[cfg['username']]['terminalId'] = cfg.get('terminalId', "0123456789abcdef")

        # 设置活动用户
        try:
            users[cfg['activeUser']]
            return setActiveUser(cfg['activeUser'])
        except:
            # 如果 activeUser 不存在或指向不存在的用户，则使用用户列表第一个用户
            return setActiveUser(list(users)[0])
    except:
        return 0


# 设置活动用户
# 返回值：0=失败，1=成功
def setActiveUser(username):
    global loginName, password, headers, userID, roleId, deviceInfo, terminalId
    try:
        # 尝试获取 users 里是否存在该用户
        activeUser = users[username]
        # 设置用户名密码
        loginName = username
        password = activeUser.get('password')
        headers['AUTHORIZATION'] = activeUser.get('auth', '')
        userID = activeUser.get('userID', 0)
        roleId = activeUser.get('roleId', 0)
        deviceInfo = activeUser.get('deviceInfo', " ulearning-cmd ")
        terminalId = activeUser.get('terminalId', "0123456789abcdef")
        # 加载成功，返回 1
        return 1
    # 加载失败，返回 0
    except:
        return 0


def saveCfg():
    print('【正在保存配置文件】\n')
    # 将活动用户的信息写入 users
    global users
    users[loginName] = {}
    users[loginName]['password'] = password
    users[loginName]['auth'] = headers['AUTHORIZATION']
    users[loginName]['userID'] = userID
    users[loginName]['roleId'] = roleId
    users[loginName]['deviceInfo'] = deviceInfo
    users[loginName]['terminalId'] = terminalId
    # 构建配置文件
    cfg = {
        'users': users,
        'activeUser': loginName,
    }
    # 写入文件
    with open('ulearning-cmd.json', 'w') as f:
        json.dump(cfg, f, indent=2)


def new_login(username=None):
    print('【 请妥善保管配置文件，配置文件里的密码 不加密存储!!! 】')
    global loginName, password, headers, userID, roleId, deviceInfo, terminalId
    # 输入用户名
    if username == None:
        loginName = input('用户名：')
    else:
        loginName = username
    # 设置用户名之后，清除活动用户数据
    password = ''
    headers = {'AUTHORIZATION': ''}
    userID = 0
    roleId = 0
    deviceInfo = " ulearning-cmd "
    terminalId = "0123456789abcdef"
    # 输入密码
    password = input('密码：')
    login()


# 用户名密码登录
def login():
    print(f'\n===【正在登录：{loginName}】===\n')

    # 1. 真正登录：POST 表单
    resp = session.post(
        'https://application.dgut.edu.cn/appapi/user/login/app',
        data={
            'loginName': loginName,
            'password': password,
            'alias': 'application'
        },
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0'
        },
        allow_redirects=False          # 禁止自动跟进 302，方便我们拿 Set-Cookie
    )

    # 2. 提取 302 里的 Set-Cookie
    if resp.status_code != 302:
        raise RuntimeError(f'登录失败：期望 302，实际 {resp.status_code}')

    cookies = SimpleCookie(resp.headers['Set-Cookie'])

    # 3. 拿 AUTHORIZATION
    global headers
    headers['AUTHORIZATION'] = cookies['AUTHORIZATION'].value
    print(f"AUTHORIZATION: {headers['AUTHORIZATION']}")

    # 4. 解析 USERINFO
    userinfo = json.loads(unquote(cookies['USERINFO'].value))
    global userID, roleId
    userID = userinfo['userId']
    roleId = userinfo['roleId']
    print(f'userId: {userID}')
    print(f'roleId: {roleId}')

    # 5. 保存配置
    saveCfg()
    print('登录成功！')


# 刷新登录，以获取新 token
def refreshLogin(username):
    print(f'正在重新登录：{username}… ', end='')
    try:
        global users

        response = session.post(
            f'https://application.dgut.edu.cn/appapi/user/check?alias=application',
            data={
                'loginName': username,
                'password': users[username]['password'],
            })

        responseHeadersObj = response.history[0].headers
        if logLevel >= 2:
            print(responseHeadersObj)
        cookies = SimpleCookie(responseHeadersObj['Set-Cookie'])

        users[username]['auth'] = cookies['AUTHORIZATION'].value
        users[username]['userID'] = json.loads(unquote(cookies['USERINFO'].value))['userId']
        users[username]['roleId'] = json.loads(unquote(cookies['USERINFO'].value))['roleId']

        print('成功')

        saveCfg()
    except:
        print('失败')



# 获取课程列表
def getCourseList():
    print(f"正在获取课程列表，登录 token 为 [{headers['AUTHORIZATION']}]")
    url = 'https://lms.dgut.edu.cn/courseapi/courses/students'
    params = {
        'keyword': '',
        'publishStatus': 1,
        'type': 1,
        'pn': 1,
        'ps': 50,          # 一页 50 条，可改
        'lang': 'zh'
    }
    response = session.get(url, params=params, headers=headers)
    if response.status_code == 200:
        responseObj = response.json()
        # 将 课程ID 和 班级ID 的对应关系写入全局变量，以便调用
        global classIds
        for course in responseObj['courseList']:
            classIds[course['id']] = course['classId']
        if logLevel >= 2:
            printObj(responseObj)
        return responseObj
    else:
        print('请求失败！尝试重新登录…')
        login()
        return getCourseList()

# 获取课堂活动（如点名），注意 courseId (响应里实际命名为id) 和 classId 是两个东西，这里使用 courseId，签到才使用 classId
def getClassActivitys(courseId):
    """
    新版智慧教室：先拉课堂列表，再逐课堂取子活动，
    最后拼成旧接口格式 {'otherActivityDTOList': [...]} 返回
    """
    url = 'https://application.dgut.edu.cn/classroomapi/wisdomClassroom/student/getClassroomList'
    params = {
        'ocId': courseId,
        'pageSize': 999,
        'pageNum': 1,
        'teacherId': userID,
        'order': 0,
        'type': 1
    }
    resp = session.get(url, params=params, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    # 拼成旧字段
    acts = []
    for room in data.get('result', {}).get('list', []):
        if room['status'] == 0:                       # 跳过已结束课堂
            sub = getClassroomActivities(room['id'])
            for act in sub.get('result', {}).get('list', []):
                # 把课堂标题和课堂ID拼进去
                act['_roomTitle'] = room['title']
                act['_roomId'] = room['id']   # 保存课堂ID
                acts.append(act)

    if logLevel >= 2:
        print('拼成旧格式：', {'otherActivityDTOList': acts})
    #print('otherActivityDTOList 内容：', json.dumps(acts, ensure_ascii=False, indent=2))
    return {'otherActivityDTOList': acts}

def getClassroomActivities(classroomId):
    url = 'https://lms.dgut.edu.cn/classroomapi/wisdomClassroom/student/scoreDetailForClassroom'
    params = {
        'type': 2,
        'classroomId': classroomId,
        'lang': 'zh'
    }
    resp = session.get(url, params=params, headers=headers)
    resp.raise_for_status()
    return resp.json()


#添加一个检查签到状态的函数，用于确认是否需要签到
def check_attendance_status(attendanceID):
    """
    检查签到活动状态
    """
    url = f'https://lms.dgut.edu.cn/apps/newAttendance/getAttendanceForStu/{attendanceID}/{userID}'
    
    try:
        resp = session.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        
        if logLevel >= 1:
            print('签到状态检查返回：', data)
            
        # 根据您之前提供的响应格式判断状态
        # status=1 表示进行中，state="1" 表示可签到
        status = data.get('status')
        state = data.get('state')
        
        if status == 1 and state == "1":
            return True, "可签到"
        elif status == 2 or state == "2":
            return False, "已结束"
        else:
            return False, "已签到"
            
    except Exception as e:
        print(f"检查签到状态失败: {e}")
        return False, "检查失败"

def signin(attendanceID, classID):
    """
    新版智慧教室签到 - 使用POST请求
    attendanceID : 签到活动ID
    classID : 课堂ID
    """
    print(f'[{attendanceID}] 正在执行签到')
    
    # 构造请求数据 - 使用模糊位置
    payload = {
        "attendanceID": attendanceID,
        "classID": classID,
        "userID": userID,
        # 使用模糊位置绕过位置验证
        "location": "113,22",
        "address": "",
        "enterWay": 1,
        "attendanceCode": ""
    }
    
    # 新的签到URL
    url = "https://application.dgut.edu.cn/classroomapi/newAttendance/signByStu"
    """
    debug打印可使用
    if logLevel >= 1:
        print("请求头:")
        printObj(headers)
    if logLevel >= 1:
        print("请求数据:")
        printObj(payload)
    """
    try:
        # 发送POST请求执行签到
        response = session.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        # 不依赖POST响应，而是通过查询状态来确认签到结果
        print(f"[{attendanceID}] 签到请求已发送，正在验证结果...")
        
        # 等待一小段时间让服务器处理
        import time
        time.sleep(2)
        
        # 通过查询状态确认签到结果
        can_sign, message = check_attendance_status(attendanceID)
        
        if not can_sign and "已签到" in message:
            print(f"[{attendanceID}] 签到成功！")
            return {"success": True, "msg": "签到成功"}
        else:
            print(f"[{attendanceID}] 签到请求已发送，当前状态: {message}")
            print("检测反馈现在还是有bug，请自行上优学院查看是否签到成功")
            return {"success": False, "msg": message}
        
    except Exception as e:
        print(f"[{attendanceID}] 签到请求失败: {e}")
        return None


# 签到某一课程的所有点名
def signinByClass(courseId, classId):
    activities = getClassActivitys(courseId)['otherActivityDTOList']
    for act in activities:
        #print(act['relationId'], act['_roomId'],userID)
        #print(act.get('relationType'),act.get('status'))
        if act.get('relationType') == 1 and act.get('status') == 0:
            print(f"  [{act['relationId']}-签到] {act['title']} 进行中 可签到")
            sleep(1.5)
            # 使用保存的课堂ID和relationId签到
            signin(act['relationId'], act['_roomId'])
            sleep(1.5)


# 签到所有课程的所有点名
def signinAllCourses():
    print('\n===【执行：签到所有课程】===\n')
    for course in getCourseList()['courseList']:
        print(f"\n【{course['id']}】《{course['name']}》 班级ID：{course['classId']} ({course['className']})")
        # sleep(0)
        signinByClass(course['id'], course['classId'])


DISCLAIMER = """
*************************************************************
　　　　　　　　　　　　免　责　声　明
　　　　使用本软件意味着你需要承担可能带来的一切风险
　　    包括但不限于被教师发现、被官方检测封号等
　　　　　　　软件作者对可能出现的风险概不负责
                燎原二次编辑，禁止倒卖！！！
*************************************************************

"""[1:-1]


HELPTXT = """
"""[1:-1]

# 活动类型 (relationType):
RELATION_TYPE = {
    1: '点名',
    2: '投票',
    4: '作业',
    5: '小组',
    6: '测验',
    8: '考试',
    9: '讨论',
    10: '选人',
    11: '互评',
}

# 活动状态 (status):
ACTIVITY_STATUS = {
    1: '未开始',
    2: '进行中',
    3: '已结束',
}

# 签到状态 (personStatus):
PERSON_STATUS = {
    0: '【未签到】',
    1: '已签到',
}


# log level
logLevel = 1

# common vars
classIds = {}

questionDB = {}
paperAnswerDB = {}

# users
users = {}

# active user
loginName = ''
password = ''
headers = {'AUTHORIZATION': ''}  # 请求头只需包含 AUTHORIZATION
userID = 0
roleId = 0
deviceInfo = " ulearning-cmd "  # 默认设备名
terminalId = "0123456789abcdef"  # 默认设备ID

session = requests.session()
session.headers = headers


if __name__ == '__main__':
    print(DISCLAIMER)
    print('【加载配置文件…】')
    if loadCfg() == 1:
        print('【配置文件加载成功!】')
        login()
    else:
        new_login()
    print(f"已加载 {len(getCourseList()['courseList'])} 条课程")
    print('=== 初始化完成! ===\n')
    signinAllCourses()
