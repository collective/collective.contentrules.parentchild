from unittest import defaultTestLoader

from zope.interface import implements
from zope.component import getUtility, getMultiAdapter

from plone.contentrules.engine.interfaces import IRuleStorage
from plone.contentrules.rule.interfaces import IRuleAction
from plone.contentrules.rule.interfaces import IExecutable

from collective.contentrules.parentchild.parenttransition import ParentTransitionAction
from collective.contentrules.parentchild.parenttransition import ParentTransitionEditForm

from plone.app.contentrules.rule import Rule

from zope.component.interfaces import IObjectEvent

from Products.CMFPlone.utils import _createObjectByType

from collective.contentrules.parentchild.tests.base import TestCase

class DummyEvent(object):
    implements(IObjectEvent)
    
    def __init__(self, object):
        self.object = object

class TestParentTransitionAction(TestCase):

    def afterSetUp(self):
        self.setRoles(('Manager',))
        self.folder.invokeFactory('Folder', 'f1')
        self.folder.f1.invokeFactory('Document', 'd1')

    def testRegistered(self): 
        element = getUtility(IRuleAction, name='collective.contentrules.parentchild.ParentTransition')
        self.assertEquals('collective.contentrules.parentchild.ParentTransition', element.addview)
        self.assertEquals('edit', element.editview)
        self.assertEquals(None, element.for_)
        self.assertEquals(IObjectEvent, element.event)
    
    def testInvokeAddView(self): 
        element = getUtility(IRuleAction, name='collective.contentrules.parentchild.ParentTransition')
        storage = getUtility(IRuleStorage)
        storage[u'foo'] = Rule()
        rule = self.portal.restrictedTraverse('++rule++foo')
        
        adding = getMultiAdapter((rule, self.portal.REQUEST), name='+action')
        addview = getMultiAdapter((adding, self.portal.REQUEST), name=element.addview)
        
        addview.createAndAdd(data={'transition' : 'publish', 'check_types': set(['Document'])})
        
        e = rule.actions[0]
        self.failUnless(isinstance(e, ParentTransitionAction))
        self.assertEquals('publish', e.transition)
        self.assertEquals(set(['Document']), e.check_types)
    
    def testInvokeEditView(self): 
        element = getUtility(IRuleAction, name='collective.contentrules.parentchild.ParentTransition')
        e = ParentTransitionAction()
        editview = getMultiAdapter((e, self.folder.REQUEST), name=element.editview)
        self.failUnless(isinstance(editview, ParentTransitionEditForm))

    def testExecute(self): 
        e = ParentTransitionAction()
        e.transition = 'publish'
        e.check_types = None
        
        ex = getMultiAdapter((self.folder, e, DummyEvent(self.folder.f1.d1)), IExecutable)
        self.assertEquals(True, ex())
        
        self.assertEquals('published', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))
        
    def testExecuteWithError(self): 
        e = ParentTransitionAction()
        e.transition = 'foobar'
        e.check_types = None
        
        old_state = self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state')
        
        ex = getMultiAdapter((self.folder, e, DummyEvent(self.folder.f1.d1)), IExecutable)
        self.assertEquals(False, ex())
        
        self.assertEquals(old_state, self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))

    def testExecuteTypeImmediateParent(self): 
        e = ParentTransitionAction()
        e.transition = 'publish'
        e.check_types = set(['Folder'])
        
        ex = getMultiAdapter((self.folder, e, DummyEvent(self.folder.f1.d1)), IExecutable)
        self.assertEquals(True, ex())
        
        self.assertEquals('published', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))

    def testExecuteTypeNestedParent(self): 
        e = ParentTransitionAction()
        e.transition = 'publish'
        e.check_types = set(['Folder'])
        
        _createObjectByType('Large Plone Folder', self.folder.f1, id='f2')
        self.folder.f1.f2.invokeFactory('Document', 'd2')
        
        old_state = self.portal.portal_workflow.getInfoFor(self.folder.f1.f2, 'review_state')
        
        ex = getMultiAdapter((self.folder, e, DummyEvent(self.folder.f1.f2.d1)), IExecutable)
        self.assertEquals(True, ex())
        
        self.assertEquals('published', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))
        self.assertEquals(old_state, self.portal.portal_workflow.getInfoFor(self.folder.f1.f2, 'review_state'))
    
def test_suite():
    return defaultTestLoader.loadTestsFromName(__name__)