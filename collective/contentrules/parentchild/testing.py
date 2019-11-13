from plone.app.testing import PloneSandboxLayer
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import TEST_USER_ID, TEST_USER_NAME
from plone.app.testing import login, setRoles
from Products.Five import fiveconfigure
from plone.app.testing import FunctionalTesting

from plone.testing import z2


class ParentChild(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE, )

    def setUpZope(self, app, configurationContext):
        # Load ZCML
 
        fiveconfigure.debug_mode = True
        import collective.contentrules.parentchild
        self.loadZCML(package=collective.contentrules.parentchild)
        fiveconfigure.debug_mode = False

    def setUpPloneSite(self, portal):
        setRoles(portal, TEST_USER_ID, ['Manager', 'Member'])
        login(portal, TEST_USER_NAME)

        portal.portal_quickinstaller.installProduct("plone.app.contenttypes")
        portal.portal_workflow.setDefaultChain("simple_publication_workflow")

        portal.invokeFactory('Folder', id='folder')

FIXTURE = ParentChild()
FUNCTIONAL_TESTING = FunctionalTesting(bases=(FIXTURE,), name="ParentChild:Functional")


