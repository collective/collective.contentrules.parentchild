from unittest import defaultTestLoader

from zope.interface import implements
from zope.component import getUtility, getMultiAdapter

from plone.contentrules.engine.interfaces import IRuleStorage
from plone.contentrules.rule.interfaces import IRuleCondition
from plone.contentrules.rule.interfaces import IExecutable

from collective.contentrules.parentchild.querysplitter import QuerySplitter
from collective.contentrules.parentchild.querysplitter import QuerySplitterEditForm
from collective.contentrules.parentchild.autotransition import AutoTransitionAction

from plone.app.contentrules.rule import Rule

from zope.component.interfaces import IObjectEvent
from Products.DCWorkflow.Transitions import TRIGGER_AUTOMATIC

from Products.CMFPlone.utils import _createObjectByType

from collective.contentrules.parentchild.tests.base import TestCase

class DummyEvent(object):
    implements(IObjectEvent)
    
    def __init__(self, object):
        self.object = object

class TestQuerySplitter(TestCase):

    def afterSetUp(self):
        self.setRoles(('Manager',))
        self.folder.invokeFactory('Folder', 'f1')
        self.folder.f1.invokeFactory('Document', 'd1')

    def _createRule(self):
        element = getUtility(IRuleCondition, name='collective.contentrules.parentchild.QuerySplitter')
        storage = getUtility(IRuleStorage)
        storage[u'foo'] = Rule()
        rule = self.portal.restrictedTraverse('++rule++foo')
        
        adding = getMultiAdapter((rule, self.portal.REQUEST), name='+condition')
        addview = getMultiAdapter((adding, self.portal.REQUEST), name=element.addview).form_instance
        addview.updateFields()
        
        condition = addview.create(data={'action_source':'__this__',
            'query':[{"i":"path", "o":"plone.app.querystring.operation.string.relativePath","v":".::1"}]})
        addview.add(condition)

        action = AutoTransitionAction()
        action.parent = False
        addview.add(action)
        self._autopublish()
        return rule

    def _autopublish(self):
        # Publish on demand, baby
        self.portal.portal_workflow['simple_publication_workflow'].transitions.publish.trigger_type = TRIGGER_AUTOMATIC


    def testRegistered(self): 
        element = getUtility(IRuleCondition, name='collective.contentrules.parentchild.QuerySplitter')
        self.assertEquals('collective.contentrules.parentchild.QuerySplitter', element.addview)
        self.assertEquals('edit', element.editview)
        self.assertEquals(None, element.for_)
        self.assertEquals(IObjectEvent, element.event)
    
    def testInvokeAddView(self): 
        rule = self._createRule()
        e = rule.conditions[0]
        self.failUnless(isinstance(e, QuerySplitter))
        self.assertEquals('path', e.query[0]['i'])
        self.assertEquals('__this__', e.action_source)
    
    def testInvokeEditView(self): 
        element = getUtility(IRuleCondition, name='collective.contentrules.parentchild.ParentTransition')
        e = QuerySplitter()
        editview = getMultiAdapter((e, self.folder.REQUEST), name=element.editview)
        self.failUnless(isinstance(editview, QuerySplitterEditForm))

    def testExecuteChild(self): 
        rule = self._createRule()
        e = rule.conditions[0]
        e.action_source = '__this__'
        e.query = [{"i":"path", "o":"plone.app.querystring.operation.string.relativePath","v":".::1"}]
        
        ex = getMultiAdapter((self.folder, rule, DummyEvent(self.folder.f1)), IExecutable)
        # we always get False since it won't execute the rule on the context
        self.assertEquals(False, ex())
        
        self.assertEquals('published', self.portal.portal_workflow.getInfoFor(self.folder.f1.d1, 'review_state'))
        self.assertEquals('private', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))

    def testExecuteTypeImmediateParent(self): 
        rule = self._createRule()
        e = rule.conditions[0]
        e.action_source = '__this__'
        e.query = [{"i":"path", "o":"plone.app.querystring.operation.string.relativePath","v":"..::0"}]
        
        ex = getMultiAdapter((self.folder, rule, DummyEvent(self.folder.f1.d1)), IExecutable)
        # we always get False since it won't execute the rule on the context
        self.assertEquals(False, ex())
        
        self.assertEquals('published', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))
        self.assertEquals('private', self.portal.portal_workflow.getInfoFor(self.folder.f1.d1, 'review_state'))

    # TODO: can't do nested parents

    def testExecuteTypeDescendents(self): 
        _createObjectByType('Folder', self.folder.f1, id='f2')
        self.folder.f1.f2.invokeFactory('Document', 'd2')

        rule = self._createRule()
        e = rule.conditions[0]
        e.action_source = '__this__'
        e.query = [{"i":"path", "o":"plone.app.querystring.operation.string.relativePath","v":"..::-1"}]
        
        ex = getMultiAdapter((self.folder, rule, DummyEvent(self.folder.f1)), IExecutable)
        # we always get False since it won't execute the rule on the context
        self.assertEquals(False, ex())
        
        self.assertEquals('published', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))
        self.assertEquals('published', self.portal.portal_workflow.getInfoFor(self.folder.f1.d1, 'review_state'))
        self.assertEquals('published', self.portal.portal_workflow.getInfoFor(self.folder.f1.f2, 'review_state'))
        self.assertEquals('published', self.portal.portal_workflow.getInfoFor(self.folder.f1.f2.d2, 'review_state'))
    
def test_suite():
    return defaultTestLoader.loadTestsFromName(__name__)