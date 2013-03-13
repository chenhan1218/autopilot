Frequently asked questions
++++++++++++++++++++++++++

Q. If we add objectNames to QML items all over. What is the impact on memory?
=============================================================================

A. objectName is a QString property of QObject which defaults to QString().
QString is UTF-16 representation and because it uses some general purpose
optimisations it usually allocates twice the space it needs to be able to grow
fast. It also uses implicit sharing with copy-on-write and other similar
tricks to increase performance again. These properties makes the used memory
not straightforward to predict. For example, copying an object with an
objectName, shares the memory between both as long as they are not changed.

When measuring memory consumption, things like memory alignment come into play.
Due to the fact that QML is interpreted by a JavaScript engine, we are working
in levels where lots of abstraction layers are in between the code and the
hardware and we have no chance to exactly measure consumption of a single
objectName property. Therefore the taken approach is to measure lots of items
and calculate the average consumption.

Measurement of memory consumption of 10000 Items

* without objectName: 65292 kB
* with unique objectName ("item_0" .. "item_9999"): 66628 kB
* with same objectName: 66480 kB

=> With 10000 different objectNames 1336 kB of memory are consumed which is
around 127 Bytes per Item.

Indeed, this is more than only the string. Some of the memory is certainly lost
due to memory alignment where certain areas are just not perfectly filled in
but left empty. However, certainly not all of the overhead can be blamed on
that. Additional memory is used by the QObject meta object information that is
needed to do signal/slot connections. Also, QML does some optimisations: It
does not connect signals/slots when not needed. So the fact that the object
name is set could trigger some more connections.

Even if more than the actual string size is used and QString uses a large 
representation, this is very little compared to the rest. A qmlscene with just 
the item is 27MB. One full screen image in the Nexus 10 tablet can easily 
consume around 30MB of memory. So objectNames are definitely not the first
places where to search for optimisations.

Writing the test code snippets, one interesting thing came up frequently: Just 
modifying the code around to set the objectName often influences the results 
more than the actual string. For example, having a javascript function that
assigns the objectName definitely uses much more memory than the objectName
itself. Unless it makes sense from a performance point of view (frequently
changing bindings can be slow), objectNames should be added by directly
binding the value to the property instead using helper code to assign it.

Conclusion: If an objectName is needed for testing, this is definitely worth
it. objectName's should obviously not be added when not needed. When adding
them, the general QML guidelines for performance should be followed.
