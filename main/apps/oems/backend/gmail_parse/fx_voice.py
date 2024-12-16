
from pygmail.process_inbox import ProcessInbox

# ============================================================================

class FxVoice(ProcessInbox):

    def __init__( self, **kwargs ):
        fetch_kwargs = {
            # 'labelIds': ['Label_2881366236640465922','UNREAD'],
            # Label_2881366236640465922 FX-VOICE label id
            'q': 'in:FX-VOICE is:unread',
        }
        super().__init__( fetch_kwargs=fetch_kwargs, **kwargs )

    def user_parse( self, message_id, msg ):
        dt          = self.get_msg_date( msg )
        info        = self.fetch_email_info( msg )
        attachments = self.fetch_attachments( msg )
        txt_list    = self.fetch_email_body( msg )
        print( info )
        print( txt_list )
        print( len(attachments), 'attachments found' )
        for att in attachments:
            print( att['name'] )
            print( att['data'] )
        self.mark_unread( message_id )

# ============================================================================

if __name__ == "__main__":

    app = FxVoice()
    msg = app.run()


