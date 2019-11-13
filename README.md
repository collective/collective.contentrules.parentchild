Introduction
============

This package provides new conditions and actions for the Plone content rules
system:

  * A Splitter Condition to execute rules on all elements that match
    the query such as all children of a given type.
  * A condition to check whether a child object of a given type and/or
    workflow state exists.
  * An action to trigger automatic workflow transitions on the current
    object or the nearest parent object of a given type.
  * An action to invoke a particular workflow transition on the nearest parent
    object of a given type.
  