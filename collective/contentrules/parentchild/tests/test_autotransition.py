from unittest import defaultTestLoader

from zope.interface import implements
from zope.component import getUtility, getMultiAdapter

from plone.contentrules.engine.interfaces import IRuleStorage
from plone.contentrules.rule.interfaces import IRuleAction
from plone.contentrules.rule.interfaces import IExecutable

from collective.contentrules.parentchild.autotransition import AutoTransitionAction
from collective.contentrules.parentchild.autotransition import AutoTransitionEditForm

from plone.app.contentrules.rule import Rule

from zope.component.interfaces import IObjectEvent

from Products.CMFPlone.utils import _createObjectByType
from Products.DCWorkflow.Transitions import TRIGGER_AUTOMATIC

from collective.contentrules.parentchild.tests.base import TestCase

class DummyEvent(object):
    implements(IObjectEvent)
    
    def __init__(self, object):
        self.object = object

class TestAutoTransitionAction(TestCase):

    def afterSetUp(self):
        self.setRoles(('Manager',))
        self.folder.invokeFactory('Folder', 'f1')
        self.folder.f1.invokeFactory('Document', 'd1')

        self.portal.portal_workflow.setChainForPortalTypes(
                ('Folder', 'Document', 'Large Plone Folder',),
                ('simple_publication_workflow',),)
        
    def _autopublish(self):
        # Publish on demand, baby
        self.portal.portal_workflow['simple_publication_workflow'].transitions.publish.trigger_type = TRIGGER_AUTOMATIC

    def testRegistered(self): 
        element = getUtility(IRuleAction, name='collective.contentrules.parentchild.AutoTransition')
        self.assertEquals('collective.contentrules.parentchild.AutoTransition', element.addview)
        self.assertEquals('edit', element.editview)
        self.assertEquals(None, element.for_)
        self.assertEquals(IObjectEvent, element.event)
    
    def testInvokeAddView(self): 
        element = getUtility(IRuleAction, name='collective.contentrules.parentchild.AutoTransition')
        storage = getUtility(IRuleStorage)
        storage[u'foo'] = Rule()
        rule = self.portal.restrictedTraverse('++rule++foo')
        
        adding = getMultiAdapter((rule, self.portal.REQUEST), name='+action')
        addview = getMultiAdapter((adding, self.portal.REQUEST), name=element.addview)
        
        addview.createAndAdd(data={'parent' : True, 'check_types': set(['Document'])})
        
        e = rule.actions[0]
        self.failUnless(isinstance(e, AutoTransitionAction))
        self.assertEquals(True, e.parent)
        self.assertEquals(set(['Document']), e.check_types)
    
    def testInvokeEditView(self): 
        element = getUtility(IRuleAction, name='collective.contentrules.parentchild.AutoTransition')
        e = AutoTransitionAction()
        editview = getMultiAdapter((e, self.folder.REQUEST), name=element.editview)
        self.failUnless(isinstance(editview, AutoTransitionEditForm))

    def testExecuteCurrent(self): 
        e = AutoTransitionAction()
        e.parent = False
        e.check_types = None
        
        self._autopublish()
        
        ex = getMultiAdapter((self.folder, e, DummyEvent(self.folder.f1.d1)), IExecutable)
        self.assertEquals(True, ex())
        
        self.assertEquals('private', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))
        self.assertEquals('published', self.portal.portal_workflow.getInfoFor(self.folder.f1.d1, 'review_state'))

    def testExecuteParent(self): 
        e = AutoTransitionAction()
        e.parent = True
        e.check_types = None
        
        self._autopublish()
        
        ex = getMultiAdapter((self.folder, e, DummyEvent(self.folder.f1.d1)), IExecutable)
        self.assertEquals(True, ex())
        
        self.assertEquals('private', self.portal.portal_workflow.getInfoFor(self.folder.f1.d1, 'review_state'))
        self.assertEquals('published', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))

    def testExecuteCurrentTypeCheck(self): 
        e = AutoTransitionAction()
        e.parent = False
        e.check_types = set(['Folder'])
        
        self.folder.f1.invokeFactory('Folder', 'f2')
        
        self._autopublish()
        
        ex = getMultiAdapter((self.folder, e, DummyEvent(self.folder.f1.f2)), IExecutable)
        self.assertEquals(True, ex())
        
        self.assertEquals('private', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))
        self.assertEquals('published', self.portal.portal_workflow.getInfoFor(self.folder.f1.f2, 'review_state'))

    def testExecuteCurrentTypeCheckPicksParent(self): 
        e = AutoTransitionAction()
        e.parent = False
        e.check_types = set(['Folder'])
        
        self._autopublish()
        
        ex = getMultiAdapter((self.folder, e, DummyEvent(self.folder.f1.d1)), IExecutable)
        self.assertEquals(True, ex())
        
        self.assertEquals('published', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))
        self.assertEquals('private', self.portal.portal_workflow.getInfoFor(self.folder.f1.d1, 'review_state'))

    def testExecuteParentTypeCheck(self): 
        e = AutoTransitionAction()
        e.parent = True
        e.check_types = set(['Folder'])
        
        self._autopublish()
        
        ex = getMultiAdapter((self.folder, e, DummyEvent(self.folder.f1.d1)), IExecutable)
        self.assertEquals(True, ex())
        
        self.assertEquals('private', self.portal.portal_workflow.getInfoFor(self.folder.f1.d1, 'review_state'))
        self.assertEquals('published', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))

    def testExecuteParentTypeCheckPicksGrandparent(self): 
        e = AutoTransitionAction()
        e.parent = True
        e.check_types = set(['Folder'])
        
        _createObjectByType('Large Plone Folder', self.folder.f1, id='f2')
        self.folder.f1.f2.invokeFactory('Folder', 'f3')
        
        self._autopublish()
        
        ex = getMultiAdapter((self.folder, e, DummyEvent(self.folder.f1.f2.f3)), IExecutable)
        self.assertEquals(True, ex())
        
        self.assertEquals('published', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))
        self.assertEquals('private', self.portal.portal_workflow.getInfoFor(self.folder.f1.f2, 'review_state'))
        self.assertEquals('private', self.portal.portal_workflow.getInfoFor(self.folder.f1.f2.f3, 'review_state'))

    def testExecutCurrentTypeCheckPicksGrandparent(self): 
        e = AutoTransitionAction()
        e.parent = False
        e.check_types = set(['Folder'])
        
        _createObjectByType('Large Plone Folder', self.folder.f1, id='f2')
        self.folder.f1.f2.invokeFactory('Document', 'd2')
        
        self._autopublish()
        
        ex = getMultiAdapter((self.folder, e, DummyEvent(self.folder.f1.f2.d2)), IExecutable)
        self.assertEquals(True, ex())
        
        self.assertEquals('published', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))
        self.assertEquals('private', self.portal.portal_workflow.getInfoFor(self.folder.f1.f2, 'review_state'))
        self.assertEquals('private', self.portal.portal_workflow.getInfoFor(self.folder.f1.f2.d2, 'review_state'))

def test_suite():
    return defaultTestLoader.loadTestsFromName(__name__)