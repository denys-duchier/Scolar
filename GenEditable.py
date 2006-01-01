"""
    Scolar class needs some doc...
"""

#
# This template allows to create a rather simple but yet usable
# Product object with the most commons tabs visible.
#
# It uses as far as possible the OO methodology, so management tabs
# are the ones provided by inherited classes.
# The 'Property' edit tab is present (but commented) with an example
# form (dtml/manage_editScolarForm). So the overriding of this most
# used tab will be easy.
#
# The help/Scolar-add.dtml page is available when adding a new
# Scolar object. The -edit- one is used by default if you override
# the 'Property' tab.
#


from OFS.SimpleItem import Item # Basic zope object
from OFS.PropertyManager import PropertyManager # provide the 'Properties' tab with the
                                # 'manage_propertiesForm' method
from AccessControl.Role import RoleManager # provide the 'Ownership' tab with
                                # the 'manage_owner' method
from Globals import DTMLFile # can use DTML files
from Globals import Persistent
from Acquisition import Implicit


class Scolar(Item,
	    Persistent,
	    Implicit,
	    PropertyManager,
            RoleManager,
	    ):

    "Scolar object"

    meta_type = 'Scolar'

    # This is the list of the methods associated to 'tabs' in the ZMI
    # Be aware that The first in the list is the one shown by default, so if
    # the 'View' tab is the first, you will never see your tabs by cliquing
    # on the object.
    manage_options = (
        PropertyManager.manage_options # add the 'Properties' tab
      + (
# this line is kept as an example with the files :
#     dtml/manage_editScolarForm.dtml
#     html/Scolar-edit.stx
#	{'label': 'Properties', 'action': 'manage_editForm',},
	{'label': 'View',       'action': 'index_html'},
      )
      + Item.manage_options            # add the 'Undo' & 'Owner' tab 
      + RoleManager.manage_options     # add the 'Security' tab
    )

    def __init__(self, id, title):
	"initialise a new instance of Scolar"
        self.id = id
	self.title = title
       
    # used to view content of the object
    index_html = DTMLFile('dtml/index_html', globals())

    # The for used to edit this object
    def manage_editAction(self, title, RESPONSE=None):
        "Changes the instance values"
        self.title = title
        self._p_changed = 1
        RESPONSE.redirect('manage_editForm')

# Uncomment these lines with the corresponding manage_option
# To everride the default 'Properties' tab
#    # Edit the Properties of the object
#    manage_editForm = DTMLFile('dtml/manage_editScolarForm', globals()) 

					    

#
# Product Administration
#

def manage_addAction(self, id= 'id_Scolar', title='The Title for Scolar Object', REQUEST=None):
   "Add a Scolar instance to a folder."
   self._setObject(id, Scolar(id, title))
   if REQUEST is not None:
        return self.manage_main(self, REQUEST)
        #return self.manage_editForm(self, REQUEST)

# The form used to get the instance id from the user.
manage_addForm = DTMLFile('dtml/manage_addScolarForm', globals())


    
