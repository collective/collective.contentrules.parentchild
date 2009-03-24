from unittest import defaultTestLoader

from zope.interface import implements
from zope.component import getUtility, getMultiAdapter

from zope.component.interfaces import IObjectEvent

from plone.contentrules.engine.interfaces import IRuleStorage
from plone.contentrules.rule.interfaces import IRuleCondition
from plone.contentrules.rule.interfaces import IExecutable

from collective.contentrules.parentchild.child import ChildCondition
from collective.contentrules.parentchild.child import ChildEditForm

from plone.app.contentrules.rule import Rule

from collective.contentrules.parentchild.tests.base import TestCase

class DummyEvent(object):
    implements(IObjectEvent)
    
    def __init__(self, obj):
        self.object = obj

class TestChildCondition(TestCase):

    def afterSetUp(self):
        self.setRoles(('Manager',))

    def testRegistered(self): 
        element = getUtility(IRuleCondition, name='collective.contentrules.parentchild.Child')
        self.assertEquals('collective.contentrules.parentchild.Child', element.addview)
        self.assertEquals('edit', element.editview)
        self.assertEquals(None, element.for_)
        self.assertEquals(IObjectEvent, element.event)
    
    def testInvokeAddView(self): 
        element = getUtility(IRuleCondition, name='collective.contentrules.parentchild.Child')
        storage = getUtility(IRuleStorage)
        storage[u'foo'] = Rule()
        rule = self.portal.restrictedTraverse('++rule++foo')
        
        adding = getMultiAdapter((rule, self.portal.REQUEST), name='+condition')
        addview = getMultiAdapter((adding, self.portal.REQUEST), name=element.addview)
        
        addview.createAndAdd(data={'check_types' : set(['Folder', 'Image']),
                                   'wf_states': set(['published']),
                                   'recursive': True,
                                   'min_count': 2,
                                   'max_count': 3})
        
        e = rule.conditions[0]
        self.failUnless(isinstance(e, ChildCondition))
        self.assertEquals(set(['Folder', 'Image']), e.check_types)
        self.assertEquals(set(['published']), e.wf_states)
        self.assertEquals(True, e.recursive)
        self.assertEquals(2, e.min_count)
        self.assertEquals(3, e.max_count)
    
    def testInvokeEditView(self): 
        element = getUtility(IRuleCondition, name='collective.contentrules.parentchild.Child')
        e = ChildCondition()
        editview = getMultiAdapter((e, self.folder.REQUEST), name=element.editview)
        self.failUnless(isinstance(editview, ChildEditForm))

    def testExecuteType(self): 
        e = ChildCondition()
        e.check_types = ['Document', 'Image']
        e.wf_states = None
        e.recursive = False
        e.min_count = 1
        e.max_count = None
        
        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEquals(False, ex())
        
        self.folder.invokeFactory('Document', 'd1')
        
        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEquals(True, ex())
        
        self.folder.invokeFactory('Document', 'd2')
        
        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEquals(True, ex())
    
    def testExecuteWorkflow(self):
        e = ChildCondition()
        e.check_types = None
        e.wf_states = set(['published'])
        e.recursive = False
        e.min_count = 1
        e.max_count = None
        
        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEquals(False, ex())
        
        self.folder.invokeFactory('Document', 'd1')
        
        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEquals(False, ex())
        
        self.folder.invokeFactory('Document', 'd2')
        self.portal.portal_workflow.doActionFor(self.folder.d2, 'publish')
        
        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEquals(True, ex())

    def testExecuteCountMin(self):
        e = ChildCondition()
        e.check_types = set(['Document', 'Image'])
        e.wf_states = None
        e.recursive = False
        e.min_count = 2
        e.max_count = None
        
        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEquals(False, ex())
        
        self.folder.invokeFactory('Document', 'd1')
        
        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEquals(False, ex())
        
        self.folder.invokeFactory('Document', 'd2')
        
        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEquals(True, ex())

    def testExecuteCountMinMax(self):
        e = ChildCondition()
        e.check_types = set(['Document', 'Image'])
        e.wf_states = None
        e.recursive = False
        e.min_count = 2
        e.max_count = 3
        
        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEquals(False, ex())
        
        self.folder.invokeFactory('Document', 'd1')
        
        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEquals(False, ex())
        
        self.folder.invokeFactory('Document', 'd2')
        
        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEquals(True, ex())
        
        self.folder.invokeFactory('Document', 'd3')
        
        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEquals(True, ex())
        
        self.folder.invokeFactory('Document', 'd4')
        
        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEquals(False, ex())

    def testExecuteRecursive(self):
        e = ChildCondition()
        e.check_types = set(['Document', 'Image'])
        e.wf_states = None
        e.recursive = True
        e.min_count = 1
        e.max_count = None
        
        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEquals(False, ex())
        
        self.folder.invokeFactory('Folder', 'f1')
        
        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEquals(False, ex())
        
        self.folder.f1.invokeFactory('Document', 'd1')
        
        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEquals(True, ex())

    def testExecuteRecursiveDoesNotCountSelf(self):
        e = ChildCondition()
        e.check_types = set(['Folder', 'Document'])
        e.wf_states = None
        e.recursive = True
        e.min_count = 1
        e.max_count = None
        
        self.folder.invokeFactory('Folder', 'f1')
        
        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder.f1)), IExecutable)
        self.assertEquals(False, ex())
        
        self.folder.f1.invokeFactory('Folder', 'f11')
        
        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder.f1)), IExecutable)
        self.assertEquals(True, ex())

    def testExecuteComplex(self):
        e = ChildCondition()
        e.check_types = set(['Folder', 'Document'])
        e.wf_states = set(['published'])
        e.recursive = True
        e.min_count = 2
        e.max_count = 3
        
        self.folder.invokeFactory('Folder', 'f1')
        
        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEquals(False, ex())
        
        self.folder.f1.invokeFactory('Document', 'd1')
        
        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEquals(False, ex())
        
        self.portal.portal_workflow.doActionFor(self.folder.f1, 'publish')
        
        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEquals(False, ex())
        
        self.portal.portal_workflow.doActionFor(self.folder.f1.d1, 'publish')
        
        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEquals(True, ex())

def test_suite():
    return defaultTestLoader.loadTestsFromName(__name__)