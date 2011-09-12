#! /usr/bin/env python
# Test program for jaxml
#
# (C) Jerome Alet <alet@librelogiciel.com> 2000
# You're welcome to redistribute this software under the
# terms of the GNU General Public Licence version 2.0
# or, at your option, any higher version.
#
# You can read the complete GNU GPL in the file COPYING
# which should come along with this software, or visit
# the Free Software Foundation's WEB site http://www.fsf.org
#
# $Id: test.py,v 1.13 2003/02/13 14:36:13 jerome Exp $
#

import sys

# import the jaxml module from the parent directory
sys.path.insert(0, "..")
import jaxml

print "\n\n==== TESTING XML ====\n"
# now we create an instance
# we may optionally pass a version and an encoding arguments.
x = jaxml.XML_document()

# first tag, with different attributes
# numeric values are automatically quoted
x.sometag(yes = "NO", some = "a bit", value = 5)

# this one, and till the end will be inside the previous one
x.anothertag("this tag and till the end will be inside the &lt;sometag&gt; ... &lt;/sometag&gt;")

# here we save the current position
x._push()

# here some nested tags
x.whatever()
x.ilikepython()
x._text("Here we are inside &lt;whatever&gt;&lt;ilikepython&gt; ... &lt;/ilikepython&gt;&lt;/whatever&gt;")

# the following tag has nothing but attributes, we must save and restore it's
# position because it is followed by another tag (we doesn't want to enclose the following tag)
x._push()
x.someattributetag(attr = "Hey ! I'm the attribute !")
x._pop()
x.justatest("This is just a test", dummy="YES")

# here we want to continue our document
# at the same indentation level than <whatever>
x._pop()

x.dummytag("we have just escaped", value = "Fine !")
x.dummytwo("Since the previous tag and this one were called with an unnamed first parameter\nwe didn't need _push() nor _pop()")


# here we insert plain text
x._text("Near the end")

# here we insert some text just like:
# <mytag>Some dummy text</mytag>
x.mytag("Some dummy text, and no tag attributes")

# here some beautiful tag nesting
x.onetag(message="This is").anotherone("a beautiful").deeper(message = "tag nesting possibility")

# here the naming space notation for <Space:Tag>...</Space:Tag>
x.namingspace.onetag("This is how to use the naming space notation Space:Tag", wonderful="YES")

# here just a tag with attributes, but nothing in it
# we don't need to _push() and _pop() because it isn't followed by anything
x.attributetag(content = "I've got nothing enclosed in me", index = 9)

# here we save to a file
x._output("sampleXML.xml")

# but we may as well output it to the screen
print x

# test the new templating facility
# I urge you to read the following lines and look carefully at the result
# to see how this beautiful thing works !
x._text("Now we will replace some content with the new possibility of using a document as a mapping.")
x._text("This may be useful for templating without a template file, or replacing some chars with their equivalent SGML entities for example:")
x._text("Here are three accented characters, two of them which will be replaced\nwith their equivalent SGML entities: איט")
x["nothing enclosed"] = "something enclosed"
x["SGML"] = "XML"
x["attributetag"] = "modifiedattributename"
x["י"] = "&eacute;";
x["ט"] = "&egrave;";
x["א"] = "&agrave;";

# this is also available as readable attributes
sys.stderr.write('x["ט"] = %s\n' % x["ט"])

# and we can also delete them
del x["ט"]

# or use the str() or repr() builtin functions
mydoc = "With str() or repr(), my modified document looks like:\n" + str(x) + "And that's all folks !"
print mydoc

# Now we want to test the HTML output
print "\n\n==== TESTING HTML ====\n"
page = jaxml.HTML_document()

# here we begin our html document
page.html()

# we must do a push and a pop in order for the <body> tags
# to not be enclosed between <head> and </head>
page._push()

# build the head of the document
page.head()
#
#
# Other meta tags should work fine
page._meta(name="GENERATOR", content="jaxml.py v2.24 from Jerome Alet - alet@librelogiciel.com")
page._meta(name="DESCRIPTION", content="A CGI document, to test jaxml.py")
page._meta(name="KEYWORDS", content="python, jaxml, linux")
page.title("A CGI test document")

# here we exit from the <head> ... </head>
page._pop()

# we begin the body
page.body(bgcolor="pink")

# here we insert a dumb text
page._text("A small text")

# we do a push to be able to exit from the <form> ... </form>
page._push()

page.form(action="/cgi-bin/jerome/ok.py", method="POST")

page.h1("Form's title")

# to be able to exit from <select> ... </select>
page._push()

page.select(name="choice", size="1", multiple="multiple")

page.option("Choice number 1")
page.option("Choice number 2", selected="selected")
page.option("Choice number 3")

# exit from <select> ... </select>
page._pop()

page.h3("Second part of the Form")
page._br()
page._textinput(name="dumbstring", size="50")
page._submit()
page._reset()

# here we exit from the <form> ... </form>
page._pop()

page._text("here we should be outside of the form")
page._text("and there we should be one the same line visually but on two different lines in the html file")

page.a("Click on Me", href="http://www.slashdot.org")
page.pre("Hello !!!\n\t\tBye Bye\n\n")

page._text("Here we should be outside of the PRE.../PRE tag")

# then we insert some text
page._text("Just below you will see some lines of text which are included from a template file, with variables substitution:")
page._br()

# then we include the template file
page._template("template.htt", font_color='red', link_to_my_homepage="<a href='http://www.librelogiciel.com/'>My website</a>", another_variable="<br /><center>Thank you for trying</center>")

# then some separation
page.hr(width="33%", noshade="noshade")

# here we do the output to the screen
page._output()

# and here we do the output to a file
page._output("sampleHTML.html")

# Now we want to test the CGI/HTML output
print "\n\n==== TESTING CGI ====\n"

# just some dummy values
page = jaxml.CGI_document(encoding = "utf-8", content_type="text/html", version = "3.0")

# to do a redirection, just do
# page.set_redirect("http://www.librelogiciel.com/")
# then just call page.output("")

# here again we can do that whenever we want (before output)
# text/html is the default for _set_content_type()
#page._set_content_type("application/pdf")

# to define a pragma, just use:
# page._set_pragma("pragma_name")
# we can do that whenever we want, (before output)

# to define an expiration date, just use:
# page._set_expires("expiration_date")
# we can do that whenever we want, (before output)

# Maybe this should be done by the class's __init__ function
# but I don't think so in order for us to have more control
page._default_header(title = 'a CGI document')

# we begin the body
page.body(bgcolor="pink")

# here we insert a dumb text
page._text("A small text")

# we do a push to be able to exit from the <form> ... </form>
page._push()

page.form(action="/cgi-bin/jerome/ok.py", method="POST")

page.h1("Form's title")

# to be able to exit from <select> ... </select>
page._push()

page.select(name="choice", size="1")

page.option("Choice number 1")
page.option("Choice number 2")
page.option("Choice number 3", selected="selected")

# exit from <select> ... </select>
page._pop()

page.h3("Second part of the Form")
page._br()
page._textinput(name="dumbstring", size="50")
page._submit()
page._reset()

# here we exit from the <form> ... </form>
page._pop()

page._text("here we should be outside of the form")
page._text("and there we should be one the same line visually but on two different lines in the html file")

page.a("Click on Me", href="http://www.slashdot.org")
page.pre("Hello !!!\n\t\tBye Bye\n\n")

page._text("Here we should be outside of the PRE.../PRE tag")

# here we define a debug file which will receive the CGI output too
page._set_debug("CGI_debug.html")

# here we do the output
# for a CGI script, give an empty string (for stdout)
# or None, or nothing, unless you want to debug (give a filename) or a file object
page._output("")

# Now we want to test the arithmetic operations
print "\n\n==== TESTING ARITHMETIC ====\n"

print "page + page = %s" % (page + page)
print "page + 'string' = %s" % (page + 'string')
print "'string' + page = %s" % ('string' + page)
print "page * 2 = %s" % (page * 2)
print "2 * page = %s" % (2 * page)

# new name spaces support
x = jaxml.XML_document()
x.tag("hello", name="blah")
x.another("bloum", 
          { "xmlns": { "tal" : "http://xml.zope.org/namespaces/tal",
                       "metal": "http://xml.zope.org/namespaces/metal"},
            "metal": {"use-macro" : "here/StandardLookAndFeel/macros/master"},
            "" : { "class" : "header"}
          })
          
x._push("save")          
x.otherone({ "xmlns": { "tal" : "http://xml.zope.org/namespaces/tal",
                        "metal": "http://xml.zope.org/namespaces/metal"},
             "metal": {"use-macro" : "here/StandardLookAndFeel/macros/master"},
             "" : { "class" : "header"}
           })
x._push()           
x.inside(name="inside")           
x.atag()
x._text("blah")
x._pop("save")
x.outside(attrib="None")
           
print x
