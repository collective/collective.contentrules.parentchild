from unittest import defaultTestLoader
import unittest

from zope.interface import implementer
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

from collective.contentrules.parentchild.testing import FUNCTIONAL_TESTING

@implementer(IObjectEvent)
class DummyEvent(object):
    
    def __init__(self, object):
        self.object = object


class TestAutoTransitionAction(unittest.TestCase):

    layer = FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.folder = self.portal.folder
        self.folder.invokeFactory('Folder', 'f1')
        self.folder.f1.invokeFactory('Document', 'd1')

        self.portal.portal_workflow.setChainForPortalTypes(
                ('Folder', 'Document', ),
                ('simple_publication_workflow',),)
        
    def _autopublish(self):
        # Publish on demand, baby
        self.portal.portal_workflow['simple_publication_workflow'].transitions.publish.trigger_type = TRIGGER_AUTOMATIC

    def testRegistered(self): 
        element = getUtility(IRuleAction, name='collective.contentrules.parentchild.AutoTransition')
        self.assertEqual('collective.contentrules.parentchild.AutoTransition', element.addview)
        self.assertEqual('edit', element.editview)
        self.assertEqual(None, element.for_)
        self.assertEqual(IObjectEvent, element.event)
    
    def testInvokeAddView(self): 
        element = getUtility(IRuleAction, name='collective.contentrules.parentchild.AutoTransition')
        storage = getUtility(IRuleStorage)
        storage[u'foo'] = Rule()
        rule = self.portal.restrictedTraverse('++rule++foo')
        
        adding = getMultiAdapter((rule, self.portal.REQUEST), name='+action')
        addview = getMultiAdapter((adding, self.portal.REQUEST), name=element.addview).form_instance
        
        addview.updateFields()
        addview.add(addview.create(data={'parent' : True, 'check_types': set(['Document'])}))
        
        e = rule.actions[0]
        self.assertTrue(isinstance(e, AutoTransitionAction))
        self.assertEqual(True, e.parent)
        self.assertEqual(set(['Document']), e.check_types)
    
    def testInvokeEditView(self): 
        element = getUtility(IRuleAction, name='collective.contentrules.parentchild.AutoTransition')
        e = AutoTransitionAction()
        editview = getMultiAdapter((e, self.folder.REQUEST), name=element.editview).form_instance
        self.assertTrue(isinstance(editview, AutoTransitionEditForm))

    def testExecuteCurrent(self): 
        e = AutoTransitionAction()
        e.parent = False
        e.check_types = None
        
        self._autopublish()
        
        ex = getMultiAdapter((self.folder, e, DummyEvent(self.folder.f1.d1)), IExecutable)
        self.assertEqual(True, ex())
        
        self.assertEqual('private', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))
        self.assertEqual('published', self.portal.portal_workflow.getInfoFor(self.folder.f1.d1, 'review_state'))

    def testExecuteParent(self): 
        e = AutoTransitionAction()
        e.parent = True
        e.check_types = None
        
        self._autopublish()
        
        ex = getMultiAdapter((self.folder, e, DummyEvent(self.folder.f1.d1)), IExecutable)
        self.assertEqual(True, ex())
        
        self.assertEqual('private', self.portal.portal_workflow.getInfoFor(self.folder.f1.d1, 'review_state'))
        self.assertEqual('published', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))

    def testExecuteCurrentTypeCheck(self): 
        e = AutoTransitionAction()
        e.parent = False
        e.check_types = set(['Folder'])
        
        self.folder.f1.invokeFactory('Folder', 'f2')
        
        self._autopublish()
        
        ex = getMultiAdapter((self.folder, e, DummyEvent(self.folder.f1.f2)), IExecutable)
        self.assertEqual(True, ex())
        
        self.assertEqual('private', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))
        self.assertEqual('published', self.portal.portal_workflow.getInfoFor(self.folder.f1.f2, 'review_state'))

    def testExecuteCurrentTypeCheckPicksParent(self): 
        e = AutoTransitionAction()
        e.parent = False
        e.check_types = set(['Folder'])
        
        self._autopublish()
        
        ex = getMultiAdapter((self.folder, e, DummyEvent(self.folder.f1.d1)), IExecutable)
        self.assertEqual(True, ex())
        
        self.assertEqual('published', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))
        self.assertEqual('private', self.portal.portal_workflow.getInfoFor(self.folder.f1.d1, 'review_state'))

    def testExecuteParentTypeCheck(self): 
        e = AutoTransitionAction()
        e.parent = True
        e.check_types = set(['Folder'])
        
        self._autopublish()
        
        ex = getMultiAdapter((self.folder, e, DummyEvent(self.folder.f1.d1)), IExecutable)
        self.assertEqual(True, ex())
        
        self.assertEqual('private', self.portal.portal_workflow.getInfoFor(self.folder.f1.d1, 'review_state'))
        self.assertEqual('published', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))

    def testExecuteParentTypeCheckPicksGrandparent(self): 
        e = AutoTransitionAction()
        e.parent = True
        e.check_types = set(['Folder'])
        
        _createObjectByType('Folder', self.folder.f1, id='f2')
        self.folder.f1.f2.invokeFactory('Folder', 'f3')
        self.folder.f1.f2.portal_type = "Not Folder"

        self._autopublish()
        
        ex = getMultiAdapter((self.folder, e, DummyEvent(self.folder.f1.f2.f3)), IExecutable)
        self.assertEqual(True, ex())
        
        self.assertEqual('published', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))
        self.folder.f1.f2.portal_type = "Folder"
        self.assertEqual('private', self.portal.portal_workflow.getInfoFor(self.folder.f1.f2, 'review_state'))
        self.assertEqual('private', self.portal.portal_workflow.getInfoFor(self.folder.f1.f2.f3, 'review_state'))

    def testExecutCurrentTypeCheckPicksGrandparent(self): 
        e = AutoTransitionAction()
        e.parent = False
        e.check_types = set(['Folder'])
        
        _createObjectByType('Folder', self.folder.f1, id='f2')
        self.folder.f1.f2.invokeFactory('Document', 'd2')
        self.folder.f1.f2.portal_type = 'Not Folder'
        
        self._autopublish()
        
        ex = getMultiAdapter((self.folder, e, DummyEvent(self.folder.f1.f2.d2)), IExecutable)
        self.assertEqual(True, ex())
        
        self.assertEqual('published', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))
        self.folder.f1.f2.portal_type = 'Folder'
        self.assertEqual('private', self.portal.portal_workflow.getInfoFor(self.folder.f1.f2, 'review_state'))
        self.assertEqual('private', self.portal.portal_workflow.getInfoFor(self.folder.f1.f2.d2, 'review_state'))

def test_suite():
    return defaultTestLoader.loadTestsFromName(__name__)