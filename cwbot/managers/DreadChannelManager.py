import re
import time
from cwbot.managers.BaseClanDungeonChannelManager \
             import BaseClanDungeonChannelManager


class DreadError(Exception):
    pass
            
            
class DreadChannelManager(BaseClanDungeonChannelManager):
    """ Subclass of BaseClanDungeonChannelManager. 
    This manager monitors Dreadsylvania in specific, resetting all its modules
    when the instance is reset.
    """
    
    _csvFile = "dread.csv"

    capabilities = set(['chat', 'inventory', 'admin', 'dread'])

    def __init__(self, parent, identity, iData, config):
        """ Initialize the DreadChannelManager """
        self.__initialized = False
        self._dvid = None
        self._active = None # TRUE if an area is still active
        super(DreadChannelManager, self).__init__(parent, identity, iData, 
                                                 config)
        if 'dread' not in self._channelName:
            raise Exception("DreadChannelManager must be listening to "
                            "/dread!")
        self.__initialized = True
        
        
    def _configure(self, config):
        """ Additional configuration for the log_check_interval option """
        super(DreadChannelManager, self)._configure(config)
        
        
    def _initialize(self):
        """ This function initializes the modules with log data and 
        persistent state information. For the DreadChannelManager, old
        persistent state is deleted if a new instance is detected. 
        """
        # unlike "normal" modules, dungeon modules' states are reset 
        # after a new instance is created.
        # so, there is an extra step: if a new dungeon instance exists, 
        # the state is cleared.
        self._initializeFromLog()
        
        try:
            # check database integrity
            if len(self._persist) == 0:
                self._persist['__init__'] = ""
        except ValueError:
            self._clearPersist()
            
        if '__dvid__' not in self._persist:
            # dread id number not in state! This should never happen
            # but if it does, delete the old state.
            self._log.warning("Dreadsylvania instance not present in state.")
            self._clearPersist()
            self._persist['__dvid__'] = self._dvid
        else:
            dvid_old = self._persist['__dvid__']
            self._log.info("Old instance: {}".format(dvid_old))
            dvid_new = self._dvid
            self._log.info("Current instance: {}".format(dvid_new))
            if dvid_old != dvid_new:

                self._log.info("New Dreadsylvania instance. Clearing state...")
                self._clearPersist()
            else:
                self._log.info("Same Dreadsylvania instance as last shutdown.")
        super(DreadChannelManager, self)._initialize()
        

    def _filterEvents(self, raidlog):
        relevant_keys = ['dvid', 'dread', 'events']
        relevant_event_categories = ['The Village', 
                                     'The Woods', 
                                     'The Castle', 
                                     'Miscellaneous']
        d = {k: v for k,v in raidlog.items() if k in relevant_keys}
        d = self._dbMatchRaidLog(d)
        d['events'] = [e for e in d['events'] 
                           if e['category'] in relevant_event_categories]
        return d
    
    
    def _syncState(self, force=False):
        '''Store persistent data for Hobo Modules. Here there is the 
        extra step of storing the old log and hoid. '''
        with self._syncLock:
            if self._persist is not None:
                self._persist['__dvid__'] = self._dvid
            super(DreadChannelManager, self)._syncState(force)

    
    def _initializeFromLog(self):
        """ Initialize active status """
        raidlog = self._filterEvents(self.lastEvents)
        self._log.info("Initializing from Dreadsylvania log...")
        
        self._active = self._dungeonIsActive(raidlog)
        self._log.info("Dread active = {}".format(self._active))
        self._dvid = raidlog.get('dvid', None)


    def _dungeonIsActive(self, raidlog):
        """ Check if dungeon is active """
        bossesKilled = [e for e in raidlog['events']
                        if e['db-match'].get("zone") == "(combat)"
                        and e['db-match'].get("subzone") == "boss"]
        return len(bossesKilled) < 3
    

    def _handleNewRaidlog(self, raidlog):
        """ Get log events and update active state """
        if not self.__initialized:
            return
        # search current log to see if hodgman is dead, if he's not
        # a new dungeon has started
        if not self._active:
            if self._dungeonIsActive(raidlog):
                self._log.info("Dungeon reset... new instance should "
                               "appear soon.")
                self._active = True
        else:
            if not self._dungeonIsActive(raidlog):
                self._active = False
                self._log.info("Dread clear!")

        newDvid = raidlog.get('dvid', None)
        if newDvid is not None and newDvid != self._dvid:
            self._log.info("Dread instance number {} (old instance {})"
                           .format(newDvid, self._dvid))
            if self._dvid is not None:
                # oldDvid is only None upon first startup. So now it's
                # time to reset!
                self._resetDungeon()
            self._dvid = newDvid
        

    def active(self):
        """ Are the bosses dead? """
        return self._active
    
    
    def _resetDungeon(self):
        """ 
        This function is called when a new Dreadsylvania instance is detected.
        """

        with self._syncLock:
            self._active = True
            self.sendChatMessage("The dungeon has been reset!")
            self._log.info("---- DUNGEON RESET {} ----"
                                  .format(time.strftime(
                                                    '%c', time.localtime())))
            self._clearPersist()
            for m in self._modules:
                mod = m.module
                self._log.debug("Resetting {}".format(mod.id))
                mod.reset(self._moduleInitData())

