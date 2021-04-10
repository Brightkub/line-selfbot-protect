# -*- coding: utf-8 -*-
from thrift.transport import THttpClient
from thrift.protocol import TCompactProtocol
from akad import AuthService, TalkService, ChannelService, CallService, SquareService
from akad.ttypes import OpType, IdentityProvider, LoginResultType, LoginRequest, LoginType, ApplicationType, Message, MediaType
from datetime import datetime

import rsa, os, sys, threading, time, json, requests, urllib, base64, ntpath, random, re, shutil, tempfile

def loggedIn(func):
    def checkLogin(*args, **kwargs):
        if args[0].isLogin:
            return func(*args, **kwargs)
        else:
            args[0].callback.other('你想調用這個函數，你必須登錄到LINE')
    return checkLogin

class Config(object):
    LINE_HOST_DOMAIN            = 'https://legy-jp-addr-long.line.naver.jp'
    LINE_OBS_DOMAIN             = 'https://obs-sg.line-apps.com'
    LINE_TIMELINE_API           = 'https://legy-jp-addr-long.line.naver.jp/mh/api'
    LINE_TIMELINE_MH            = 'https://legy-jp-addr-long.line.naver.jp/mh'

    LINE_LOGIN_QUERY_PATH       = '/api/v4p/rs'
    LINE_AUTH_QUERY_PATH        = '/api/v4/TalkService.do'

    LINE_API_QUERY_PATH_FIR     = '/S4'
    LINE_POLL_QUERY_PATH_FIR    = '/P4'
    LINE_CALL_QUERY_PATH        = '/V4'
    LINE_CERTIFICATE_PATH       = '/Q'
    LINE_CHAN_QUERY_PATH        = '/CH4'
    LINE_SQUARE_QUERY_PATH      = '/SQS1'
    LINE_SHOP_QUERY_PATH        = '/SHOP4'
    LINE_LIFF_QUERY_PATH        = '/LIFF1'

    CHANNEL_ID = {
        'LINE_TIMELINE': '1341209950',
        'LINE_WEBTOON': '1401600689',
        'LINE_TODAY': '1518712866',
        'LINE_STORE': '1376922440',
        'LINE_MUSIC': '1381425814',
        'LINE_SERVICES': '1459630796'
    }

    listAppType = [
        'CHROMEOS\t2.1.5\tYTER Chromes\t11.2.5',
        'DESKTOPWIN\t5.9.2\tYTER DesktopWin\t11.2.5',
        'DESKTOPMAC\t5.9.2\tYTER DesktopMac\t11.2.5',
        'IOSIPAD\t8.11.0\tYTER IosIpad\t11.2.5',
        'WIN10\t5.5.5\tYTER Win10\t11.2.5'
    ]
    listAppVer = [
        '2.1.5',
        '5.9.2',
        '5.9.2',
        '8.11.0',
        '5.5.5'
    ]
    listAppName = [
        'Chromes',
        'DesktopWin',
        'DesktopMac',
        'IosIpad',
        'Win10'
    ]
    num = 3
    APP_TYPE    = listAppType[num]
    APP_VER     = listAppVer[num]
    CARRIER     = '51089, 1-0'
    SYSTEM_NAME = 'iOS'
    SYSTEM_VER  = '11.2.5'
    IP_ADDR     = '8.8.8.8'
    EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")

    def __init__(self):
        self.APP_NAME = '%s\t%s\t%s\t%s' % (self.APP_TYPE, self.APP_VER, self.SYSTEM_NAME, self.SYSTEM_VER)
        self.USER_AGENT = 'Line/%s' % self.APP_VER

class Auth(object):
    isLogin     = False
    authToken   = ""
    certificate = ""

    def __init__(self):
        self.server = Server()
        self.callback = Callback(self.__defaultCallback)
        self.server.setHeadersWithDict({
            'User-Agent': self.server.USER_AGENT,
            'X-Line-Application': self.server.APP_NAME,
            'X-Line-Carrier': self.server.CARRIER
        })

    def __loadSession(self):
        self.talk       = Session(self.server.LINE_HOST_DOMAIN, self.server.Headers, self.server.LINE_API_QUERY_PATH_FIR).Talk()
        self.poll       = Session(self.server.LINE_HOST_DOMAIN, self.server.Headers, self.server.LINE_POLL_QUERY_PATH_FIR).Talk()
        self.call       = Session(self.server.LINE_HOST_DOMAIN, self.server.Headers, self.server.LINE_CALL_QUERY_PATH).Call()
        self.channel    = Session(self.server.LINE_HOST_DOMAIN, self.server.Headers, self.server.LINE_CHAN_QUERY_PATH).Channel()
        self.square     = Session(self.server.LINE_HOST_DOMAIN, self.server.Headers, self.server.LINE_SQUARE_QUERY_PATH).Square()
        self.revision = self.poll.getLastOpRevision()
        self.isLogin = True

    def __loginRequest(self, type, data):
        lReq = LoginRequest()
        if type == '0':
            lReq.type = LoginType.ID_CREDENTIAL
            lReq.identityProvider = data['identityProvider']
            lReq.identifier = data['identifier']
            lReq.password = data['password']
            lReq.keepLoggedIn = data['keepLoggedIn']
            lReq.accessLocation = data['accessLocation']
            lReq.systemName = data['systemName']
            lReq.certificate = data['certificate']
            lReq.e2eeVersion = data['e2eeVersion']
        elif type == '1':
            lReq.type = LoginType.QRCODE
            lReq.keepLoggedIn = data['keepLoggedIn']
            if 'identityProvider' in data:
                lReq.identityProvider = data['identityProvider']
            if 'accessLocation' in data:
                lReq.accessLocation = data['accessLocation']
            if 'systemName' in data:
                lReq.systemName = data['systemName']
            lReq.verifier = data['verifier']
            lReq.e2eeVersion = data['e2eeVersion']
        else:
            lReq=False
        return lReq

    def loginWithCredential(self, _id, passwd, certificate=None, systemName=None, appName=None, keepLoggedIn=True):
        if systemName is None:
            systemName=self.server.SYSTEM_NAME
        if self.server.EMAIL_REGEX.match(_id):
            self.provider = IdentityProvider.LINE       # LINE
        else:
            self.provider = IdentityProvider.NAVER_KR   # NAVER

        if appName is None:
            appName=self.server.APP_NAME
        self.server.setHeaders('X-Line-Application', appName)
        self.tauth = Session(self.server.LINE_HOST_DOMAIN, self.server.Headers, self.server.LINE_AUTH_QUERY_PATH).Talk(isopen=False)

        rsaKey = self.tauth.getRSAKeyInfo(self.provider)

        message = (chr(len(rsaKey.sessionKey)) + rsaKey.sessionKey +
                   chr(len(_id)) + _id +
                   chr(len(passwd)) + passwd).encode('utf-8')
        pub_key = rsa.PublicKey(int(rsaKey.nvalue, 16), int(rsaKey.evalue, 16))
        crypto = rsa.encrypt(message, pub_key).hex()

        try:
            with open(_id + '.crt', 'r') as f:
                self.certificate = f.read()
        except:
            if certificate is not None:
                self.certificate = certificate
                if os.path.exists(certificate):
                    with open(certificate, 'r') as f:
                        self.certificate = f.read()

        self.auth = Session(self.server.LINE_HOST_DOMAIN, self.server.Headers, self.server.LINE_LOGIN_QUERY_PATH).Auth(isopen=False)

        lReq = self.__loginRequest('0', {
            'identityProvider': self.provider,
            'identifier': rsaKey.keynm,
            'password': crypto,
            'keepLoggedIn': keepLoggedIn,
            'accessLocation': self.server.IP_ADDR,
            'systemName': systemName,
            'certificate': self.certificate,
            'e2eeVersion': 0
        })

        result = self.auth.loginZ(lReq)

        if result.type == LoginResultType.REQUIRE_DEVICE_CONFIRM:
            self.callback.PinVerified(result.pinCode)

            self.server.setHeaders('X-Line-Access', result.verifier)
            getAccessKey = self.server.getJson(self.server.parseUrl(self.server.LINE_CERTIFICATE_PATH), allowHeader=True)

            self.auth = Session(self.server.LINE_HOST_DOMAIN, self.server.Headers, self.server.LINE_LOGIN_QUERY_PATH).Auth(isopen=False)

            try:
                lReq = self.__loginRequest('1', {
                    'keepLoggedIn': keepLoggedIn,
                    'verifier': getAccessKey['result']['verifier'],
                    'e2eeVersion': 0
                })
                result = self.auth.loginZ(lReq)
            except:
                raise Exception('登錄失敗')

            if result.type == LoginResultType.SUCCESS:
                if result.certificate is not None:
                    with open(_id + '.crt', 'w') as f:
                        f.write(result.certificate)
                    self.certificate = result.certificate
                if result.authToken is not None:
                    self.loginWithAuthToken(result.authToken, appName)
                else:
                    return False
            else:
                raise Exception('登錄失敗')

        elif result.type == LoginResultType.REQUIRE_QRCODE:
            self.loginWithQrCode(keepLoggedIn, systemName, appName)
            pass

        elif result.type == LoginResultType.SUCCESS:
            self.certificate = result.certificate
            self.loginWithAuthToken(result.authToken, appName)

    def loginWithQrCode(self, keepLoggedIn=True, systemName=None, appName=None, showQr=False):
        if systemName is None:
            systemName=self.server.SYSTEM_NAME
        if appName is None:
            appName=self.server.APP_NAME
        self.server.setHeaders('X-Line-Application', appName)

        self.tauth = Session(self.server.LINE_HOST_DOMAIN, self.server.Headers, self.server.LINE_AUTH_QUERY_PATH).Talk(isopen=False)
        qrCode = self.tauth.getAuthQrcode(keepLoggedIn, systemName)

        self.callback.QrUrl('line://au/q/' + qrCode.verifier, showQr)
        self.server.setHeaders('X-Line-Access', qrCode.verifier)

        getAccessKey = self.server.getJson(self.server.parseUrl(self.server.LINE_CERTIFICATE_PATH), allowHeader=True)

        self.auth = Session(self.server.LINE_HOST_DOMAIN, self.server.Headers, self.server.LINE_LOGIN_QUERY_PATH).Auth(isopen=False)

        try:
            lReq = self.__loginRequest('1', {
                'keepLoggedIn': keepLoggedIn,
                'systemName': systemName,
                'identityProvider': IdentityProvider.LINE,
                'verifier': getAccessKey['result']['verifier'],
                'accessLocation': self.server.IP_ADDR,
                'e2eeVersion': 0
            })
            result = self.auth.loginZ(lReq)
        except:
            raise Exception('登錄失敗')

        if result.type == LoginResultType.SUCCESS:
            if result.authToken is not None:
                self.loginWithAuthToken(result.authToken, appName)
            else:
                return False
        else:
            raise Exception('登錄失敗')

    def loginWithAuthToken(self, authToken=None, appName=None):
        if authToken is None:
            raise Exception('請提供驗證令牌')
        if appName is None:
            appName=self.server.APP_NAME
        self.server.setHeadersWithDict({
            'X-Line-Application': appName,
            'X-Line-Access': authToken
        })
        self.authToken = authToken
        self.__loadSession()

    def __defaultCallback(self, str):
        print(str)

    def logout(self):
        self.auth.logoutZ()

class OEPoll(object):
    OpInterrupt = {}
    client = None
    __squareSubId = {}
    __squareSyncToken = {}

    def __init__(self, client):
        if type(client) is not LINE:
            raise Exception('您需要設置LINE實例來初始化OEPoll')
        self.client = client

    def __fetchOperation(self, revision, count=1):
        return self.client.poll.fetchOperations(revision, count)

    def __execute(self, op, threading):
        try:
            if threading:
                _td = threading.Thread(target=self.OpInterrupt[op.type](op))
                _td.daemon = False
                _td.start()
            else:
                self.OpInterrupt[op.type](op)
        except Exception as e:
            self.client.log(e)

    def addOpInterruptWithDict(self, OpInterruptDict):
        self.OpInterrupt.update(OpInterruptDict)

    def addOpInterrupt(self, OperationType, DisposeFunc):
        self.OpInterrupt[OperationType] = DisposeFunc

    def setRevision(self, revision):
        self.client.revision = max(revision, self.client.revision)

    def singleTrace(self, count=1):
        try:
            operations = self.__fetchOperation(self.client.revision, count=count)
        except KeyboardInterrupt:
            exit()
        except:
            return

        if operations is None:
            return []
        else:
            return operations

    def trace(self, threading=False):
        try:
            operations = self.__fetchOperation(self.client.revision)
        except KeyboardInterrupt:
            exit()
        except:
            return

        for op in operations:
            if op.type in self.OpInterrupt.keys():
                self.__execute(op, threading)
            self.setRevision(op.revision)

    def singleFetchSquareChat(self, squareChatMid, limit=1):
        if squareChatMid not in self.__squareSubId:
            self.__squareSubId[squareChatMid] = 0
        if squareChatMid not in self.__squareSyncToken:
            self.__squareSyncToken[squareChatMid] = ''

        sqcEvents = self.client.fetchSquareChatEvents(squareChatMid, subscriptionId=self.__squareSubId[squareChatMid], syncToken=self.__squareSyncToken[squareChatMid], limit=limit, direction=1)
        self.__squareSubId[squareChatMid] = sqcEvents.subscription
        self.__squareSyncToken[squareChatMid] = sqcEvents.syncToken

        return sqcEvents.events

class Channel(object):
    isLogin = False
    channelId     = None
    channelResult = None

    def __init__(self, client, channelId, showSuccess=True):
        self.client = client
        self.channelId = channelId
        self.showSuccess = showSuccess
        self.__loginChannel()

    def __logChannel(self, text):
        self.client.log('[%s] : 登錄成功 %s' % (self.client.profile.displayName, text))

    def __loginChannel(self):
        self.isLogin = True
        self.channelResult  = self.approveChannelAndIssueChannelToken(self.channelId)
        self.__createChannelSession()

    @loggedIn
    def getChannelResult(self):
        return self.channelResult

    def __createChannelSession(self):
        channelInfo = self.getChannelInfo(self.channelId)
        if self.showSuccess:
            self.__logChannel(channelInfo.name)

    @loggedIn
    def approveChannelAndIssueChannelToken(self, channelId):
        return self.client.approveChannelAndIssueChannelToken(channelId)

    @loggedIn
    def issueChannelToken(self, channelId):
        return self.client.issueChannelToken(channelId)

    @loggedIn
    def getChannelInfo(self, channelId, locale='EN'):
        return self.client.getChannelInfo(channelId, locale)

    @loggedIn
    def revokeChannel(self, channelId):
        return self.client.revokeChannel(channelId)

class Call(object):
    isLogin = False

    def __init__(self):
        self.isLogin = True

    @loggedIn
    def acquireCallRoute(self, to):
        return self.call.acquireCallRoute(to)

    @loggedIn
    def acquireGroupCallRoute(self, groupId, mediaType=MediaType.AUDIO):
        return self.call.acquireGroupCallRoute(groupId, mediaType)

    @loggedIn
    def acquireGroupVideoCallRoute(self, groupId, mediaType=MediaType.VIDEO):
        return self.call.acquireGroupVideoCallRoute(groupId, mediaType)
    @loggedIn
    def getGroupCall(self, ChatMid):
        return self.call.getGroupCall(ChatMid)

    @loggedIn
    def inviteIntoGroupCall(self, chatId, contactIds=[], mediaType=MediaType.AUDIO):
        return self.call.inviteIntoGroupCall(chatId, contactIds, mediaType)

    @loggedIn
    def inviteIntoGroupVideoCall(self, chatId, contactIds=[], mediaType=MediaType.VIDEO):
        return self.call.inviteIntoGroupVideoCall(chatId, contactIds, mediaType)

class Timeline(Channel):

    def __init__(self):
        Channel.__init__(self, self.channel, self.server.CHANNEL_ID['LINE_TIMELINE'], False)
        self.tl = self.getChannelResult()
        self.__loginTimeline()

    def __loginTimeline(self):
        self.server.setTimelineHeadersWithDict({
            'Content-Type': 'application/json',
            'User-Agent': self.server.USER_AGENT,
            'X-Line-Mid': self.profile.mid,
            'X-Line-Carrier': self.server.CARRIER,
            'X-Line-Application': self.server.APP_NAME,
            'X-Line-ChannelToken': self.tl.channelAccessToken
        })
        self.profileDetail = self.getProfileDetail()

    """Timeline"""

    @loggedIn
    def getFeed(self, postLimit=10, commentLimit=1, likeLimit=1, order='TIME'):
        params = {'postLimit': postLimit, 'commentLimit': commentLimit, 'likeLimit': likeLimit, 'order': order}
        url = self.server.urlEncode(self.server.LINE_TIMELINE_API, '/v27/feed/list.json', params)
        r = self.server.getContent(url, headers=self.server.timelineHeaders)
        return r.json()

    @loggedIn
    def getHomeProfile(self, mid=None, postLimit=10, commentLimit=1, likeLimit=1):
        if mid is None:
            mid = self.profile.mid
        params = {'homeId': mid, 'postLimit': postLimit, 'commentLimit': commentLimit, 'likeLimit': likeLimit, 'sourceType': 'LINE_PROFILE_COVER'}
        url = self.server.urlEncode(self.server.LINE_TIMELINE_API, '/v27/post/list.json', params)
        r = self.server.getContent(url, headers=self.server.timelineHeaders)
        return r.json()

    @loggedIn
    def getProfileDetail(self, mid=None):
        if mid is None:
            mid = self.profile.mid
        params = {'userMid': mid}
        url = self.server.urlEncode(self.server.LINE_TIMELINE_API, '/v1/userpopup/getDetail.json', params)
        r = self.server.getContent(url, headers=self.server.timelineHeaders)
        return r.json()

    @loggedIn
    def updateProfileCoverById(self, objId):
        params = {'coverImageId': objId}
        url = self.server.urlEncode(self.server.LINE_TIMELINE_API, '/v39/home/updateCover.json', params)
        r = self.server.getContent(url, headers=self.server.timelineHeaders)
        return r.json()

    @loggedIn
    def getProfileCoverId(self, mid=None):
        if mid is None:
            mid = self.profile.mid
        home = self.getProfileDetail(mid)
        return home['result']['objectId']

    @loggedIn
    def getProfileCoverURL(self, mid=None):
        if mid is None:
            mid = self.profile.mid
        home = self.getProfileDetail(mid)
        params = {'userid': mid, 'oid': home['result']['objectId']}
        return self.server.urlEncode(self.server.LINE_OBS_DOMAIN, '/myhome/c/download.nhn', params)

    """Post"""

    @loggedIn
    def createPost(self, text, holdingTime=None):
        params = {'homeId': mid, 'sourceType': 'TIMELINE'}
        url = self.server.urlEncode(self.server.LINE_TIMELINE_API, '/v33/post/create.json', params)
        payload = {'postInfo': {'readPermission': {'type': 'ALL'}}, 'sourceType': 'TIMELINE', 'contents': {'text': text}}
        if holdingTime != None:
            payload["postInfo"]["holdingTime"] = holdingTime
        data = json.dumps(payload)
        r = self.server.postContent(url, data=data, headers=self.server.timelineHeaders)
        return r.json()

    @loggedIn
    def sendPostToTalk(self, mid, postId):
        if mid is None:
            mid = self.profile.mid
        params = {'receiveMid': mid, 'postId': postId}
        url = self.server.urlEncode(self.server.LINE_TIMELINE_API, '/v33/post/sendPostToTalk.json', params)
        r = self.server.getContent(url, data=data, headers=self.server.timelineHeaders)
        return r.json()

    @loggedIn
    def createComment(self, mid, postId, text):
        if mid is None:
            mid = self.profile.mid
        params = {'homeId': mid, 'sourceType': 'TIMELINE'}
        url = self.server.urlEncode(self.server.LINE_TIMELINE_API, '/v33/comment/create.json', params)
        data = {'commentText': text, 'activityExternalId': postId, 'actorId': mid}
        r = self.server.postContent(url, data=data, headers=self.server.timelineHeaders)
        return r.json()

    @loggedIn
    def deleteComment(self, mid, postId, commentId):
        if mid is None:
            mid = self.profile.mid
        params = {'homeId': mid, 'sourceType': 'TIMELINE'}
        url = self.server.urlEncode(self.server.LINE_TIMELINE_API, '/v33/comment/delete.json', params)
        data = {'commentId': commentId, 'activityExternalId': postId, 'actorId': mid}
        r = self.server.postContent(url, data=data, headers=self.server.timelineHeaders)
        return r.json()

    @loggedIn
    def likePost(self, mid, postId, likeType=1001):
        if mid is None:
            mid = self.profile.mid
        if likeType not in [1001,1002,1003,1004,1005,1006]:
            raise Exception('Invalid parameter likeType')
        params = {'homeId': mid, 'sourceType': 'TIMELINE'}
        url = self.server.urlEncode(self.server.LINE_TIMELINE_API, '/v33/like/create.json', params)
        data = {'likeType': likeType, 'activityExternalId': postId, 'actorId': mid}
        r = self.server.postContent(url, data=data, headers=self.server.timelineHeaders)
        return r.json()

    @loggedIn
    def unlikePost(self, mid, postId):
        if mid is None:
            mid = self.profile.mid
        params = {'homeId': mid, 'sourceType': 'TIMELINE'}
        url = self.server.urlEncode(self.server.LINE_TIMELINE_API, '/v33/like/cancel.json', params)
        data = {'activityExternalId': postId, 'actorId': mid}
        r = self.server.postContent(url, data=data, headers=self.server.timelineHeaders)
        return r.json()

    """Group Post"""

    @loggedIn
    def createGroupPost(self, mid, text):
        payload = {'postInfo': {'readPermission': {'homeId': mid}}, 'sourceType': 'TIMELINE', 'contents': {'text': text}}
        print(payload)
        print("1")
        data = json.dumps(payload)
        r = self.server.postContent(self.server.LINE_TIMELINE_API + '/v39/post/create.json', data=data, headers=self.server.timelineHeaders)
        print(r)
        print("2")
        return r.json()

    @loggedIn
    def createGroupAlbum(self, mid, name):
        data = json.dumps({'title': name, 'type': 'image'})
        params = {'homeId': mid,'count': '1','auto': '0'}
        url = self.server.urlEncode(self.server.LINE_TIMELINE_MH, '/album/v3/album.json', params)
        r = self.server.postContent(url, data=data, headers=self.server.timelineHeaders)
        if r.status_code != 201:
            raise Exception('創建一個新的相冊失敗。')
        return True

    @loggedIn
    def deleteGroupAlbum(self, mid, albumId):
        params = {'homeId': mid}
        url = self.server.urlEncode(self.server.LINE_TIMELINE_MH, '/album/v3/album/%s' % albumId, params)
        r = self.server.deleteContent(url, headers=self.server.timelineHeaders)
        if r.status_code != 201:
            raise Exception('刪除相冊失敗。')
        return True

    @loggedIn
    def getGroupPost(self, groupId, postLimit=10, commentLimit=1, likeLimit=1):
        params = {'homeId': groupId, 'commentLimit': commentLimit, 'likeLimit': likeLimit, 'sourceType': 'TALKROOM'}
        url = self.server.urlEncode(self.server.LINE_TIMELINE_API, '/v27/post/list.json', params)
        r = self.server.getContent(url, headers=self.server.timelineHeaders)
        return r.json()

    """Group Album"""

    @loggedIn
    def getGroupAlbum(self, groupId):
        params = {'homeId': groupId, 'type': 'g', 'sourceType': 'TALKROOM'}
        url = self.server.urlEncode(self.server.LINE_TIMELINE_MH, '/album/v3/albums.json', params)
        r = self.server.getContent(url, headers=self.server.timelineHeaders)
        return r.json()

    @loggedIn
    def changeGroupAlbumName(self, mid, albumId, name):
        data = json.dumps({'title': name})
        params = {'homeId': mid}
        url = self.server.urlEncode(self.server.LINE_TIMELINE_MH, '/album/v3/album/%s' % albumId, params)
        r = self.server.putContent(url, data=data, headers=self.server.timelineHeaders)
        if r.status_code != 201:
            raise Exception('更改專輯名稱失敗。')
        return True

    @loggedIn
    def addImageToAlbum(self, mid, albumId, path):
        file = open(path, 'rb').read()
        params = {
            'oid': int(time.time()),
            'quality': '90',
            'range': len(file),
            'type': 'image'
        }
        hr = self.server.additionalHeaders(self.server.timelineHeaders, {
            'Content-Type': 'image/jpeg',
            'X-Line-Mid': mid,
            'X-Line-Album': albumId,
            'x-obs-params': self.genOBSParams(params,'b64')
        })
        r = self.server.getContent(self.server.LINE_OBS_DOMAIN + '/album/a/upload.nhn', data=file, headers=hr)
        if r.status_code != 201:
            raise Exception('將圖片添加到相冊失敗。')
        return r.json()

    @loggedIn
    def getImageGroupAlbum(self, mid, albumId, objId, returnAs='path', saveAs=''):
        if saveAs == '':
            saveAs = self.genTempFile('path')
        if returnAs not in ['path','bool','bin']:
            raise Exception('Invalid returnAs value')
        hr = self.server.additionalHeaders(self.server.timelineHeaders, {
            'Content-Type': 'image/jpeg',
            'X-Line-Mid': mid,
            'X-Line-Album': albumId
        })
        params = {'ver': '1.0', 'oid': objId}
        url = self.server.urlEncode(self.server.LINE_OBS_DOMAIN, '/album/a/download.nhn', params)
        r = self.server.getContent(url, headers=hr)
        if r.status_code == 200:
            self.saveFile(saveAs, r.raw)
            if returnAs == 'path':
                return saveAs
            elif returnAs == 'bool':
                return True
            elif returnAs == 'bin':
                return r.raw
        else:
            raise Exception('下載圖片專輯失敗。')

class Talk(object):
    isLogin = False
    _messageReq = {}
    _unsendMessageReq = 0

    def __init__(self):
        self.isLogin = True

    """User"""

    @loggedIn
    def acquireEncryptedAccessToken(self, featureType=2):
        return self.talk.acquireEncryptedAccessToken(featureType)

    @loggedIn
    def getProfile(self):
        return self.talk.getProfile()

    @loggedIn
    def getSettings(self):
        return self.talk.getSettings()

    @loggedIn
    def getUserTicket(self):
        return self.talk.getUserTicket()

    @loggedIn
    def updateProfile(self, profileObject):
        return self.talk.updateProfile(0, profileObject)

    @loggedIn
    def updateSettings(self, settingObject):
        return self.talk.updateSettings(0, settingObject)

    @loggedIn
    def updateProfileAttribute(self, attrId, value):
        return self.talk.updateProfileAttribute(0, attrId, value)

    """Operation"""

    @loggedIn
    def fetchOperation(self, revision, count):
        return self.talk.fetchOperations(revision, count)

    @loggedIn
    def getLastOpRevision(self):
        return self.talk.getLastOpRevision()

    """Message"""

    @loggedIn
    def sendMessage(self, to, text, contentMetadata={}, contentType=0):
        msg = Message()
        msg.to, msg._from = to, self.profile.mid
        msg.text = text
        msg.contentType, msg.contentMetadata = contentType, contentMetadata
        if to not in self._messageReq:
            self._messageReq[to] = -1
        self._messageReq[to] += 1
        return self.talk.sendMessage(self._messageReq[to], msg)

    """ Usage:
        @to Integer
        @text String
        @dataMid List of user Mid
    """
    @loggedIn
    def Tag(self, to, midlist):
        txt = u''
        s=0
        b=[]
        for mid in midlist:
            b.append({"S":str(s), "E" :str(s+6), "M":mid})
            s += 7
            txt += u'@Moe \n'
        return self.sendMessage(to, text=txt, contentMetadata={u'MENTION': json.dumps({'MENTIONEES':b})}, contentType=0)

    @loggedIn
    def sendMessageWithMention(self, to, text='', dataMid=[]):
        arr = []
        list_text=''
        if '[list]' in text.lower():
            i=0
            for l in dataMid:
                list_text+='\n@[list-'+str(i)+']'
                i=i+1
            text=text.replace('[list]', list_text)
        elif '[list-' in text.lower():
            text=text
        else:
            i=0
            for l in dataMid:
                list_text+=' @[list-'+str(i)+']'
                i=i+1
            text=text+list_text
        i=0
        for l in dataMid:
            mid=l
            name='@[list-'+str(i)+']'
            ln_text=text.replace('\n',' ')
            if ln_text.find(name):
                line_s=int(ln_text.index(name))
                line_e=(int(line_s)+int(len(name)))
            arrData={'S': str(line_s), 'E': str(line_e), 'M': mid}
            arr.append(arrData)
            i=i+1
        contentMetadata={'MENTION':str('{"MENTIONEES":' + json.dumps(arr).replace(' ','') + '}')}
        return self.sendMessage(to, text, contentMetadata)

    @loggedIn
    def sendSticker(self, to, packageId, stickerId):
        contentMetadata = {
            'STKVER': '100',
            'STKPKGID': packageId,
            'STKID': stickerId
        }
        return self.sendMessage(to, '', contentMetadata, 7)

    @loggedIn
    def sendContact(self, to, mid):
        contentMetadata = {'mid': mid}
        return self.sendMessage(to, '', contentMetadata, 13)

    @loggedIn
    def sendGift(self, to, productId, productType):
        if productType not in ['theme','sticker']:
            raise Exception('Invalid productType value')
        contentMetadata = {
            'MSGTPL': str(random.randint(0, 12)),
            'PRDTYPE': productType.upper(),
            'STKPKGID' if productType == 'sticker' else 'PRDID': productId
        }
        return self.sendMessage(to, '', contentMetadata, 9)

    @loggedIn
    def sendMessageAwaitCommit(self, to, text, contentMetadata={}, contentType=0):
        msg = Message()
        msg.to, msg._from = to, self.profile.mid
        msg.text = text
        msg.contentType, msg.contentMetadata = contentType, contentMetadata
        if to not in self._messageReq:
            self._messageReq[to] = -1
        self._messageReq[to] += 1
        return self.talk.sendMessageAwaitCommit(self._messageReq[to], msg)

    @loggedIn
    def unsendMessage(self, messageId):
        self._unsendMessageReq += 1
        return self.talk.unsendMessage(self._unsendMessageReq, messageId)

    @loggedIn
    def requestResendMessage(self, senderMid, messageId):
        return self.talk.requestResendMessage(0, senderMid, messageId)

    @loggedIn
    def respondResendMessage(self, receiverMid, originalMessageId, resendMessage, errorCode):
        return self.talk.respondResendMessage(0, receiverMid, originalMessageId, resendMessage, errorCode)

    @loggedIn
    def removeMessage(self, messageId):
        return self.talk.removeMessage(messageId)

    @loggedIn
    def removeAllMessages(self, lastMessageId):
        return self.talk.removeAllMessages(0, lastMessageId)

    @loggedIn
    def removeMessageFromMyHome(self, messageId):
        return self.talk.removeMessageFromMyHome(messageId)

    @loggedIn
    def destroyMessage(self, chatId, messageId):
        return self.talk.destroyMessage(0, chatId, messageId, sessionId)

    @loggedIn
    def sendChatChecked(self, consumer, messageId):
        return self.talk.sendChatChecked(0, consumer, messageId)

    @loggedIn
    def sendEvent(self, messageObject):
        return self.talk.sendEvent(0, messageObject)

    @loggedIn
    def getLastReadMessageIds(self, chatId):
        return self.talk.getLastReadMessageIds(0, chatId)

    @loggedIn
    def getPreviousMessagesV2WithReadCount(self, messageBoxId, endMessageId, messagesCount=50):
        return self.talk.getPreviousMessagesV2WithReadCount(messageBoxId, endMessageId, messagesCount)

    """Object"""

    @loggedIn
    def sendImage(self, to, path):
        objectId = self.sendMessage(to=to, text=None, contentType = 1).id
        return self.uploadObjTalk(path=path, type='image', returnAs='bool', objId=objectId)

    @loggedIn
    def sendImageWithURL(self, to, url):
        path = self.downloadFileURL(url, 'path')
        return self.sendImage(to, path)
        return self.deleteFile(path)

    @loggedIn
    def sendGIF(self, to, path):
        return self.uploadObjTalk(path=path, type='gif', returnAs='bool', to=to)

    @loggedIn
    def sendGIFWithURL(self, to, url):
        path = self.downloadFileURL(url, 'path')
        return self.sendGIF(to, path)
        return self.deleteFile(path)

    @loggedIn
    def sendVideo(self, to, path):
        objectId = self.sendMessage(to=to, text=None, contentMetadata={'VIDLEN': '60000','DURATION': '60000'}, contentType = 2).id
        return self.uploadObjTalk(path=path, type='video', returnAs='bool', objId=objectId)

    @loggedIn
    def sendVideoWithURL(self, to, url):
        path = self.downloadFileURL(url, 'path')
        return self.sendVideo(to, path)
        return self.deleteFile(path)

    @loggedIn
    def sendAudio(self, to, path):
        objectId = self.sendMessage(to=to, text=None, contentType = 3).id
        return self.uploadObjTalk(path=path, type='audio', returnAs='bool', objId=objectId)

    @loggedIn
    def sendAudioWithURL(self, to, url):
        path = self.downloadFileURL(url, 'path')
        return self.sendAudio(to, path)
        return self.deleteFile(path)

    @loggedIn
    def sendFile(self, to, path, file_name=''):
        if file_name == '':
            file_name = ntpath.basename(path)
        file_size = len(open(path, 'rb').read())
        objectId = self.sendMessage(to=to, text=None, contentMetadata={'FILE_NAME': str(file_name),'FILE_SIZE': str(file_size)}, contentType = 14).id
        return self.uploadObjTalk(path=path, type='file', returnAs='bool', objId=objectId)

    @loggedIn
    def sendFileWithURL(self, to, url, fileName=''):
        path = self.downloadFileURL(url, 'path')
        return self.sendFile(to, path, fileName)
        return self.deleteFile(path)

    """Contact"""

    @loggedIn
    def blockContact(self, mid):
        return self.talk.blockContact(0, mid)

    @loggedIn
    def unblockContact(self, mid):
        return self.talk.unblockContact(0, mid)

    @loggedIn
    def findAndAddContactByMetaTag(self, userid, reference):
        return self.talk.findAndAddContactByMetaTag(0, userid, reference)

    @loggedIn
    def findAndAddContactsByMid(self, mid):
        return self.talk.findAndAddContactsByMid(0, mid, 0, '')

    @loggedIn
    def findAndAddContactsByEmail(self, emails=[]):
        return self.talk.findAndAddContactsByEmail(0, emails)

    @loggedIn
    def findAndAddContactsByUserid(self, userid):
        return self.talk.findAndAddContactsByUserid(0, userid)

    @loggedIn
    def findContactsByUserid(self, userid):
        return self.talk.findContactByUserid(userid)

    @loggedIn
    def findContactByTicket(self, ticketId):
        return self.talk.findContactByUserTicket(ticketId)

    @loggedIn
    def getAllContactIds(self):
        return self.talk.getAllContactIds()

    @loggedIn
    def getBlockedContactIds(self):
        return self.talk.getBlockedContactIds()

    @loggedIn
    def getContact(self, mid):
        return self.talk.getContact(mid)

    @loggedIn
    def getContacts(self, midlist):
        return self.talk.getContacts(midlist)

    @loggedIn
    def getFavoriteMids(self):
        return self.talk.getFavoriteMids()

    @loggedIn
    def getHiddenContactMids(self):
        return self.talk.getHiddenContactMids()

    @loggedIn
    def tryFriendRequest(self, midOrEMid, friendRequestParams, method=1):
        return self.talk.tryFriendRequest(midOrEMid, method, friendRequestParams)

    @loggedIn
    def makeUserAddMyselfAsContact(self, contactOwnerMid):
        return self.talk.makeUserAddMyselfAsContact(contactOwnerMid)

    @loggedIn
    def getContactWithFriendRequestStatus(self, id):
        return self.talk.getContactWithFriendRequestStatus(id)

    @loggedIn
    def reissueUserTicket(self, expirationTime=100, maxUseCount=100):
        return self.talk.reissueUserTicket(expirationTime, maxUseCount)

    @loggedIn
    def cloneContactProfile(self, mid):
        contact = self.getContact(mid)
        profile = self.profile
        profile.displayName = contact.displayName
        profile.statusMessage = contact.statusMessage
        profile.pictureStatus = contact.pictureStatus
        if self.getProfileCoverId(mid) is not None:
            self.updateProfileCoverById(self.getProfileCoverId(mid))
        self.updateProfileAttribute(8, profile.pictureStatus)
        return self.updateProfile(profile)

    """Group"""

    @loggedIn
    def getChatRoomAnnouncementsBulk(self, chatRoomMids):
        return self.talk.getChatRoomAnnouncementsBulk(chatRoomMids)

    @loggedIn
    def getChatRoomAnnouncements(self, chatRoomMid):
        return self.talk.getChatRoomAnnouncements(chatRoomMid)

    @loggedIn
    def createChatRoomAnnouncement(self, chatRoomMid, type, contents):
        return self.talk.createChatRoomAnnouncement(0, chatRoomMid, type, contents)

    @loggedIn
    def removeChatRoomAnnouncement(self, chatRoomMid, announcementSeq):
        return self.talk.removeChatRoomAnnouncement(0, chatRoomMid, announcementSeq)

    @loggedIn
    def getGroupWithoutMembers(self, groupId):
        return self.talk.getGroupWithoutMembers(groupId)

    @loggedIn
    def findGroupByTicket(self, ticketId):
        return self.talk.findGroupByTicket(ticketId)

    @loggedIn
    def acceptGroupInvitation(self, groupId):
        return self.talk.acceptGroupInvitation(0, groupId)

    @loggedIn
    def acceptGroupInvitationByTicket(self, groupId, ticketId):
        return self.talk.acceptGroupInvitationByTicket(0, groupId, ticketId)

    @loggedIn
    def cancelGroupInvitation(self, groupId, contactIds):
        return self.talk.cancelGroupInvitation(0, groupId, contactIds)

    @loggedIn
    def createGroup(self, name, midlist):
        return self.talk.createGroup(0, name, midlist)

    @loggedIn
    def getGroup(self, groupId):
        return self.talk.getGroup(groupId)

    @loggedIn
    def getGroups(self, groupIds):
        return self.talk.getGroups(groupIds)

    @loggedIn
    def getGroupsV2(self, groupIds):
        return self.talk.getGroupsV2(groupIds)

    @loggedIn
    def getCompactGroup(self, groupId):
        return self.talk.getCompactGroup(groupId)

    @loggedIn
    def getCompactRoom(self, roomId):
        return self.talk.getCompactRoom(roomId)

    @loggedIn
    def getGroupIdsByName(self, groupName):
        gIds = []
        for gId in self.getGroupIdsJoined():
            g = self.getCompactGroup(gId)
            if groupName in g.name:
                gIds.append(gId)
        return gIds

    @loggedIn
    def getGroupIdsInvited(self):
        return self.talk.getGroupIdsInvited()

    @loggedIn
    def getGroupIdsJoined(self):
        return self.talk.getGroupIdsJoined()

    @loggedIn
    def updateGroupPreferenceAttribute(self, groupMid, updatedAttrs):
        return self.talk.updateGroupPreferenceAttribute(0, groupMid, updatedAttrs)

    @loggedIn
    def inviteIntoGroup(self, groupId, midlist):
        return self.talk.inviteIntoGroup(0, groupId, midlist)

    @loggedIn
    def kickoutFromGroup(self, groupId, midlist):
        return self.talk.kickoutFromGroup(0, groupId, midlist)

    @loggedIn
    def leaveGroup(self, groupId):
        return self.talk.leaveGroup(0, groupId)

    @loggedIn
    def rejectGroupInvitation(self, groupId):
        return self.talk.rejectGroupInvitation(0, groupId)

    @loggedIn
    def reissueGroupTicket(self, groupId):
        return self.talk.reissueGroupTicket(groupId)

    @loggedIn
    def updateGroup(self, groupObject):
        return self.talk.updateGroup(0, groupObject)

    """Room"""

    @loggedIn
    def createRoom(self, midlist):
        return self.talk.createRoom(0, midlist)

    @loggedIn
    def getRoom(self, roomId):
        return self.talk.getRoom(roomId)

    @loggedIn
    def inviteIntoRoom(self, roomId, midlist):
        return self.talk.inviteIntoRoom(0, roomId, midlist)

    @loggedIn
    def leaveRoom(self, roomId):
        return self.talk.leaveRoom(0, roomId)

    """Call"""

    @loggedIn
    def acquireCallTalkRoute(self, to):
        return self.talk.acquireCallRoute(to)

    """Report"""

    @loggedIn
    def reportSpam(self, chatMid, memberMids=[], spammerReasons=[], senderMids=[], spamMessageIds=[], spamMessages=[]):
        return self.talk.reportSpam(chatMid, memberMids, spammerReasons, senderMids, spamMessageIds, spamMessages)

    @loggedIn
    def reportSpammer(self, spammerMid, spammerReasons=[], spamMessageIds=[]):
        return self.talk.reportSpammer(spammerMid, spammerReasons, spamMessageIds)

class Square(object):
    isSupportSquare = False
    isLogin = False

    def __init__(self):
        self.isLogin = True
        try:
            self.isSupportSquare = True
            self.squares    = self.getJoinedSquares().squares
            self.squareObsToken = self.acquireEncryptedAccessToken(2).split('\x1e')[1]
        except:
            self.isSupportSquare = False
            self.log('登入成功')

    """Object"""

    @loggedIn
    def sendSquareImage(self, squareChatMid, path): # Under development
        return self.uploadObjSquare(squareChatMid=squareChatMid, path=path, type='image', returnAs='bool')

    @loggedIn
    def sendSquareImageWithURL(self, squareChatMid, url): # Under development
        path = self.downloadFileURL(url, 'path')
        return self.sendSquareImage(squareChatMid, path)

    @loggedIn
    def sendSquareGIF(self, squareChatMid, path): # Under development
        return self.uploadObjSquare(squareChatMid=squareChatMid, path=path, type='gif', returnAs='bool')

    @loggedIn
    def sendSquareGIFWithURL(self, squareChatMid, url): # Under development
        path = self.downloadFileURL(url, 'path')
        return self.sendSquareGIF(squareChatMid, path)

    @loggedIn
    def sendSquareVideo(self, squareChatMid, path): # Under development
        return self.uploadObjSquare(squareChatMid=squareChatMid, path=path, type='video', returnAs='bool')

    @loggedIn
    def sendSquareVideoWithURL(self, squareChatMid, url): # Under development
        path = self.downloadFileURL(url, 'path')
        return self.sendSquareVideo(squareChatMid, path)

    @loggedIn
    def sendSquareAudio(self, squareChatMid, path): # Under development
        return self.uploadObjSquare(squareChatMid=squareChatMid, path=path, type='audio', returnAs='bool')

    @loggedIn
    def sendSquareAudioWithURL(self, squareChatMid, url): # Under development
        path = self.downloadFileURL(url, 'path')
        return self.sendSquareAudio(squareChatMid, path)

    @loggedIn
    def sendSquareFile(self, squareChatMid, path): # Under development
        return self.uploadObjSquare(squareChatMid=squareChatMid, path=path, type='file', returnAs='bool')

    @loggedIn
    def sendSquareFileWithURL(self, squareChatMid, url, fileName=''): # Under development
        path = self.downloadFileURL(url, 'path')
        return self.sendSquareFile(squareChatMid, path, fileName)

    """Square Message"""

    @loggedIn
    def sendSquareMessage(self, squareChatMid, text, contentMetadata={}, contentType=0):
        rq = SendMessageRequest()
        rq.squareChatMid = squareChatMid
        rq.squareMessage = SquareMessage()
        msg = Message()
        msg.to = squareChatMid
        msg.text = text
        msg.contentType, msg.contentMetadata = contentType, contentMetadata
        rq.squareMessage.message = msg
        rq.squareMessage.fromType = 4
        if squareChatMid not in self._messageReq:
            self._messageReq[squareChatMid] = -1
        self._messageReq[squareChatMid] += 1
        rq.squareMessage.squareMessageRevision = self._messageReq[squareChatMid]
        return self.square.sendMessage(rq)

    @loggedIn
    def sendSquareSticker(self, squareChatMid, packageId, stickerId):
        contentMetadata = {
            'STKVER': '100',
            'STKPKGID': packageId,
            'STKID': stickerId
        }
        return self.sendSquareMessage(squareChatMid, '', contentMetadata, 7)

    @loggedIn
    def sendSquareContact(self, squareChatMid, mid):
        contentMetadata = {'mid': mid}
        return self.sendSquareMessage(squareChatMid, '', contentMetadata, 13)

    @loggedIn
    def sendSquareGift(self, squareChatMid, productId, productType):
        if productType not in ['theme','sticker']:
            raise Exception('產品類型值無效')
        contentMetadata = {
            'MSGTPL': str(random.randint(0, 10)),
            'PRDTYPE': productType.upper(),
            'STKPKGID' if productType == 'sticker' else 'PRDID': productId
        }
        return self.sendSquareMessage(squareChatMid, '', contentMetadata, 9)

    @loggedIn
    def destroySquareMessage(self, squareChatMid, messageId):
        rq = DestroyMessageRequest()
        rq.squareChatMid = squareChatMid
        rq.messageId = messageId
        return self.square.destroyMessage(rq)

    """Square"""

    @loggedIn
    def searchSquareMembers(self, squareMid, continuationToken=None, limit=50):
        rq = SearchSquareMembersRequest()
        rq.squareMid = squareMid
        rq.searchOption = SquareMemberSearchOption()
        rq.continuationToken = continuationToken
        rq.limit = limit
        return self.square.searchSquareMembers(rq)

    @loggedIn
    def findSquareByInvitationTicket(self, invitationTicket):
        rq = FindSquareByInvitationTicketRequest()
        rq.invitationTicket = invitationTicket
        return self.square.findSquareByInvitationTicket(rq)

    @loggedIn
    def approveSquareMembers(self, squareMid, requestedMemberMids=[]):
        rq = ApproveSquareMembersRequest()
        rq.squareMid = squareMid
        rq.requestedMemberMids = requestedMemberMids
        return self.square.approveSquareMembers(rq)

    @loggedIn
    def deleteSquare(self, mid):
        rq = DeleteSquareRequest()
        rq.mid = mid
        rq.revision = self.revision
        return self.square.deleteSquare(rq)

    @loggedIn
    def deleteSquareChat(self, squareChatMid):
        rq = DeleteSquareChatRequest()
        rq.squareChatMid = squareChatMid
        rq.revision = self.revision
        return self.square.deleteSquareChat(request)

    @loggedIn
    def createSquare(self, name, categoryID, welcomeMessage='', profileImageObsHash='', desc='', searchable=True, type=1, ableToUseInvitationTicket=True):
        rq = CreateSquareRequest()
        rq.square = Square()
        rq.square.name = name
        rq.square.categoryID = categoryID
        rq.square.welcomeMessage = welcomeMessage
        rq.square.profileImageObsHash = profileImageObsHash
        rq.square.desc = desc
        rq.square.searchable = searchable
        rq.square.type = type
        rq.square.ableToUseInvitationTicket = ableToUseInvitationTicket
        rq.creator = SquareMember()
        return self.square.createSquare(rq)

    @loggedIn
    def createSquareChat(self, squareMid, name, squareMemberMids):
        rq = CreateSquareChatRequest()
        rq.reqSeq = self.revision
        rq.squareChat = SquareChat()
        rq.squareChat.squareMid = squareMid
        rq.squareChat.name = name
        rq.squareMemberMids = squareMemberMids
        return self.square.createSquareChat(request)

    @loggedIn
    def fetchSquareChatEvents(self, squareChatMid, subscriptionId=0, syncToken='', limit=50, direction=2):
        rq = FetchSquareChatEventsRequest()
        rq.squareChatMid = squareChatMid
        rq.subscriptionId = subscriptionId
        rq.syncToken = syncToken
        rq.limit = limit
        rq.direction = direction
        return self.square.fetchSquareChatEvents(rq)

    @loggedIn
    def fetchMyEvents(self, subscriptionId=0, syncToken='', continuationToken=None, limit=50):
        rq = FetchMyEventsRequest()
        rq.subscriptionId = subscriptionId
        rq.syncToken = syncToken
        rq.continuationToken = continuationToken
        rq.limit = limit
        return self.square.fetchMyEvents(rq)

    @loggedIn
    def markAsRead(self, squareChatMid, messageId):
        rq = MarkAsReadRequest()
        rq.squareChatMid = squareChatMid
        rq.messageId = messageId
        return self.square.markAsRead(rq)

    @loggedIn
    def getSquareAuthority(self, squareMid):
        rq = GetSquareAuthorityRequest()
        rq.squareMid = squareMid
        return self.square.getSquareAuthority(rq)

    @loggedIn
    def leaveSquare(self, squareMid):
        rq = LeaveSquareRequest()
        rq.squareMid = squareMid
        return self.square.leaveSquare(rq)

    @loggedIn
    def leaveSquareChat(self, squareChatMid, squareChatMemberRevision, sayGoodbye=True):
        rq = LeaveSquareChatRequest()
        rq.squareChatMid = squareChatMid
        rq.sayGoodbye = sayGoodbye
        rq.squareChatMemberRevision = squareChatMemberRevision
        return self.square.leaveSquareChat(rq)

    @loggedIn
    def joinSquareChat(self, squareChatMid):
        rq = JoinSquareChatRequest()
        rq.squareChatMid = squareChatMid
        return self.square.joinSquareChat(rq)

    @loggedIn
    def joinSquare(self, squareMid, displayName, profileImageObsHash):
        rq = JoinSquareRequest()
        rq.squareMid = squareMid
        rq.member = SquareMember()
        rq.member.squareMid = squareMid
        rq.member.displayName = displayName
        rq.member.profileImageObsHash = profileImageObsHash
        return self.square.joinSquare(rq)

    @loggedIn
    def inviteToSquare(self, squareMid, squareChatMid, invitees=[]):
        rq = InviteToSquareRequest()
        rq.squareMid = squareMid
        rq.invitees = invitees
        rq.squareChatMid = squareChatMid
        return self.square.inviteToSquare(rq)

    @loggedIn
    def inviteToSquareChat(self, squareChatMid, inviteeMids=[]):
        rq = InviteToSquareChatRequest()
        rq.inviteeMids = inviteeMids
        rq.squareChatMid = squareChatMid
        return self.square.inviteToSquareChat(rq)

    @loggedIn
    def getSquareMember(self, squareMemberMid):
        rq = GetSquareMemberRequest()
        rq.squareMemberMid = squareMemberMid
        return self.square.getSquareMember(rq)

    @loggedIn
    def getSquareMembers(self, mids=[]):
        rq = GetSquareMembersRequest()
        rq.mids = mids
        return self.square.getSquareMembers(rq)

    @loggedIn
    def getSquareMemberRelation(self, squareMid, targetSquareMemberMid):
        rq = GetSquareMemberRelationRequest()
        rq.squareMid = squareMid
        rq.targetSquareMemberMid = targetSquareMemberMid
        return self.square.getSquareMemberRelation(rq)

    @loggedIn
    def getSquareMemberRelations(self, state=1, continuationToken=None, limit=50):
        rq = GetSquareMemberRelationsRequest()
        rq.state = state # 1 NONE, 2 BLOCKED
        rq.continuationToken = continuationToken
        rq.limit = limit
        return self.square.getSquareMemberRelations(rq)

    @loggedIn
    def getSquareChatMembers(self, squareChatMid, continuationToken=None, limit=50):
        rq = GetSquareChatMembersRequest()
        rq.squareChatMid = squareChatMid
        rq.continuationToken = continuationToken
        rq.limit = limit
        return self.square.getSquareChatMembers(rq)

    @loggedIn
    def getSquareChatStatus(self, squareChatMid):
        rq = GetSquareChatStatusRequest()
        rq.squareChatMid = squareChatMid
        return self.square.getSquareChatStatus(rq)

    @loggedIn
    def getSquareChat(self, squareChatMid):
        rq = GetSquareChatRequest()
        rq.squareChatMid = squareChatMid
        return self.square.getSquareChat(rq)

    @loggedIn
    def getSquare(self, mid):
        rq = GetSquareRequest()
        rq.mid = mid
        return self.square.getSquare(rq)

    @loggedIn
    def getSquareChatAnnouncements(self, squareChatMid):
        rq = GetSquareChatAnnouncementsRequest()
        rq.squareChatMid = squareChatMid
        return self.square.getSquareChatAnnouncements(rq)

    @loggedIn
    def deleteSquareChatAnnouncement(self, squareChatMid, announcementSeq):
        rq = DeleteSquareChatAnnouncementRequest()
        rq.squareChatMid = squareChatMid
        rq.squareChatMid = announcementSeq
        return self.square.deleteSquareChatAnnouncement(rq)

    @loggedIn
    def createSquareChatAnnouncement(self, squareChatMid, text, messageId='', senderSquareMemberMid=''):
        rq = CreateSquareChatAnnouncementRequest()
        rq.reqSeq = 0
        rq.squareChatMid = squareChatMid
        rq.squareChatAnnouncement = SquareChatAnnouncement()
        rq.squareChatAnnouncement.announcementSeq = 0
        rq.squareChatAnnouncement.type = 0
        rq.squareChatAnnouncement.contents = SquareChatAnnouncementContents()
        rq.squareChatAnnouncement.contents.textMessageAnnouncementContents = TextMessageAnnouncementContents()
        rq.squareChatAnnouncement.contents.textMessageAnnouncementContents.messageId = messageId
        rq.squareChatAnnouncement.contents.textMessageAnnouncementContents.text = text
        rq.squareChatAnnouncement.contents.textMessageAnnouncementContents.senderSquareMemberMid = senderSquareMemberMid
        return self.square.createSquareChatAnnouncement(rq)

    @loggedIn
    def getJoinedSquares(self, continuationToken=None, limit=50):
        rq = GetJoinedSquaresRequest()
        rq.continuationToken = continuationToken
        rq.limit = limit
        return self.square.getJoinedSquares(rq)

    @loggedIn
    def getJoinedSquareChats(self, continuationToken=None, limit=50):
        rq = GetJoinedSquareChatsRequest()
        rq.continuationToken = continuationToken
        rq.limit = limit
        return self.square.getJoinedSquareChats(rq)

    @loggedIn
    def getJoinableSquareChats(self, squareMid, continuationToken=None, limit=50):
        rq = GetJoinableSquareChatsRequest()
        rq.squareMid = squareMid
        rq.continuationToken = continuationToken
        rq.limit = limit
        return self.square.getJoinableSquareChats(rq)

    @loggedIn
    def getInvitationTicketUrl(self, mid):
        rq = GetInvitationTicketUrlRequest()
        rq.mid = mid
        return self.square.getInvitationTicketUrl(rq)

    @loggedIn
    def getSquareStatus(self, squareMid):
        rq = GetSquareStatusRequest()
        rq.squareMid = squareMid
        return self.square.getSquareStatus(rq)

    @loggedIn
    def getNoteStatus(self, squareMid):
        rq = GetNoteStatusRequest()
        rq.squareMid = squareMid
        return self.square.getNoteStatus(rq)

    @loggedIn
    def searchSquares(self, query, continuationToken=None, limit=50):
        rq = SearchSquaresRequest()
        rq.query = query
        rq.continuationToken = continuationToken
        rq.limit = limit
        return self.square.searchSquares(rq)

    @loggedIn
    def refreshSubscriptions(self, subscriptions=[]):
        rq = RefreshSubscriptionsRequest()
        rq.subscriptions = subscriptions
        return self.square.refreshSubscriptions(rq)

    @loggedIn
    def removeSubscriptions(self, unsubscriptions=[]):
        rq = RemoveSubscriptionsRequest()
        rq.unsubscriptions = unsubscriptions
        return self.square.removeSubscriptions(rq)

class Session:

    def __init__(self, url, headers, path=''):
        self.host = url + path
        self.headers = headers
    def Auth(self, isopen=True):
        self.transport = THttpClient.THttpClient(self.host)
        self.transport.setCustomHeaders(self.headers)
        self.protocol = TCompactProtocol.TCompactProtocol(self.transport)
        self._auth  = AuthService.Client(self.protocol)
        if isopen:
            self.transport.open()
        return self._auth
    def Talk(self, isopen=True):
        self.transport = THttpClient.THttpClient(self.host)
        self.transport.setCustomHeaders(self.headers)
        self.protocol = TCompactProtocol.TCompactProtocol(self.transport)
        self._talk  = TalkService.Client(self.protocol)
        if isopen:
            self.transport.open()
        return self._talk
    def Channel(self, isopen=True):
        self.transport = THttpClient.THttpClient(self.host)
        self.transport.setCustomHeaders(self.headers)
        self.protocol = TCompactProtocol.TCompactProtocol(self.transport)
        self._channel  = ChannelService.Client(self.protocol)
        if isopen:
            self.transport.open()
        return self._channel
    def Call(self, isopen=True):
        self.transport = THttpClient.THttpClient(self.host)
        self.transport.setCustomHeaders(self.headers)
        self.protocol = TCompactProtocol.TCompactProtocol(self.transport)
        self._call  = CallService.Client(self.protocol)
        if isopen:
            self.transport.open()
        return self._call
    def Square(self, isopen=True):
        self.transport = THttpClient.THttpClient(self.host)
        self.transport.setCustomHeaders(self.headers)
        self.protocol = TCompactProtocol.TCompactProtocol(self.transport)
        self._square  = SquareService.Client(self.protocol)
        if isopen:
            self.transport.open()
        return self._square

    def Liff(self, isopen=True):
        self.transport = THttpClient.THttpClient(self.host)
        self.transport.setCustomHeaders(self.headers)
        self.protocol = TCompactProtocol.TCompactProtocol(self.transport)
        self._liff  = TalkService.Client(self.protocol)
        if isopen:
            self.transport.open()
        return self._liff

class Server(Config):
    _session        = requests.session()
    timelineHeaders = {}
    Headers         = {}

    def __init__(self):
        self.Headers = {}
        self.channelHeaders = {}
        Config.__init__(self)

    def parseUrl(self, path):
        return self.LINE_HOST_DOMAIN + path

    def urlEncode(self, url, path, params=[]):
        return url + path + '?' + urllib.parse.urlencode(params)

    def getJson(self, url, allowHeader=False):
        if allowHeader is False:
            return json.loads(self._session.get(url).text)
        else:
            return json.loads(self._session.get(url, headers=self.Headers).text)

    def setHeadersWithDict(self, headersDict):
        self.Headers.update(headersDict)

    def setHeaders(self, argument, value):
        self.Headers[argument] = value

    def setTimelineHeadersWithDict(self, headersDict):
        self.timelineHeaders.update(headersDict)

    def setTimelineHeaders(self, argument, value):
        self.timelineHeaders[argument] = value

    def additionalHeaders(self, source, newSource):
        headerList={}
        headerList.update(source)
        headerList.update(newSource)
        return headerList

    def optionsContent(self, url, data=None, headers=None):
        if headers is None:
            headers=self.Headers
        return self._session.options(url, headers=headers, data=data)

    def postContent(self, url, data=None, files=None, headers=None):
        if headers is None:
            headers=self.Headers
        return self._session.post(url, headers=headers, data=data, files=files)

    def getContent(self, url, headers=None):
        if headers is None:
            headers=self.Headers
        return self._session.get(url, headers=headers, stream=True)

    def deleteContent(self, url, data=None, headers=None):
        if headers is None:
            headers=self.Headers
        return self._session.delete(url, headers=headers, data=data)

    def putContent(self, url, data=None, headers=None):
        if headers is None:
            headers=self.Headers
        return self._session.put(url, headers=headers, data=data)

class Callback(object):

    def __init__(self, callback):
        self.callback = callback

    def PinVerified(self, pin):
        self.callback("輸入此PIN碼 '" + pin + "' 在2分鐘內在您手機的LINE上")

    def QrUrl(self, url, showQr=True):
        if showQr:
            notice='或掃描此QR '
        else:
            notice=''
        self.callback('打開此鏈接 ' + notice + '在2分鐘內在您手機的LINE上\n' + url)
        if showQr:
            try:
                import pyqrcode
                url = pyqrcode.create(url)
                self.callback(url.terminal('green', 'white', 1))
            except:
                pass
        a = url
        return a

    def default(self, str):
        self.callback(str)

class Object(object):

    def __init__(self):
        if self.isLogin == True:
            self.log("[%s] : 登入成功" % self.profile.displayName)

    """Group"""

    @loggedIn
    def updateGroupPicture(self, groupId, path):
        files = {'file': open(path, 'rb')}
        data = {'params': self.genOBSParams({'oid': groupId,'type': 'image'})}
        r = self.server.postContent(self.server.LINE_OBS_DOMAIN + '/talk/g/upload.nhn', data=data, files=files)
        if r.status_code != 201:
            raise Exception('更新組圖片失敗。')
        return True

    """Personalize"""

    @loggedIn
    def updateProfilePicture(self, path, type='p'):
        files = {'file': open(path, 'rb')}
        params = {'oid': self.profile.mid,'type': 'image'}
        if type == 'vp':
            params.update({'ver': '2.0', 'cat': 'vp.mp4'})
        data = {'params': self.genOBSParams(params)}
        r = self.server.postContent(self.server.LINE_OBS_DOMAIN + '/talk/p/upload.nhn', data=data, files=files)
        if r.status_code != 201:
            raise Exception('更新資料圖片失敗。')
        return True

    @loggedIn
    def updateProfileVideoPicture(self, path):
        try:
            from ffmpy import FFmpeg
            files = {'file': open(path, 'rb')}
            data = {'params': self.genOBSParams({'oid': self.profile.mid,'ver': '2.0','type': 'video','cat': 'vp.mp4'})}
            r_vp = self.server.postContent(self.server.LINE_OBS_DOMAIN + '/talk/vp/upload.nhn', data=data, files=files)
            if r_vp.status_code != 201:
                raise Exception('更新個人資料視頻圖片失敗')
            path_p = self.genTempFile('path')
            ff = FFmpeg(inputs={'%s' % path: None}, outputs={'%s' % path_p: ['-ss', '00:00:2', '-vframes', '1']})
            ff.run()
            self.updateProfilePicture(path_p, 'vp')
        except:
            raise Exception('You should install FFmpeg and ffmpy from pypi')

    @loggedIn
    def updateProfileCover(self, path, returnAs='bool'):
        if returnAs not in ['objId','bool']:
            raise Exception('返回值無效')
        objId = self.uploadObjHome(path, type='image', returnAs='objId')
        home = self.updateProfileCoverById(objId)
        if returnAs == 'objId':
            return objId
        elif returnAs == 'bool':
            return True

    """Object"""

    @loggedIn
    def uploadObjSquare(self, squareChatMid, path, type='image', returnAs='bool'):
        if returnAs not in ['bool']:
            raise Exception('返回值無效')
        if type not in ['image','gif','video','audio','file']:
            raise Exception('Invalid type value')
        data = open(path, 'rb').read()
        params = {
            'oid': 'reqseq',
            'reqseq': '%s' % str(self.revision),
            'tomid': '%s' % str(squareChatMid),
            'size': '%s' % str(len(data)),
            'range': len(data),
            'type': '%s' % str(type)
        }
        if type == 'image':
            contentType = 'image/jpeg'
        elif type == 'gif':
            contentType = 'image/gif'
        elif type == 'video':
            params.update({'duration': '60000'})
            contentType = 'video/mp4'
        elif type == 'audio':
            params.update({'duration': '0'})
            contentType = 'audio/mp3'
        headers = self.server.additionalHeaders(self.server.Headers, {
            'content-type': contentType,
            'Content-Length': str(len(data)),
            'x-obs-params': self.genOBSParams(params,'b64'),
            'X-Line-Access': self.squareObsToken
        })
        r = self.server.postContent(self.server.LINE_OBS_DOMAIN + '/r/g2/m/reqseq', data=data, headers=headers)
        if r.status_code != 201:
            raise Exception('上 %s 失敗。' % type)
        if returnAs == 'bool':
            return True

    @loggedIn
    def uploadObjTalk(self, path, type='image', returnAs='bool', objId=None, to=None):
        if returnAs not in ['objId','bool']:
            raise Exception('返回值無效')
        if type not in ['image','gif','video','audio','file']:
            raise Exception('無效的類型值')
        headers=None
        files = {'file': open(path, 'rb')}
        if type == 'image' or type == 'video' or type == 'audio' or type == 'file':
            e_p = self.server.LINE_OBS_DOMAIN + '/talk/m/upload.nhn'
            data = {'params': self.genOBSParams({'oid': objId,'size': len(open(path, 'rb').read()),'type': type})}
        elif type == 'gif':
            e_p = self.server.LINE_OBS_DOMAIN + '/r/talk/m/reqseq'
            files = None
            data = open(path, 'rb').read()
            params = {
                'oid': 'reqseq',
                'reqseq': '%s' % str(self.revision),
                'tomid': '%s' % str(to),
                'size': '%s' % str(len(data)),
                'range': len(data),
                'type': 'image'
            }
            headers = self.server.additionalHeaders(self.server.Headers, {
                'Content-Type': 'image/gif',
                'Content-Length': str(len(data)),
                'x-obs-params': self.genOBSParams(params,'b64')
            })
        r = self.server.postContent(e_p, data=data, headers=headers, files=files)
        if r.status_code != 201:
            raise Exception('上傳 %s 失敗。' % type)
        if returnAs == 'objId':
            return objId
        elif returnAs == 'bool':
            return True

    @loggedIn
    def uploadObjHome(self, path, type='image', returnAs='bool', objId=None):
        if returnAs not in ['objId','bool']:
            raise Exception('返回值無效')
        if type not in ['image','video','audio']:
            raise Exception('無效的類型值')
        if type == 'image':
            contentType = 'image/jpeg'
        elif type == 'video':
            contentType = 'video/mp4'
        elif type == 'audio':
            contentType = 'audio/mp3'
        if not objId:
            objId = int(time.time())
        file = open(path, 'rb').read()
        params = {
            'userid': '%s' % self.profile.mid,
            'oid': '%s' % str(objId),
            'range': len(file),
            'type': type
        }
        hr = self.server.additionalHeaders(self.server.timelineHeaders, {
            'Content-Type': contentType,
            'Content-Length': str(len(file)),
            'x-obs-params': self.genOBSParams(params,'b64')
        })
        r = self.server.postContent(self.server.LINE_OBS_DOMAIN + '/myhome/c/upload.nhn', headers=hr, data=file)
        if r.status_code != 201:
            raise Exception('上傳對象主頁失敗。')
        if returnAs == 'objId':
            return objId
        elif returnAs == 'bool':
            return True

    @loggedIn
    def downloadObjectMsg(self, messageId, returnAs='path', saveAs=''):
        if saveAs == '':
            saveAs = self.genTempFile('path')
        if returnAs not in ['path','bool','bin']:
            raise Exception('返回值無效')
        params = {'oid': messageId}
        url = self.server.urlEncode(self.server.LINE_OBS_DOMAIN, '/talk/m/download.nhn', params)
        r = self.server.getContent(url)
        if r.status_code == 200:
            self.saveFile(saveAs, r.raw)
            if returnAs == 'path':
                return saveAs
            elif returnAs == 'bool':
                return True
            elif returnAs == 'bin':
                return r.raw
        else:
            raise Exception('下載對象失敗。')

    @loggedIn
    def forwardObjectMsg(self, to, msgId, contentType='image'):
        if contentType not in ['image','video','audio']:
            raise Exception('Type not valid.')
        data = self.genOBSParams({'oid': 'reqseq','reqseq': self.revision,'type': contentType,'copyFrom': '/talk/m/%s' % msgId},'default')
        r = self.server.postContent(self.server.LINE_OBS_DOMAIN + '/talk/m/copy.nhn', data=data)
        if r.status_code != 200:
            raise Exception('轉發對象失敗。')
        return True

class Models(Object):

    def __init__(self):
        Object.__init__(self)

    """Text"""

    def log(self, text):
        print("[%s] %s" % (str(datetime.now()), text))

    """File"""

    def saveFile(self, path, raw):
        with open(path, 'wb') as f:
            shutil.copyfileobj(raw, f)

    def deleteFile(self, path):
        if os.path.exists(path):
            os.remove(path)
            return True
        else:
            return False

    def downloadFileURL(self, fileUrl, returnAs='path', saveAs='', headers=None):
        if returnAs not in ['path','bool','bin']:
            raise Exception('返回值無效')
        if saveAs == '':
            saveAs = self.genTempFile()
        r = self.server.getContent(fileUrl, headers=headers)
        if r.status_code != 404:
            self.saveFile(saveAs, r.raw)
            if returnAs == 'path':
                return saveAs
            elif returnAs == 'bool':
                return True
            elif returnAs == 'bin':
                return r.raw
        else:
            raise Exception('下載文件失敗。')

    """Generator"""

    def genTempFile(self, returnAs='path'):
        try:
            if returnAs not in ['file','path']:
                raise Exception('返回值無效')
            fName, fPath = 'linepy-%s-%i.bin' % (int(time.time()), randint(0, 9)), tempfile.gettempdir()
            if returnAs == 'file':
                return fName
            elif returnAs == 'path':
                return os.path.join(fPath, fName)
        except:
            raise Exception('臨時文件是必需的')

    def genOBSParams(self, newList, returnAs='json'):
        oldList = {'name': self.genTempFile('file'),'ver': '1.0'}
        if returnAs not in ['json','b64','default']:
            raise Exception('無效的參數返回為')
        oldList.update(newList)
        if 'range' in oldList:
            new_range='bytes 0-%s\/%s' % ( str(oldList['range']-1), str(oldList['range']) )
            oldList.update({'range': new_range})
        if returnAs == 'json':
            oldList=json.dumps(oldList)
            return oldList
        elif returnAs == 'b64':
            oldList=json.dumps(oldList)
            return base64.b64encode(oldList.encode('utf-8'))
        elif returnAs == 'default':
            return oldList

class Liff(object):
    isLogin = False
    def __init__(self):
        self.isLogin = True
    @loggedIn
    def issueLiffView(self, to):
        az = LiffChatContext(to)
        ax = LiffContext(chat=az)
        lf = LiffViewRequest('1654773370-bl8pnONV', ax)
        return self.liff.issueLiffView(lf)
    @loggedIn
    def sendFlex(self, to, data):
        token = self.issueLiffView(to)
        url = 'https://api.line.me/message/v3/share'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % token.accessToken
        }
        data = {
            'messages': [data]
        }
        res = requests.post(url, headers=headers, data=json.dumps(data))
        return res
    @loggedIn
    def issueLiffSquareView(self, to):
        az = LiffSquareChatContext(to)
        ax = LiffContext(squareChat=az)
        lf = LiffViewRequest('1654773370-bl8pnONV', ax)
        return self.liff.issueLiffView(lf)
    @loggedIn
    def postSquareTemplate(self, to, data):
        token = self.issueLiffSquareView(to)
        url = 'https://api.line.me/message/v3/share'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % token.accessToken
        }
        data = {
            'messages': [data]
        }
        res = requests.post(url, headers=headers, data=json.dumps(data))
        return res

class LINE(Auth, Models, Talk, Square, Call, Timeline, Liff):

    def __init__(self, idOrAuthToken=None, passwd=None, certificate=None, systemName=None, appName=None, showQr=False, keepLoggedIn=True):

        Auth.__init__(self)
        if not (idOrAuthToken or idOrAuthToken and passwd):
            self.loginWithQrCode(keepLoggedIn=keepLoggedIn, systemName=systemName, appName=appName, showQr=showQr)
        if idOrAuthToken and passwd:
            self.loginWithCredential(_id=idOrAuthToken, passwd=passwd, certificate=certificate, systemName=systemName, appName=appName, keepLoggedIn=keepLoggedIn)
        elif idOrAuthToken and not passwd:
            self.loginWithAuthToken(authToken=idOrAuthToken, appName=appName)

        self.__initAll()

    def __initAll(self):

        self.profile    = self.talk.getProfile()
        self.groups     = self.talk.getGroupIdsJoined()

        Models.__init__(self)
        Talk.__init__(self)
        Square.__init__(self)
        Call.__init__(self)
        Timeline.__init__(self)
        Liff.__init__(self)
