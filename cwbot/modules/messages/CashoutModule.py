from cwbot.modules.BaseKmailModule import BaseKmailModule
from kol.database.ItemDatabase import getOrDiscoverItemFromId
import kol.Error


class CashoutModule(BaseKmailModule):
    """ 
    A module that "cashes out" items withheld due to ronin/HC status.
    
    No configuration options.
    """
    requiredCapabilities = ['kmail']
    _name = "cashout"
    
    def __init__(self, manager, identity, config):
        super(CashoutModule, self).__init__(manager, identity, config)

        
    def _processKmail(self, message):
        if message.text.strip().lower() == "cashout":
            self.log("Cashout message: {}".format(message))
            try:
                self.parent.director.cashout(message.uid)
                return self.newMessage(-1)
            except IndexError:
                return self.newMessage(message.uid, "I don't have any items "
                                                    "stored for you.")
        elif message.text.strip().lower() == "balance":
            (meat, items) = self.parent.director.balance(message.uid)
            if meat == 0 and len(items) == 0:
                return self.newMessage(message.uid, "I don't have any items "
                                                    "stored for you.")
            text = "Your balance: \n"
            for iid, qty in items.items():
                try:
                    itemName = getOrDiscoverItemFromId(iid, self.session).get(
                                          'name', "item ID {}".format(iid))
                except kol.Error.Error:
                    itemName = "item ID {}".format(iid)
                text += ("\n{}: {}".format(qty, itemName))
            if meat > 0:
                text += "\n{} meat".format(meat)
            text += "\n\nIf you are ready to retrieve your items, send a kmail with the text \"cashout\".\n"
            text += "\nIf you don't want your items back, send a kmail with the text \"clear balance\"."
            return self.newMessage(message.uid, text)
        elif message.text.strip().lower() == "clear balance":
            self.parent.director.clearBalance(message.uid)
            return self.newMessage(message.uid, "Your balance has been cleared.")

    def _kmailDescription(self):
        return ("CASHING OUT: If I am holding any items for you, send a kmail "
                "with the text \"cashout\" to get your stuff back. You can "
                "send a kmail with the text \"balance\" to get a list of what "
                "I am holding for you.")