from unittest import defaultTestLoader
import unittest

from zope.interface import implementer
from zope.component import getUtility, getMultiAdapter

from plone.contentrules.engine.interfaces import IRuleStorage
from plone.contentrules.rule.interfaces import IRuleCondition
from plone.contentrules.rule.interfaces import IExecutable
from plone.app.contentrules.conditions.portaltype import PortalTypeCondition

from collective.contentrules.parentchild.querysplitter import QuerySplitter
from collective.contentrules.parentchild.querysplitter import QuerySplitterEditForm
from collective.contentrules.parentchild.autotransition import AutoTransitionAction
from collective.contentrules.parentchild.testing import FUNCTIONAL_TESTING

from plone.app.contentrules.rule import Rule

from zope.component.interfaces import IObjectEvent
from Products.DCWorkflow.Transitions import TRIGGER_AUTOMATIC

from Products.CMFPlone.utils import _createObjectByType


@implementer(IObjectEvent)
class DummyEvent(object):

    def __init__(self, object):
        self.object = object


class TestQuerySplitter(unittest.TestCase):

    layer = FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.folder = self.portal.folder
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

        condition = addview.create(data={'rule': '__this__',
                                         'query': [{"i": "path", "o": "plone.app.querystring.operation.string.relativePath", "v": ".::1"}]})
        addview.add(condition)

        action = AutoTransitionAction()
        action.parent = False
        rule.actions.append(action)
        self._autopublish()
        return rule

    def _autopublish(self):
        # Publish on demand, baby
        self.portal.portal_workflow['simple_publication_workflow'].transitions.publish.trigger_type = TRIGGER_AUTOMATIC

    def testRegistered(self):
        element = getUtility(IRuleCondition, name='collective.contentrules.parentchild.QuerySplitter')
        self.assertEqual('collective.contentrules.parentchild.QuerySplitter', element.addview)
        self.assertEqual('edit', element.editview)
        self.assertEqual(None, element.for_)
        self.assertEqual(IObjectEvent, element.event)

    def testInvokeAddView(self):
        rule = self._createRule()
        e = rule.conditions[0]
        self.assertTrue(isinstance(e, QuerySplitter))
        self.assertEqual('path', e.query[0]['i'])
        self.assertEqual('__this__', e.rule)

    def testInvokeEditView(self):
        element = getUtility(IRuleCondition, name='collective.contentrules.parentchild.QuerySplitter')
        e = QuerySplitter()
        editview = getMultiAdapter((e, self.folder.REQUEST), name=element.editview).form_instance
        self.assertTrue(isinstance(editview, QuerySplitterEditForm))

    def testExecuteChild(self):
        rule = self._createRule()
        e = rule.conditions[0]
        e.rule = '__this__'
        e.query = [{"i": "path", "o": "plone.app.querystring.operation.string.relativePath", "v": ".::1"}]

        ex = getMultiAdapter((self.folder, rule, DummyEvent(self.folder.f1)), IExecutable)
        # we always get False since it won't execute the rule on the context
        self.assertEqual(False, ex())

        self.assertEqual('published', self.portal.portal_workflow.getInfoFor(self.folder.f1.d1, 'review_state'))
        self.assertEqual('private', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))

    def testExecuteTypeImmediateParent(self):
        rule = self._createRule()
        e = rule.conditions[0]
        e.rule = '__this__'
        e.query = [{"i": "path", "o": "plone.app.querystring.operation.string.relativePath", "v": "..::0"}]

        ex = getMultiAdapter((self.folder, rule, DummyEvent(self.folder.f1.d1)), IExecutable)
        # we always get False since it won't execute the rule on the context
        self.assertEqual(False, ex())

        self.assertEqual('published', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))
        self.assertEqual('private', self.portal.portal_workflow.getInfoFor(self.folder.f1.d1, 'review_state'))

    # TODO: can't do nested parents

    def testExecuteTypeDescendents(self):
        _createObjectByType('Folder', self.folder.f1, id='f2')
        self.folder.f1.f2.invokeFactory('Document', 'd2')

        rule = self._createRule()
        e = rule.conditions[0]
        e.rule = '__this__'
        e.query = [{"i": "path", "o": "plone.app.querystring.operation.string.relativePath", "v": "..::-1"}]

        ex = getMultiAdapter((self.folder, rule, DummyEvent(self.folder.f1)), IExecutable)
        # we always get False since it won't execute the rule on the context
        self.assertEqual(False, ex())

        self.assertEqual('published', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))
        self.assertEqual('published', self.portal.portal_workflow.getInfoFor(self.folder.f1.d1, 'review_state'))
        self.assertEqual('published', self.portal.portal_workflow.getInfoFor(self.folder.f1.f2, 'review_state'))
        self.assertEqual('published', self.portal.portal_workflow.getInfoFor(self.folder.f1.f2.d2, 'review_state'))

    def testExecuteFollowingConditions(self):
        _createObjectByType('Folder', self.folder.f1, id='f2')
        self.folder.f1.f2.invokeFactory('Document', 'd2')

        rule = self._createRule()
        e = rule.conditions[0]
        e.rule = '__this__'
        e.query = [{"i": "path", "o": "plone.app.querystring.operation.string.relativePath", "v": ".::-1"}]
        condition = PortalTypeCondition()
        condition.check_types = ["Document"]
        rule.conditions.append(condition)

        ex = getMultiAdapter((self.folder, rule, DummyEvent(self.folder.f1)), IExecutable)
        # we always get False since it won't execute the rule on the context
        self.assertEqual(False, ex())

        self.assertEqual('private', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))
        self.assertEqual('published', self.portal.portal_workflow.getInfoFor(self.folder.f1.d1, 'review_state'))
        self.assertEqual('private', self.portal.portal_workflow.getInfoFor(self.folder.f1.f2, 'review_state'))
        self.assertEqual('published', self.portal.portal_workflow.getInfoFor(self.folder.f1.f2.d2, 'review_state'))

    def testExecuteAnotherRule(self):

        rule = self._createRule()
        e = rule.conditions[0]
        e.rule = 'rule2'
        e.query = [{"i": "path", "o": "plone.app.querystring.operation.string.relativePath", "v": ".::-1"}]
        rule.actions.pop()

        storage = getUtility(IRuleStorage)
        storage[u'rule2'] = Rule()
        rule2 = self.portal.restrictedTraverse('++rule++rule2')
        action = AutoTransitionAction()
        action.parent = False
        rule2.actions.append(action)

        ex = getMultiAdapter((self.folder, rule, DummyEvent(self.folder.f1)), IExecutable)
        # we always get False since it won't execute the rule on the context
        self.assertEqual(False, ex())

        self.assertEqual('published', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))
        self.assertEqual('published', self.portal.portal_workflow.getInfoFor(self.folder.f1.d1, 'review_state'))

    def testSummary(self):
        _createObjectByType('Folder', self.folder.f1, id='f2')

        rule = self._createRule()
        e = rule.conditions[0]
        e.rule = '__this__'
        e.query = [{"i": "path", "o": "plone.app.querystring.operation.string.relativePath", "v": "..::-1"}]
        self.assertEqual('Execute this rule on "path relativePath ..::-1" instead', e.summary)


def test_suite():
    return defaultTestLoader.loadTestsFromName(__name__)
