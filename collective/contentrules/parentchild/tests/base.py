from Products.Five import zcml
from Products.Five import fiveconfigure
from Products.PloneTestCase import PloneTestCase
from Products.PloneTestCase.layer import onsetup

@onsetup
def setupPackage():
    fiveconfigure.debug_mode = True
    import collective.contentrules.parentchild
    zcml.load_config('configure.zcml', collective.contentrules.parentchild)
    fiveconfigure.debug_mode = False

setupPackage()
PloneTestCase.setupPloneSite()

class TestCase(PloneTestCase.PloneTestCase):
    """Base class for integration tests
    """