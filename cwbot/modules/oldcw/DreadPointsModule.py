from cwbot.modules.BaseDungeonModule import BaseDungeonModule
from cwbot.common.exceptions import FatalError
from cwbot.util.textProcessing import intOrFloatToString
from cwbot.common.kmailContainer import Kmail
from collections import defaultdict
import re
import random
import copy


def _nameKey(x):
    return "".join(x.split()).strip().lower()


class DreadPointsModule(BaseDungeonModule):
    """ 
    Determines points for Dreadsylvania.
    
    No configuration options.
    """
    requiredCapabilities = ['chat', 'dread']
    _name = "dread-kills"
    
    machineRegex = re.compile(r'used The Machine, assisted by (.*?) and (.*)$')
    
    def __init__(self, manager, identity, config):
        self._killPoints = None
        self._bossPoints = None
        self._machinePoints = None
        self._keyUnlocks = None
        self._drunkPoints = None
        self._codePts = None
        self._regexPts = None
        self._userPoints = None
        self._userEvents = None
        self._eventValue = None
        self._properUserNames = None
        self._userIds = None
        self._minPoints = None
        self._grantedPoints = None
        self._lastRaidlog = None
        super(DreadPointsModule, self).__init__(manager, identity, config)

        
    def initialize(self, state, initData):
        self._db = initData['event-db']

        lockedSubzones = set(record['subzone'] for record in self._db
                             if record['zone'] == "(unlock)")
        keySubzones = set(self._keyUnlocks.keys())
        if lockedSubzones != keySubzones:
            missing = lockedSubzones.difference(keySubzones)
            if missing:
                raise FatalError("DreadPointsModule: no 'keys' entry for '{}'"
                                 .format(missing.pop()))
            extra = keySubzones.difference(lockedSubzones)
            if extra:
                raise FatalError("DreadPointsModule: no such locked area '{}'"
                                 .format(extra.pop()))
        self._grantedPoints = state['granted']
        self._processLog(initData)
        
        
    @property
    def initialState(self):
        return {'granted': {}}
    
    
    @property
    def state(self):
        return {'granted': self._grantedPoints}
        
    
    def _configure(self, config):
        try:
            self._minPoints = int(config.setdefault('min_points_to_win', 1))
            self._killPoints = int(config.setdefault('kills', 1))
            self._bossPoints = int(config.setdefault('boss', 1))
            self._machinePoints = int(config.setdefault('machine_assist', 10))
        except ValueError:
            raise FatalError("DreadPointsModule: kills, boss, min_points "
                             "must be integers")
        try:
            self._drunkPoints = float(config.setdefault('drunk', 0.01))
        except ValueError:
            raise FatalError("DreadPointsModule: drunk must be float")
        self._keyUnlocks = config.setdefault('keys', {'Attic': 25, 
                                                'Fire Tower': 25,
                                                'Suite': 25,
                                                'School': 25,
                                                'Lab': 25,
                                                'Ballroom': 25})
        self._codePts = config.setdefault('codes', {})
        self._regexPts = config.setdefault('regex', {})
        try:
            self._keyUnlocks = {k: int(v) for k,v in self._keyUnlocks.items()}
            self._codePts = {k: int(v) for k,v in self._codePts.items()}
            self._regexPts = {k: int(v) for k,v in self._regexPts.items()}
        except ValueError:
            raise FatalError("DreadPointsModule: points "
                             "must be integers")


    def _processLog(self, raidlog):
        events = raidlog['events']
        self._lastRaidlog = copy.deepcopy(raidlog)
        self._userPoints = {}
        self._userIds = {}
        self._userEvents = defaultdict(lambda: defaultdict(int))
        self._eventValue = {'kill': self._killPoints, 
                            'boss': self._bossPoints,
                            'drunk': self._drunkPoints,
                            'given by admin': 1,
                            'machine assist': self._machinePoints}
        self._properUserNames = {}
        for e in events:
            user = _nameKey(e['userName'])
            self._userPoints.setdefault(user, 0)            
            self._properUserNames[user] = e['userName']
            self._userIds[user] = e['userId']
            match = e['db-match']
            zone = match.get('zone')
            subzone = match.get('subzone')
            code = match.get('code')
            event = e['event']
            turns = e['turns']
            
            if zone == "(combat)":
                if subzone == "normal":
                    self._userPoints[user] += self._killPoints * turns
                    self._userEvents[user]['kill'] += turns
                elif subzone == "boss":
                    self._userPoints[user] += self._bossPoints * turns
                    self._userEvents[user]['boss'] += turns
            elif zone == "(unlock)":
                txt = 'unlocked {}'.format(subzone)
                self._userPoints[user] += self._keyUnlocks[subzone] * turns
                self._userEvents[user][txt] += turns
                self._eventValue[txt] = self._keyUnlocks[subzone]

            if code in self._codePts:
                self._userPoints[user] += self._codePts[code] * turns
                self._userEvents[user][code] += turns
                self._eventValue[code] = self._codePts[code]
            
            for r,p in self._regexPts.items():
                m = re.search(r, event)
                if m:
                    self._userPoints[user] += p * turns
                    self._userEvents[user][m.group()] += turns
                    self._eventValue[m.group()] = p
                    
            # give points for helping in the machine
            m = self.machineRegex.search(event)
            if m:
                for i in [1, 2]:
                    # note: the message for the assist does not include the
                    # userId, so we will have to manually look for these
                    # users. 
                    assistUser = _nameKey(m.group(i))
                    if assistUser not in self._userPoints:
                        continue
                    self._userPoints[assistUser] += self._machinePoints * turns
                    self._userEvents[assistUser]['machine assist'] += turns
                    
        for e in raidlog['dread']['drunkActivity']:
            user = _nameKey(e['userName'])
            self._properUserNames[user] = e['userName']
            self._userIds[user] = e['userId']
            self._userPoints.setdefault(user, 0)            
            self._userPoints[user] += self._drunkPoints * e['drunkenness']
            self._userEvents[user]['drunk'] += e['drunkenness']
            
        for user,pts in self._grantedPoints.items():
            try:
                if pts != 0:
                    self._userPoints[user] += pts
                    self._userEvents[user]['given by admin'] += pts
            except KeyError:
                pass
        return True

            
    def _processCommand(self, msg, cmd, args):
        if cmd in ["points", "score"]:
            hasPermission = "dread_points" in self.properties.getPermissions(
                                                                msg['userId'])
            
            txt = "Current Dreadsylvania scores:\n\n"
            sortedUsers = list(self._userPoints.items())
            sortedUsers.sort(key=lambda x: -x[1])
            
            for user, points in sortedUsers:
                events = self._userEvents[user]
                if not events:
                    continue
                userName = self._properUserNames[user]
                userId = self._userIds[user]
                userTxt = ("[{}] {} (#{}): "
                           .format(intOrFloatToString(points, 2), 
                                   userName, 
                                   userId))
                userEventTxt = []
                for e, num in events.items():
                    value = self._eventValue[e]
                    userEventTxt.append("{} x {} ({:+})"
                        .format(num, e, value * num))
                userTxt += ", ".join(userEventTxt)
                txt += userTxt + "\n"
                
            if hasPermission and not self._dungeonActive():
                txt += "(use '!points official' to run drawing)\n"

            if args.lower().strip() in ["official", "test"]:
                if hasPermission:
                    if (self._dungeonActive() 
                            and args.lower().strip() != "test"):
                        return ("I can't perform the drawing until the "
                                "instance is done.")
                    else:
                        self._performDrawing()
                else:
                    return "You don't have permission to distribute loot."
            elif args and args.lower().strip().split()[0] in ["give", "grant"]:
                if not hasPermission:
                    return "You don't have permission to do that."
                isPM = (msg['type'] == "private")
                if isPM:
                    return "You can't grant points in a PM."
                match = re.search(r'(-?\d+)(?: points?)? to (.*)', 
                                  args, flags=re.IGNORECASE)
                if not match:
                    return "Invalid format."
                pointAmount = int(match.group(1))
                user = _nameKey(match.group(2))
                if user not in self._userPoints:
                    return "No such user {}.".format(match.group(2))
                self._grantedPoints.setdefault(user, 0)
                self._grantedPoints[user] += pointAmount
                self._processLog(self._lastRaidlog)
                return ("Granted {} points to {}"
                        .format(pointAmount, self._properUserNames[user]))
            else:
                self.sendKmail(Kmail(msg['userId'], txt))
                return "Kmail sent."
        return None


    def _performDrawing(self):
        availableUsers = {user: points 
                          for user,points in self._userPoints.items()
                          if points >= self._minPoints and points > 0}
        winList = []
        
        # order users by tournament selection
        while availableUsers:
            totalPoints = sum(availableUsers.values())
            selected = random.uniform(0, totalPoints)
            for user, points in availableUsers.items():
                selected -= points
                if selected < 0:
                    winList.append(user)
                    del availableUsers[user]
                    break
                
        self.chat("The order of loot distribution is:")
        i = 1
        for user in winList:
            self.chat("#{} {} (#{}) with {} points"
                      .format(i, 
                              self._properUserNames[user], 
                              self._userIds[user], 
                              intOrFloatToString(self._userPoints[user], 2)))
            i += 1
    
    
    def reset(self, initData):
        self._grantedPoints = {}
        super(DreadPointsModule, self).reset(initData)
        
                
    def _availableCommands(self):
        return {'points': "!points: Send a kmail with Dreadsylvania point "
                          "totals. Admins can use !points official to run "
                          "the lottery."}
    