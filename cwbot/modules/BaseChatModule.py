from BaseModule import BaseModule


class BaseChatModule(BaseModule):
    """A class to process chat !commands. Adds two extended calls:
    process_command -> _processCommand is called when chat !commands are
    passed through the manager. available_commands -> _avilableCommands
    returns a dict of commands and help text for !help commands and for a 
    few other purposes. """
    requiredCapabilities = []
    _name = ""
    
    
    def __init__(self, manager, identity, config):
        super(BaseChatModule, self).__init__(manager, identity, config)
        self._registerExtendedCall('process_command', self._processCommand)
        self._registerExtendedCall('available_commands', 
                                   self._availableCommands)


    def _processCommand(self, message, cmd, args):
        """
        Process chat commands (chats which start with !).
        If the module is not set as clan-only, all chats will be sent to this
        function. If it is clan-only, only commands matching those in
        _availableCommands() are sent here.
        
        The derived class should process those that apply and ignore the 
        others. 'message' contains the full message structure as defined by
        pyKol. 'cmd' contains the actual command (without the !) 
        in lower case. 'args' contains everything else.
        For example "!HeLLo     World 123" -> cmd = "hello", 
                                              args = "World 123"
        
        This function must return either a string, which will be printed in 
        chat, or None. Under the default managers, only the highest-priority
        module that sends a reply will be processed. If you want to reply
        but also allow the command to propagate, use the sendChatMessage() or
        whisper() methods instead.
        """
        pass
    

    def _availableCommands(self):
        """ Return a dict of available commands. Entries should be in the form
        "command": "text that is shown for help". To keep a command hidden,
        use the format "command": None. """
        return {}
