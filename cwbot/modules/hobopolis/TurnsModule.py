from cwbot.modules.BaseDungeonModule import BaseDungeonModule


class TurnsModule(BaseDungeonModule):
    """ 
    A stateless module that keeps track of number of turns spent in Hobopolis.
    
    No configuration options.
    """
    requiredCapabilities = ['chat', 'hobopolis']
    _name = "turns"

    def __init__(self, manager, identity, config):
        self._turns = None
        super(TurnsModule, self).__init__(manager, identity, config)

        
    def initialize(self, state, initData):
        self._processLog(initData)


    def _processLog(self, raidlog):
        events = raidlog['events']
        self._turns = 0
        for hobopolisevent in (item for item in events 
                               if "Slime" not in item['event']):
            self._turns += hobopolisevent['turns']
        return True

    
    def _processDungeon(self, dungeonText, raidlog):
        self._processLog(raidlog)
        return None

        
    def _processCommand(self, msg, cmd, args):
        if cmd in ["turns"]:
            if self._turns is not None:
                return ("{} turns have been spent in Hobopolis."
                        .format(self._turns))
        return None


    def _eventCallback(self, eData):
        if eData.subject == "turns":
            self._eventReply({'turns': self._turns})


    def _availableCommands(self):
        return {'turns': "Display total turns spent in Hobopolis."}
    