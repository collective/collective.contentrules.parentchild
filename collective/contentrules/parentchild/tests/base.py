from Products.Five import fiveconfigure
from Products.PloneTestCase import PloneTestCase
from Products.PloneTestCase.layer import onsetup


from zope.configuration import xmlconfig


@onsetup
def setupPackage():
    fiveconfigure.debug_mode = True
    import collective.contentrules.parentchild
    xmlconfig.file('configure.zcml',
                   collective.contentrules.parentchild,
                   )

    fiveconfigure.debug_mode = False


setupPackage()
PloneTestCase.setupPloneSite()


class TestCase(PloneTestCase.PloneTestCase):
    """Base class for integration tests
    """
